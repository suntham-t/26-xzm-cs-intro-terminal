// cap.mjs —— 用 CDP 在一个无头页面里"按剧本跑多步并逐张截图"，最后输出 JSON 报告。
//
// 为什么不是手工一张张截：基线要和改造后的版本逐张对照，构图就必须可复现。
// 这个脚本保证：同样的剧本 = 同样的滚动位置、同样的等待、同样的 viewport，
// 于是 before/after 同名文件可以直接叠着看。
//
// 用法（通常由 cap.ps1 调起，不要直接跑）:
//   node cap.mjs --baseUrl=http://127.0.0.1:8800/ --out=D:\...\shots\before
//                --cdpPort=9223 --scenarios=...\scenarios.json --scenario=all
//   --html=<file>  用这份 HTML 顶替服务端返回的顶层文档（用于永远可重现的 before 基线）
//   --scenario 可以逗号分隔多个名字；--only=cat,sear 只跑名字里含这些子串的剧本。
//   --width/--height 是剧本没写 viewport 时的默认窗口；--noshot 只跑断言不截图。
//
// 依赖：Node 22+ 自带的 fetch / WebSocket，零第三方包。

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));

// ---------------------------------------------------------------- argv ------
const argv = process.argv.slice(2);
function arg(name, def) {
  const eq = argv.find(a => a.startsWith('--' + name + '='));
  if (eq) return eq.slice(name.length + 3);
  const i = argv.indexOf('--' + name);
  if (i >= 0 && argv[i + 1] && !argv[i + 1].startsWith('--')) return argv[i + 1];
  return def;
}
function flag(name) { return argv.includes('--' + name); }

const BASE_URL = arg('baseUrl', 'http://127.0.0.1:8800/');
const OUT = path.resolve(arg('out', 'shots'));
const CDP_PORT = arg('cdpPort', '9223');
const SCEN_FILE = path.resolve(arg('scenarios', path.join(HERE, 'scenarios.json')));
const SCENARIO_ARG = arg('scenario', 'all');
const ONLY = arg('only', '');
const DEF_W = Number(arg('width', '1280'));
const DEF_H = Number(arg('height', '880'));
const NO_SHOT = flag('noshot');
const SETTLE = Number(arg('settle', '1200'));
// --html=<file>：用 CDP Fetch 拦截顶层文档请求，把这一个文件的字节回给页面。
// 为什么需要它：Lead 随时在改 web/index.html，而"改造前"的基线必须永远能重现。
// 于是基线用 _redesign/baseline/index.html（= git HEAD 的字节）喂给页面，
// 页面里的 API 请求仍然打到真正跑着的 dev server（同源，不做任何代理）。
const HTML_FILE = arg('html', '');

const sleep = ms => new Promise(r => setTimeout(r, ms));

// ------------------------------------------------------- CDP connection -----
let seq = 0;
const pending = new Map();

// 事件归属：每条事件都记到"当前这一步"名下，报告里就能指认是哪一步弄脏了控制台。
let curRef = { scenario: '(boot)', step: -1, desc: 'page load' };
const EVENTS = [];
let MAIN_FRAME = null;        // 顶层 frameId：只拦它的 Document，别碰页面里的 iframe
let HTML_B64 = null;
let DOC_SERVED = 0;

function classifyEvent(msg) {
  if (msg.method === 'Runtime.exceptionThrown') {
    const d = msg.params && msg.params.exceptionDetails;
    const txt = (d && ((d.exception && (d.exception.description || d.exception.value)) || d.text)) || JSON.stringify(d);
    return { kind: 'exception', text: String(txt).slice(0, 800) };
  }
  if (msg.method === 'Runtime.consoleAPICalled' && msg.params && msg.params.type === 'error') {
    const a = msg.params.args || [];
    const txt = a.map(x => (x && (x.value !== undefined ? x.value
      : (x.description || (x.preview && JSON.stringify(x.preview)) || x.type)))).join(' ');
    return { kind: 'console-error', text: String(txt).slice(0, 600) };
  }
  if (msg.method === 'Runtime.consoleAPICalled' && msg.params && msg.params.type === 'warning') {
    const a = msg.params.args || [];
    const txt = a.map(x => (x && (x.value !== undefined ? x.value : x.description))).join(' ');
    return { kind: 'console-warn', text: String(txt).slice(0, 400) };
  }
  if (msg.method === 'Log.entryAdded') {
    const e = msg.params && msg.params.entry;
    if (!e) return null;
    if (e.level === 'error') {
      return { kind: 'log-error', text: String(e.text || '').slice(0, 400), source: e.source || '' };
    }
    return null;
  }
  return null;
}

let ws = null;

async function onFetchPaused(params) {
  try {
    if (HTML_B64 && params.resourceType === 'Document' && (!MAIN_FRAME || params.frameId === MAIN_FRAME)) {
      DOC_SERVED++;
      await send('Fetch.fulfillRequest', {
        requestId: params.requestId,
        responseCode: 200,
        responseHeaders: [
          { name: 'Content-Type', value: 'text/html; charset=utf-8' },
          { name: 'Cache-Control', value: 'no-store, must-revalidate' },
        ],
        body: HTML_B64,
      });
      return;
    }
    await send('Fetch.continueRequest', { requestId: params.requestId });
  } catch (e) {
    // 请求可能已经被取消（导航打断），继续下一个
  }
}

function onMessage(ev) {
  let msg;
  try { msg = JSON.parse(ev.data); } catch { return; }
  if (msg.method === 'Fetch.requestPaused') { onFetchPaused(msg.params).catch(() => { }); return; }
  const evt = classifyEvent(msg);
  if (evt) {
    EVENTS.push({ kind: evt.kind, text: evt.text, source: evt.source || '',
      scenario: curRef.scenario, step: curRef.step, desc: curRef.desc });
    if (evt.kind === 'exception' || evt.kind === 'console-error') {
      console.error('  [page] ' + evt.kind + ': ' + String(evt.text).replace(/\s+/g, ' ').slice(0, 220));
    }
    return;
  }
  if (msg.id && pending.has(msg.id)) {
    const { resolve, reject } = pending.get(msg.id);
    pending.delete(msg.id);
    if (msg.error) reject(new Error(JSON.stringify(msg.error)));
    else resolve(msg.result);
  }
}

function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++seq;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
}

async function connect() {
  let list = null;
  for (let i = 0; i < 60; i++) {
    try {
      const res = await fetch('http://127.0.0.1:' + CDP_PORT + '/json/list');
      list = await res.json();
      if (list && list.length) break;
    } catch { /* not up yet */ }
    await sleep(250);
  }
  if (!list) throw new Error('连不上 Chrome 调试端口 ' + CDP_PORT);
  const page = list.find(t => t.type === 'page');
  if (!page) throw new Error('没有 page target');
  ws = new WebSocket(page.webSocketDebuggerUrl);
  ws.addEventListener('message', onMessage);
  await new Promise((resolve, reject) => {
    ws.addEventListener('open', resolve, { once: true });
    ws.addEventListener('error', () => reject(new Error('WebSocket 连接失败')), { once: true });
  });
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Network.enable');
  await send('Network.setCacheDisabled', { cacheDisabled: true });
  try { await send('Log.enable'); } catch { }

  if (HTML_FILE) {
    if (!fs.existsSync(HTML_FILE)) throw new Error('--html 文件不存在: ' + HTML_FILE);
    HTML_B64 = fs.readFileSync(HTML_FILE).toString('base64');
    const ft = await send('Page.getFrameTree');
    MAIN_FRAME = ft && ft.frameTree && ft.frameTree.frame ? ft.frameTree.frame.id : null;
    await send('Fetch.enable', {
      patterns: [{ urlPattern: '*', resourceType: 'Document', requestStage: 'Request' }],
    });
    console.log('[cap] serving document from ' + HTML_FILE + ' (mainFrame=' + MAIN_FRAME + ')');
  }
}

// -------------------------------------------------------------- helpers -----
// 注进页面的一小包工具。每次 evaluate 都带上，页面重载后自动补回。
// 页面自己已有全局 $，这里一律用 __cap.* 避免撞名字。
const PRELUDE = [
  "window.__cap = {",
  "  sleep: function(ms){ return new Promise(function(r){ setTimeout(r, ms); }); },",
  "  q: function(s){ return document.querySelector(s); },",
  "  qa: function(s){ return Array.prototype.slice.call(document.querySelectorAll(s)); },",
  "  text: function(s){ var el = document.querySelector(s); return el ? (el.innerText || el.textContent || \"\").trim() : null; },",
  "  count: function(s){ return document.querySelectorAll(s).length; },",
  "  vis: function(s){ var el = document.querySelector(s); if(!el || el.hidden) return false;",
  "    var r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; },",
  "  click: function(s){ var el = (typeof s === \"string\") ? document.querySelector(s) : s;",
  "    if(!el){ throw new Error(\"click: not found \" + s); } el.click(); return true; },",
  "  setVal: function(s, v){ var el = document.querySelector(s);",
  "    if(!el){ throw new Error(\"setVal: not found \" + s); }",
  "    el.focus(); el.value = v;",
  "    el.dispatchEvent(new Event(\"input\", { bubbles: true }));",
  "    el.dispatchEvent(new Event(\"change\", { bubbles: true }));",
  "    return true; },",
  "  waitFor: async function(fn, ms){ var t0 = Date.now(); var last = null;",
  "    while(Date.now() - t0 < (ms || 4000)){",
  "      try { last = fn(); if (last) return last; } catch(e) { last = \"ERR \" + e.message; }",
  "      await new Promise(function(r){ setTimeout(r, 100); });",
  "    }",
  "    return last; },",
  "  ready: async function(ms){",
  "    var t0 = Date.now();",
  "    while(Date.now() - t0 < (ms || 8000)){",
  "      if (window.__IC__ && window.__IC__.ready_) {",
  "        try { await Promise.race([window.__IC__.ready_(), new Promise(function(r){ setTimeout(r, (ms||8000)); })]); } catch(e) {}",
  "        return true;",
  "      }",
  "      await new Promise(function(r){ setTimeout(r, 100); });",
  "    }",
  "    return false; }",
  "};"
].join("\n");

async function evaluate(expr) {
  const wrapped = '(async () => {\n' + PRELUDE + '\n' + expr + '\n})()';
  const r = await send('Runtime.evaluate', {
    expression: wrapped,
    awaitPromise: true,
    returnByValue: true,
    userGesture: true,
  });
  if (r.exceptionDetails) {
    const d = r.exceptionDetails;
    const txt = (d.exception && (d.exception.description || d.exception.value)) || d.text || 'evaluate failed';
    const err = new Error(String(txt).split('\n').slice(0, 6).join(' / '));
    err.exceptionDetails = d;
    throw err;
  }
  return r.result ? r.result.value : undefined;
}

const KEYMAP = {
  ArrowRight: { key: 'ArrowRight', code: 'ArrowRight', vk: 39 },
  ArrowLeft: { key: 'ArrowLeft', code: 'ArrowLeft', vk: 37 },
  ArrowDown: { key: 'ArrowDown', code: 'ArrowDown', vk: 40 },
  ArrowUp: { key: 'ArrowUp', code: 'ArrowUp', vk: 38 },
  Enter: { key: 'Enter', code: 'Enter', vk: 13, text: '\r' },
  Escape: { key: 'Escape', code: 'Escape', vk: 27 },
  Tab: { key: 'Tab', code: 'Tab', vk: 9 },
  Backspace: { key: 'Backspace', code: 'Backspace', vk: 8 },
  j: { key: 'j', code: 'KeyJ', vk: 74, text: 'j' },
  k: { key: 'k', code: 'KeyK', vk: 75, text: 'k' },
};

// 发真正的按键（trusted）：页面里的事件监听器才会当真。
async function pressKey(name) {
  const k = KEYMAP[name];
  if (!k) throw new Error('未知按键 ' + name + '（支持：' + Object.keys(KEYMAP).join(',') + '）');
  await send('Input.dispatchKeyEvent', {
    type: 'rawKeyDown', key: k.key, code: k.code,
    windowsVirtualKeyCode: k.vk, nativeVirtualKeyCode: k.vk,
    text: k.text || undefined, unmodifiedText: k.text || undefined,
  });
  if (k.text) {
    await send('Input.dispatchKeyEvent', {
      type: 'char', key: k.key, code: k.code,
      windowsVirtualKeyCode: k.vk, nativeVirtualKeyCode: k.vk,
      text: k.text, unmodifiedText: k.text,
    });
  }
  await send('Input.dispatchKeyEvent', {
    type: 'keyUp', key: k.key, code: k.code,
    windowsVirtualKeyCode: k.vk, nativeVirtualKeyCode: k.vk,
  });
}

async function setViewport(w, h) {
  await send('Emulation.setDeviceMetricsOverride', {
    width: w, height: h, deviceScaleFactor: 1, mobile: false,
  });
  // viewport 变化会触发 window resize；应用自己的 onWindowResize 要跑完布局才稳定。
  await sleep(420);
}

async function shot(file, fullPage) {
  let restore = null;
  if (fullPage) {
    const h = await evaluate('return Math.max(document.documentElement.scrollHeight, document.body.scrollHeight);');
    const w = await evaluate('return window.innerWidth;');
    restore = { w, h: await evaluate('return window.innerHeight;') };
    // 全页截图：把 viewport 撑到整页高，再抓 viewport（比 captureBeyondViewport 稳）
    await send('Emulation.setDeviceMetricsOverride', {
      width: w, height: Math.min(Math.max(h + 40, 800), 12000), deviceScaleFactor: 1, mobile: false,
    });
    await sleep(500);
  }
  const r = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  const buf = Buffer.from(r.data, 'base64');
  fs.writeFileSync(file, buf);
  if (restore) {
    await send('Emulation.setDeviceMetricsOverride', {
      width: restore.w, height: restore.h, deviceScaleFactor: 1, mobile: false,
    });
    await sleep(300);
  }
  return buf.length;
}

// 加载页面等稳。每次剧本都从导航开始，保证剧本之间不串状态。
async function loadFresh(url, settle) {
  curRef = { scenario: curRef.scenario, step: -1, desc: 'page load' };
  await send('Page.navigate', { url });
  await evaluate([
    'await __cap.sleep(150);',
    'if (window.__IC__ && window.__IC__.ready_) {',
    '  try { await Promise.race([window.__IC__.ready_(), __cap.sleep(8000)]); } catch(e) {}',
    '}',
    'return !!(window.__IC__ && window.__IC__.S);',
  ].join('\n')).catch(() => { });
  await sleep(settle);
}

// ------------------------------------------------------------ scenario -----
function pickScenarios(all) {
  const want = String(SCENARIO_ARG || 'all').split(',').map(s => s.trim()).filter(Boolean);
  let list = all;
  if (!(want.length === 1 && (want[0] === 'all' || want[0] === '*'))) {
    list = all.filter(s => want.includes(s.name));
    const missing = want.filter(w => !all.some(s => s.name === w));
    if (missing.length) console.error('[cap] 剧本不存在: ' + missing.join(', '));
  }
  if (ONLY) {
    const pats = ONLY.split(',').map(s => s.trim()).filter(Boolean);
    list = list.filter(s => pats.some(p => s.name.indexOf(p) >= 0));
  }
  return list;
}

async function runScenario(sc) {
  const t0 = Date.now();
  const rec = {
    name: sc.name, desc: sc.desc || '', note: sc.note || '',
    ok: true, ms: 0, skipped: false, skipReason: '',
    viewport: sc.viewport || [DEF_W, DEF_H],
    shots: [], steps: [], errors: [],
  };
  console.log('\n[cap] === ' + sc.name + '  ' + (sc.desc || ''));

  try {
    curRef = { scenario: sc.name, step: -1, desc: 'load' };
    await setViewport(rec.viewport[0], rec.viewport[1]);
    await loadFresh(sc.url ? new URL(sc.url, BASE_URL).toString() : BASE_URL, sc.settle != null ? sc.settle : SETTLE);

    // 每个剧本开场先归一化界面状态（REPL/目录/滚动）。
    // 为什么必须做：ui.repl / ui.toc 这些偏好是**存到服务端进度**里的，一个剧本打开
    // 了 REPL，后面所有剧本的截图里都会多出一条终端抽屉 —— before/after 就没法逐张对照了。
    if (sc.beforeJs) {
      curRef = { scenario: sc.name, step: -1, desc: 'reset ui' };
      const rv = await evaluate(sc.beforeJs);
      if (rv !== undefined) console.log('  reset: ' + JSON.stringify(rv));
    }

    if (sc.readyJs) {
      curRef = { scenario: sc.name, step: 0, desc: 'readyJs' };
      const v = await evaluate(sc.readyJs);
      if (!v) {
        rec.skipped = true;
        rec.skipReason = 'readyJs returned ' + JSON.stringify(v);
        console.log('  [skip] ' + rec.skipReason);
        rec.ms = Date.now() - t0;
        return rec;
      }
    }

    for (let i = 0; i < sc.steps.length; i++) {
      const st = sc.steps[i];
      const kind = st.kind || (st.js ? 'js' : st.wait ? 'wait' : st.key ? 'key' : st.shot ? 'shot' : '?');
      const stepRec = { i, desc: st.desc || (st.js ? String(st.js).replace(/\s+/g, ' ').slice(0, 90) : kind), kind, ok: true, ms: 0, error: null, value: undefined };
      curRef = { scenario: sc.name, step: i, desc: stepRec.desc };
      const s0 = Date.now();
      try {
        if (st.js) {
          const v = await evaluate(st.js);
          if (v !== undefined) stepRec.value = v;
        }
        if (st.wait) await sleep(st.wait);
        if (st.key) { await pressKey(st.key); if (st.after) await sleep(st.after); }
        if (st.shot) {
          if (NO_SHOT) { stepRec.value = 'noshot'; }
          else {
            const w = st.w || rec.viewport[0];
            const h = st.h || rec.viewport[1];
            if (w !== rec.viewport[0] || h !== rec.viewport[1]) await setViewport(w, h);
            const file = path.join(OUT, st.shot + '.png');
            const bytes = await shot(file, !!st.full);
            rec.shots.push({ file: st.shot + '.png', abs: file, bytes, w, h, full: !!st.full });
            console.log('  shot ' + (st.shot + '.png').padEnd(36) + String(bytes).padStart(8) + ' B');
          }
        }
        if (st.expect) {
          const v = await evaluate('return (' + st.expect + ');');
          if (!v) { stepRec.ok = false; stepRec.error = 'expect failed: ' + st.expect; rec.ok = false; }
          stepRec.value = stepRec.value === undefined ? v : stepRec.value;
        }
      } catch (e) {
        stepRec.ok = false;
        stepRec.error = String(e && e.message || e).replace(/\s+/g, ' ').slice(0, 400);
        rec.ok = false;
        console.log('  [step ' + i + ' FAIL] ' + stepRec.error);
      }
      stepRec.ms = Date.now() - s0;
      rec.steps.push(stepRec);
    }

    // 每个剧本收尾再抓一组定尺寸图（剧本自带 shots 列表时）
    const shotsSpec = sc.shots || [];
    for (const sp of shotsSpec) {
      if (NO_SHOT) break;
      const w = sp.w || rec.viewport[0];
      const h = sp.h || rec.viewport[1];
      curRef = { scenario: sc.name, step: rec.steps.length, desc: 'shot ' + w + 'x' + h };
      if (w !== rec.viewport[0] || h !== rec.viewport[1]) { await setViewport(w, h); }
      else { await sleep(120); }
      const name = sc.name + '@' + w + 'x' + h + (sp.full ? '-full' : '');
      const file = path.join(OUT, name + '.png');
      try {
        const bytes = await shot(file, !!sp.full);
        rec.shots.push({ file: name + '.png', abs: file, bytes, w, h, full: !!sp.full });
        console.log('  shot ' + (name + '.png').padEnd(36) + String(bytes).padStart(8) + ' B');
      } catch (e) {
        rec.ok = false;
        rec.errors.push('screenshot ' + name + ': ' + e.message);
        console.log('  [shot FAIL] ' + name + ': ' + e.message);
      }
    }
  } catch (e) {
    rec.ok = false;
    rec.errors.push('scenario: ' + String(e && e.message || e).slice(0, 400));
    console.log('  [scenario FAIL] ' + rec.errors[rec.errors.length - 1]);
  }

  rec.consoleErrors = EVENTS.filter(e => e.scenario === sc.name && e.kind === 'console-error').map(e => ({ step: e.step, text: e.text }));
  rec.exceptions = EVENTS.filter(e => e.scenario === sc.name && e.kind === 'exception').map(e => ({ step: e.step, text: e.text }));
  rec.warnings = EVENTS.filter(e => e.scenario === sc.name && e.kind === 'console-warn').map(e => e.text);
  rec.logErrors = EVENTS.filter(e => e.scenario === sc.name && e.kind === 'log-error').map(e => ({ step: e.step, text: e.text }));
  if (rec.exceptions.length) rec.ok = false;   // 未捕获异常 = 剧本失败，没有商量
  if (rec.skipped) rec.ok = true;
  rec.ms = Date.now() - t0;
  console.log('  [' + (rec.skipped ? 'SKIP' : rec.ok ? 'ok' : 'FAIL') + '] ' + rec.name + '  ' + rec.ms + 'ms  shots=' + rec.shots.length + '  exceptions=' + rec.exceptions.length + '  console.error=' + rec.consoleErrors.length);
  return rec;
}

// ---------------------------------------------------------------- main -----
async function main() {
  if (!fs.existsSync(SCEN_FILE)) {
    console.error('[cap] 找不到剧本文件: ' + SCEN_FILE);
    process.exit(2);
  }
  const cfg = JSON.parse(fs.readFileSync(SCEN_FILE, 'utf8'));
  const all = (cfg.scenarios || []).map(s => Object.assign({}, cfg.defaults || {}, s));
  const list = pickScenarios(all);
  if (!list.length) { console.error('[cap] 没有匹配的剧本'); process.exit(2); }

  fs.mkdirSync(OUT, { recursive: true });
  // 幂等：同名旧图先删掉，防止失败时留着上一轮的图冒充这一轮。
  for (const f of fs.readdirSync(OUT)) {
    if (f.endsWith('.png')) fs.unlinkSync(path.join(OUT, f));
  }

  await connect();
  const results = [];
  for (const sc of list) {
    results.push(await runScenario(sc));
  }
  try { ws.close(); } catch { }

  const failed = results.filter(r => !r.ok);
  const report = {
    generatedAt: new Date().toISOString(),
    baseUrl: BASE_URL,
    htmlOverride: HTML_FILE || null,
    documentsServedFromOverride: DOC_SERVED,
    cdpPort: CDP_PORT,
    out: OUT,
    total: results.length,
    failed: failed.length,
    skipped: results.filter(r => r.skipped).length,
    shotCount: results.reduce((n, r) => n + r.shots.length, 0),
    scenarios: results,
  };
  fs.writeFileSync(path.join(OUT, '_report.json'), JSON.stringify(report, null, 2), 'utf8');

  const totalConsoleErrors = EVENTS.filter(e => e.kind === 'console-error').length;
  const totalExceptions = EVENTS.filter(e => e.kind === 'exception').length;
  console.log('\n================ summary ================');
  for (const r of results) {
    console.log(' ' + (r.skipped ? 'SKIP' : r.ok ? ' OK ' : 'FAIL') + ' ' + r.name.padEnd(18) +
      String(r.shots.length).padStart(2) + ' shots  ' + String(r.ms).padStart(6) + 'ms' +
      (r.skipped ? '   skipped: ' + r.skipReason : '') +
      (!r.ok ? '   errors=' + (r.errors.length + r.exceptions.length) : ''));
  }
  console.log(' total shots=' + report.shotCount + '  scenarios=' + results.length +
    '  failed=' + failed.length + '  skipped=' + report.skipped +
    '  console.error=' + totalConsoleErrors + '  uncaught=' + totalExceptions);
  if (HTML_FILE) console.log(' html override: ' + HTML_FILE + '  documents served: ' + DOC_SERVED);
  console.log(' report: ' + path.join(OUT, '_report.json'));

  const noise = EVENTS.filter(e => e.kind === 'console-error' || e.kind === 'exception');
  if (noise.length) {
    console.log(' ---- page noise (first 12) ----');
    for (const e of noise.slice(0, 12)) {
      console.log('  ' + e.kind.padEnd(13) + ' [' + e.scenario + '#' + e.step + '] ' + String(e.text).replace(/\s+/g, ' ').slice(0, 180));
    }
  } else {
    console.log(' page noise: none');
  }
  process.exit(failed.length ? 1 : 0);
}

main().catch(e => {
  console.error('[cap] fatal: ' + (e && e.stack || e));
  try { if (ws) ws.close(); } catch { }
  process.exit(1);
});
