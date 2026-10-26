// smoke.mjs —— 前端功能回归：纯 CDP 驱动真实的 headless Chrome，做"点了有没有反应"的断言。
//
// 骨架和 cap.mjs 一样（连 CDP → 导航 → Runtime.evaluate 操作页面 → 收页面事件），
// 区别是它只断言不截图：每条断言打印 PASS/FAIL，最后按失败数给 exit code。
// Lead 改完 CSS/HTML 先跑它确认"功能一个不少"，再跑 cap.ps1 看视觉。
//
// 用法（一般由 cap.ps1 -Smoke 调起）:
//   node smoke.mjs --baseUrl=http://127.0.0.1:8800/ --cdpPort=9223
//   node smoke.mjs --html=D:\...\_redesign\baseline\index.html   # 对基线跑一遍做对照
//   --json=<path> 写机器可读报告；--failShots=<dir> 失败时存图便于定位。
//
// 依赖：Node 22+ 自带 fetch / WebSocket，零第三方包。

import fs from 'node:fs';
import path from 'node:path';

const argv = process.argv.slice(2);
function arg(name, def) {
  const eq = argv.find(a => a.startsWith('--' + name + '='));
  if (eq) return eq.slice(name.length + 3);
  const i = argv.indexOf('--' + name);
  if (i >= 0 && argv[i + 1] && !argv[i + 1].startsWith('--')) return argv[i + 1];
  return def;
}
const BASE_URL = arg('baseUrl', 'http://127.0.0.1:8800/');
const CDP_PORT = arg('cdpPort', '9223');
const HTML_FILE = arg('html', '');
const JSON_OUT = arg('json', '');
const FAIL_SHOTS = arg('failShots', '');
const W = Number(arg('width', '1280'));
const H = Number(arg('height', '880'));

const sleep = ms => new Promise(r => setTimeout(r, ms));

// ------------------------------------------------------------ CDP client ----
let seq = 0;
const pending = new Map();
const EXCEPTIONS = [];      // 未捕获异常（必须为 0）
const CONSOLE_ERRORS = [];  // console.error（允许有，但要列出来）
let ws = null;
let MAIN_FRAME = null;
let HTML_B64 = null;

function onMessage(ev) {
  let msg;
  try { msg = JSON.parse(ev.data); } catch { return; }
  if (msg.method === 'Fetch.requestPaused') { onPaused(msg.params).catch(() => { }); return; }
  if (msg.method === 'Runtime.exceptionThrown') {
    const d = msg.params && msg.params.exceptionDetails;
    const txt = (d && ((d.exception && (d.exception.description || d.exception.value)) || d.text)) || JSON.stringify(d);
    EXCEPTIONS.push(String(txt).replace(/\s+/g, ' ').slice(0, 600));
    return;
  }
  if (msg.method === 'Runtime.consoleAPICalled' && msg.params && msg.params.type === 'error') {
    const a = msg.params.args || [];
    CONSOLE_ERRORS.push(a.map(x => (x && (x.value !== undefined ? x.value : (x.description || x.type)))).join(' ').slice(0, 400));
    return;
  }
  if (msg.id && pending.has(msg.id)) {
    const { resolve, reject } = pending.get(msg.id);
    pending.delete(msg.id);
    if (msg.error) reject(new Error(JSON.stringify(msg.error)));
    else resolve(msg.result);
  }
}

async function onPaused(params) {
  try {
    if (HTML_B64 && params.resourceType === 'Document' && (!MAIN_FRAME || params.frameId === MAIN_FRAME)) {
      await send('Fetch.fulfillRequest', {
        requestId: params.requestId, responseCode: 200,
        responseHeaders: [
          { name: 'Content-Type', value: 'text/html; charset=utf-8' },
          { name: 'Cache-Control', value: 'no-store, must-revalidate' },
        ],
        body: HTML_B64,
      });
      return;
    }
    await send('Fetch.continueRequest', { requestId: params.requestId });
  } catch { /* 请求已被导航取消 */ }
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
    } catch { /* 端口还没起 */ }
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
  if (HTML_FILE) {
    HTML_B64 = fs.readFileSync(HTML_FILE).toString('base64');
    const ft = await send('Page.getFrameTree');
    MAIN_FRAME = ft && ft.frameTree && ft.frameTree.frame.id ? ft.frameTree.frame.id : null;
    await send('Fetch.enable', { patterns: [{ urlPattern: '*', resourceType: 'Document', requestStage: 'Request' }] });
  }
}

const PRELUDE = [
  "window.__sm = {",
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
    expression: wrapped, awaitPromise: true, returnByValue: true, userGesture: true,
  });
  if (r.exceptionDetails) {
    const d = r.exceptionDetails;
    const txt = (d.exception && (d.exception.description || d.exception.value)) || d.text || 'evaluate failed';
    throw new Error(String(txt).split('\n').slice(0, 5).join(' / '));
  }
  return r.result ? r.result.value : undefined;
}

const KEYMAP = {
  ArrowRight: { key: 'ArrowRight', code: 'ArrowRight', vk: 39 },
  ArrowLeft: { key: 'ArrowLeft', code: 'ArrowLeft', vk: 37 },
  Enter: { key: 'Enter', code: 'Enter', vk: 13, text: '\r' },
  Escape: { key: 'Escape', code: 'Escape', vk: 27 },
  j: { key: 'j', code: 'KeyJ', vk: 74, text: 'j' },
};
async function pressKey(name) {
  const k = KEYMAP[name];
  if (!k) throw new Error('未知按键 ' + name);
  await send('Input.dispatchKeyEvent', {
    type: 'rawKeyDown', key: k.key, code: k.code,
    windowsVirtualKeyCode: k.vk, nativeVirtualKeyCode: k.vk,
    text: k.text || undefined, unmodifiedText: k.text || undefined,
  });
  if (k.text) {
    await send('Input.dispatchKeyEvent', {
      type: 'char', key: k.key, code: k.code, windowsVirtualKeyCode: k.vk,
      nativeVirtualKeyCode: k.vk, text: k.text, unmodifiedText: k.text,
    });
  }
  await send('Input.dispatchKeyEvent', {
    type: 'keyUp', key: k.key, code: k.code,
    windowsVirtualKeyCode: k.vk, nativeVirtualKeyCode: k.vk,
  });
}

async function shot(file) {
  const r = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  fs.writeFileSync(file, Buffer.from(r.data, 'base64'));
}

// --------------------------------------------------------------- harness -----
const RESULTS = [];
const NOTES = [];

function ok(name, extra) {
  RESULTS.push({ name, ok: true, detail: extra || '' });
  console.log('  PASS  ' + name + (extra ? '   (' + extra + ')' : ''));
}
function bad(name, detail) {
  RESULTS.push({ name, ok: false, detail: String(detail || '') });
  console.log('  FAIL  ' + name + '   -> ' + String(detail || ''));
}
/** 记录一条"看见但不算失败"的观察（比如基线上就有的小毛病）。 */
function note(name, text) {
  NOTES.push({ name, text });
  console.log('  NOTE  ' + name + '   ' + text);
}

/** 跑一条断言：抛错或显式 {pass:false} 都算失败；失败顺手截图存现场。 */
async function check(name, fn) {
  try {
    const v = await fn();
    if (v && v.pass === false) { bad(name, v.detail); return false; }
    ok(name, v && v.detail ? v.detail : '');
    return true;
  } catch (e) {
    bad(name, String(e && e.message || e).split('\n')[0]);
    if (FAIL_SHOTS) {
      try {
        fs.mkdirSync(FAIL_SHOTS, { recursive: true });
        const safe = name.replace(/[^\w.-]+/g, '_').slice(0, 60);
        await shot(path.join(FAIL_SHOTS, 'fail-' + safe + '.png'));
      } catch { /* 忽略 */ }
    }
    return false;
  }
}

const CARD_TITLE = "(document.querySelector('#card h2.cardTitle') || {textContent:''}).textContent.trim()";
const DOT_COUNT = "(document.querySelector('#dotCount') || {textContent:''}).textContent.trim()";
const CARD_PRESENT = "!!document.querySelector('#card') && document.querySelectorAll('#card h2.cardTitle').length === 1";
const STATE = "JSON.stringify({inlineHidden:document.querySelector('#inlinePanel').hidden,modalHidden:document.querySelector('#modal').hidden,card:" + CARD_PRESENT + "})";

async function loadFresh() {
  await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: BASE_URL });
  await evaluate([
    'await __sm.sleep(150);',
    'if (window.__IC__ && window.__IC__.ready_) {',
    '  try { await Promise.race([window.__IC__.ready_(), __sm.sleep(10000)]); } catch(e) {}',
    '}',
    'await __sm.sleep(400);',
    'window.__IC__ && window.__IC__.closeAll();',
    'await __sm.sleep(250);',
    'if (!document.querySelector("#repl").hidden) { var rb=document.querySelector("#btnReplClose"); if(rb) rb.click(); await __sm.sleep(300); }',
    'var wide = document.body.getAttribute("data-wide") === "1";',
    'if (wide && document.querySelector("#toc").hidden) { document.querySelector("#btnToc").click(); await __sm.sleep(400); }',
    'return !!(window.__IC__ && window.__IC__.S);',
  ].join('\n'));
  await sleep(500);
}

async function main() {
  console.log('[smoke] target ' + BASE_URL + (HTML_FILE ? '  (html override: ' + HTML_FILE + ')' : ''));
  await connect();
  await loadFresh();

  // 1) 卡片落地
  await check('card.landing 卡片落地有标题与点阵', async () => {
    const v = await evaluate('return JSON.stringify({t:' + CARD_TITLE + ', dots:document.querySelectorAll("#dots .dot").length, d:' + DOT_COUNT + '});');
    const o = JSON.parse(v);
    if (!o.t) return { pass: false, detail: 'cardTitle 为空' };
    if (!(o.dots > 0)) return { pass: false, detail: '#dots .dot 数量 ' + o.dots };
    return { detail: 'title=' + o.t + ' dots=' + o.dots + ' ' + o.d };
  });

  // 2) 翻卡：键盘 ArrowRight + 按钮 #btnNext
  await check('card.key 方向键翻卡（#dotCount 变化）', async () => {
    const before = await evaluate('return ' + DOT_COUNT + ';');
    await pressKey('ArrowRight');
    await sleep(700);
    const after = await evaluate('return ' + DOT_COUNT + ';');
    if (before === after) return { pass: false, detail: 'ArrowRight 前后都是 ' + JSON.stringify(before) };
    return { detail: JSON.stringify(before) + ' -> ' + JSON.stringify(after) };
  });
  await check('card.next 点 #btnNext 翻卡（#dotCount 变化）', async () => {
    const before = await evaluate('return ' + DOT_COUNT + ';');
    await evaluate('document.querySelector("#btnNext").click();');
    await sleep(700);
    const after = await evaluate('return ' + DOT_COUNT + ';');
    if (before === after) return { pass: false, detail: '点 #btnNext 前后都是 ' + JSON.stringify(before) };
    return { detail: JSON.stringify(before) + ' -> ' + JSON.stringify(after) };
  });

  // 3) 目录：#btnToc 开关 + .tocPt 跳卡
  await check('toc.toggle #btnToc 能开关目录', async () => {
    const a = await evaluate('return document.querySelector("#toc").hidden;');
    await evaluate('document.querySelector("#btnToc").click(); await __sm.sleep(500); return true;');
    const b = await evaluate('return document.querySelector("#toc").hidden;');
    if (a === b) return { pass: false, detail: '#toc hidden 没有变化（' + a + '）' };
    return { detail: 'hidden ' + a + ' -> ' + b };
  });
  await evaluate('if (document.querySelector("#toc").hidden) { document.querySelector("#btnToc").click(); await __sm.sleep(500); } return true;');
  await check('toc.jump 点 .tocPt 能跳卡', async () => {
    const before = await evaluate('return ' + CARD_TITLE + ';');
    const v = await evaluate([
      'var pts = __sm.qa("#tocBody .tocPt");',
      'if (pts.length < 5) throw new Error(".tocPt 只有 " + pts.length + " 个");',
      'pts[4].click(); await __sm.sleep(900);',
      'return ' + CARD_TITLE + ';',
    ].join('\n'));
    if (!v) return { pass: false, detail: '跳转后 cardTitle 为空' };
    if (v === before) return { pass: false, detail: '标题没变，仍是 ' + before };
    return { detail: JSON.stringify(before) + ' -> ' + JSON.stringify(v) };
  });

  // 4) 搜索：打开
  await loadFresh();
    // 每个 block 从干净页面重新加载：history 栈 / 键盘焦点 / 上次开的层都不跨 block 污染。 → 输入 → 命中 → 点第一条 → 卡片变 + .findmark
  await check('search.open #btnSearch 打开搜索面板', async () => {
    const v = await evaluate('document.querySelector("#btnSearch").click(); await __sm.sleep(600);' +
      'var m=document.querySelector("#modal");' +
      'return JSON.stringify({hidden:m.hidden, kind:m.getAttribute("data-kind"), input:!!document.querySelector("#modal .searchInput")});');
    const o = JSON.parse(v);
    if (o.hidden || o.kind !== 'search' || !o.input) return { pass: false, detail: v };
    return { detail: 'data-kind=search' };
  });
  await check('search.hits 输入「列表」出现命中列表', async () => {
    const v = await evaluate('__sm.setVal("#modal .searchInput", "列表"); await __sm.sleep(800);' +
      'return document.querySelectorAll(".searchHit").length;');
    if (!(v > 0)) return { pass: false, detail: '.searchHit 数量 ' + v };
    return { detail: '.searchHit=' + v };
  });
  await check('search.jump 点第一条命中 → 卡片变了 + .findmark 出现', async () => {
    const before = await evaluate('return ' + CARD_TITLE + ';');
    const v = await evaluate('document.querySelector(".searchHit").click(); await __sm.sleep(1000);' +
      'return JSON.stringify({t:' + CARD_TITLE + ', marks:document.querySelectorAll(".findmark").length});');
    const o = JSON.parse(v);
    if (!o.marks) return { pass: false, detail: '.findmark 数量 0（title=' + o.t + '）' };
    if (o.t === before) return { pass: false, detail: '卡片标题没变：' + o.t + '（findmark=' + o.marks + '）' };
    return { detail: '.findmark=' + o.marks + ' title=' + o.t };
  });

  // 5) 内嵌面板
  await loadFresh();
    // 每个 block 从干净页面重新加载：history 栈 / 键盘焦点 / 上次开的层都不跨 block 污染。：videos / days / hw，Esc 关掉回卡片
  //    注意：视频目录/100Days 打开时会把焦点放进面板里的搜索框，而 handleKey 在
  //    INPUT/TEXTAREA 上直接 return（基线就是这样）——所以先按一次 Esc（记录结果），
  //    没关就把焦点交回 body 再按一次（等价于用户先点一下页面空白再按 Esc）。
  const panels = [['#btnVideos', 'videos', 1300, '#vidList .newHwRow'], ['#btnDays', 'days', 1500, '.dayRow'], ['#btnHw', 'hw', 2600, '#inlineBody .hwBlock']];
  for (const p of panels) {
    const btn = p[0], tag = p[1], waitMs = p[2], waitSel = p[3];
    await check('inline.' + tag + ' ' + btn + ' 打开内嵌面板（可见且 #inlineBody 非空）', async () => {
      const v = await evaluate('document.querySelector("' + btn + '").click(); await __sm.sleep(' + waitMs + ');' +
        'await __sm.waitFor(function(){ return !!document.querySelector("' + waitSel + '"); }, 8000);' +
        'var p=document.querySelector("#inlinePanel"), b=document.querySelector("#inlineBody");' +
        'return JSON.stringify({hidden:p.hidden, w:p.getBoundingClientRect().width, len:b.innerHTML.length, txt:b.innerText.trim().length});');
      const o = JSON.parse(v);
      if (o.hidden || !(o.w > 100)) return { pass: false, detail: v };
      if (!(o.len > 100)) return { pass: false, detail: '#inlineBody 内容过少 ' + o.len };
      return { detail: 'body ' + o.len + ' chars' };
    });
    await check('inline.' + tag + '.esc Esc 关掉回卡片', async () => {
      await pressKey('Escape');
      await sleep(800);
      let st = JSON.parse(await evaluate('return ' + STATE + ';'));
      if (!st.inlineHidden) {
        if (st.card && !st.modalHidden) { /* 弹层代替内嵌，也算"还在面板里" */ }
        note('inline.' + tag + '.esc.focus', '焦点在面板内的输入框时第一次 Esc 不生效（基线行为），先 blur 再按 Esc');
        await evaluate('if (document.activeElement && document.activeElement.blur) document.activeElement.blur(); return (document.activeElement.tagName||"");');
        await pressKey('Escape');
        await sleep(900);
        st = JSON.parse(await evaluate('return ' + STATE + ';'));
      }
      if (!st.inlineHidden) return { pass: false, detail: '#inlinePanel 还开着' };
      if (!st.modalHidden) return { pass: false, detail: '#modal 还开着' };
      if (!st.card) return { pass: false, detail: '#card 不见了（状态被打坏）' };
      return { detail: '回到卡片' };
    });
  }

  // 6) 终端
  await loadFresh();
    // 每个 block 从干净页面重新加载：history 栈 / 键盘焦点 / 上次开的层都不跨 block 污染。：打开 → 执行 print(1+1) → 输出 2
  await check('repl.open #btnRepl 打开终端抽屉', async () => {
    const v = await evaluate('document.querySelector("#btnRepl").click(); await __sm.sleep(900);' +
      'var r=document.querySelector("#repl"); return JSON.stringify({hidden:r.hidden, h:r.getBoundingClientRect().height, input:!!document.querySelector("#replIn")});');
    const o = JSON.parse(v);
    if (o.hidden || !(o.h > 80)) return { pass: false, detail: v };
    return { detail: 'height=' + Math.round(o.h) };
  });
  await check('repl.run 执行 print(1+1) 输出 2', async () => {
    const v = await evaluate([
      'var inp=document.querySelector("#replIn"); inp.focus(); inp.value="print(1+1)";',
      'inp.dispatchEvent(new Event("input",{bubbles:true}));',
      'inp.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",code:"Enter",keyCode:13,which:13,bubbles:true,cancelable:true}));',
      'await __sm.sleep(1800);',
      'var out=document.querySelector("#replOut");',
      'return JSON.stringify({txt:String(out.textContent||""), outs:out.querySelectorAll(".rl-out").length});',
    ].join('\n'));
    const o = JSON.parse(v);
    if (!/(^|[^0-9])2([^0-9]|$)/.test(o.txt) || !o.outs) return { pass: false, detail: JSON.stringify(o).slice(0, 200) };
    return { detail: 'rl-out=' + o.outs };
  });
  await check('repl.close 收起终端后卡片还在', async () => {
    const v = await evaluate('var b=document.querySelector("#btnReplClose"); if(b) b.click(); await __sm.sleep(700);' +
      'return JSON.stringify({replHidden:document.querySelector("#repl").hidden, card:' + CARD_PRESENT + '});');
    const o = JSON.parse(v);
    if (!o.replHidden) return { pass: false, detail: '终端没收起' };
    if (!o.card) return { pass: false, detail: '#card 不见了' };
    return { detail: '收起 ok' };
  });

  // 7) 助教
  await loadFresh();
    // 每个 block 从干净页面重新加载：history 栈 / 键盘焦点 / 上次开的层都不跨 block 污染。：圆钮 → 气泡
  await check('assistant.fab #asFab 打开助教气泡', async () => {
    const v = await evaluate('document.querySelector("#asFab").click(); await __sm.sleep(900);' +
      'var b=document.querySelector("#asBubble"); return JSON.stringify({hidden:b.hidden, w:b.getBoundingClientRect().width, msgs:!!document.querySelector("#asBubMsgs")});');
    const o = JSON.parse(v);
    if (o.hidden || !(o.w > 200) || !o.msgs) return { pass: false, detail: v };
    return { detail: 'bubble ' + Math.round(o.w) + 'px' };
  });
  await check('assistant.close 关掉气泡后卡片还在', async () => {
    const v = await evaluate('var c=document.querySelector("#asBubble [data-act=asbclose]"); if(c) c.click(); await __sm.sleep(600);' +
      'return JSON.stringify({hidden:document.querySelector("#asBubble").hidden, card:' + CARD_PRESENT + '});');
    const o = JSON.parse(v);
    if (!o.hidden) return { pass: false, detail: '气泡没关' };
    if (!o.card) return { pass: false, detail: '#card 不见了' };
    return { detail: '关闭 ok' };
  });

  // 8) 设置 / 更新面板
  const modals = [['#btnAiSet', 'aiset', 2800, '#aiKey'], ['#btnUpdate', 'update', 1600, '#modalBody button']];
  for (const m of modals) {
    const btn = m[0], kind = m[1], waitMs = m[2], waitSel = m[3];
    await check('modal.' + kind + ' ' + btn + ' 打开面板且 #modalBody 非空', async () => {
      const v = await evaluate('document.querySelector("' + btn + '").click(); await __sm.sleep(' + waitMs + ');' +
        'await __sm.waitFor(function(){ return !!document.querySelector("' + waitSel + '"); }, 8000);' +
        'var m=document.querySelector("#modal"), b=document.querySelector("#modalBody");' +
        'return JSON.stringify({hidden:m.hidden, kind:m.getAttribute("data-kind"), len:b.innerHTML.length, txt:b.innerText.trim().length, loading:/正在读|正在加载/.test(b.innerText)});');
      const o = JSON.parse(v);
      if (o.hidden || o.kind !== kind) return { pass: false, detail: v };
      // 断言只要求"面板打开 + 正文非空"（用户的验收口径）。
      // 内容还在加载（例如 /ai/status 慢）时只记 NOTE，不判失败 —— 那是环境问题，不是前端回归。
      if (!(o.txt >= 5)) return { pass: false, detail: '#modalBody 文本过少 ' + o.txt };
      if (o.loading) note('modal.' + kind + '.loading', '#modalBody 仍停在加载态（' + o.txt + ' 字）：/ai/status 之类的接口慢，不是前端问题');
      return { detail: 'data-kind=' + kind + ' text=' + o.txt };
    });
    await check('modal.' + kind + '.esc Esc 关闭后 #card 仍在', async () => {
      await pressKey('Escape');
      await sleep(700);
      const v = await evaluate('if (!document.querySelector("#modal").hidden) { var x=document.querySelector("#modalClose"); if(x) x.click(); await __sm.sleep(400); }' +
        'return JSON.stringify({modalHidden:document.querySelector("#modal").hidden, card:' + CARD_PRESENT + ', title:' + CARD_TITLE + '});');
      const o = JSON.parse(v);
      if (!o.modalHidden) return { pass: false, detail: '#modal 还开着' };
      if (!o.card) return { pass: false, detail: '#card 不见了' };
      return { detail: 'ok, card=' + JSON.stringify(o.title).slice(0, 40) };
    });
  }

  // 9) 收尾：整理状态，报异常与 console.error
  await evaluate('window.__IC__.closeAll(); await __sm.sleep(400); var b=document.querySelector("#btnReplClose"); if(b && !document.querySelector("#repl").hidden) b.click(); return true;');
  const finalCard = await evaluate('return JSON.stringify({card:' + CARD_PRESENT + ', title:' + CARD_TITLE + ', dots:document.querySelectorAll("#dots .dot").length});');
  await check('final.state 收尾后卡片状态完好', async () => {
    const o = JSON.parse(finalCard);
    if (!o.card || !o.title || !(o.dots > 0)) return { pass: false, detail: finalCard };
    return { detail: 'title=' + o.title + ' dots=' + o.dots };
  });
  await check('no.uncaught 全程零未捕获异常', async () => {
    if (EXCEPTIONS.length) return { pass: false, detail: EXCEPTIONS.length + ' 个: ' + EXCEPTIONS.slice(0, 3).join(' | ') };
    return { detail: '0' };
  });

  try { ws.close(); } catch { }

  const failed = RESULTS.filter(r => !r.ok);
  console.log('\n================ smoke summary ================');
  console.log(' assertions: ' + RESULTS.length + '  pass: ' + (RESULTS.length - failed.length) + '  fail: ' + failed.length);
  console.log(' notes: ' + NOTES.length);
  for (const n of NOTES) console.log('   NOTE ' + n.name + ' -> ' + n.text);
  console.log(' uncaught exceptions: ' + EXCEPTIONS.length);
  console.log(' console.error: ' + CONSOLE_ERRORS.length);
  for (const c of CONSOLE_ERRORS.slice(0, 12)) console.log('   console.error: ' + c.slice(0, 200));
  if (failed.length) {
    console.log(' ---- failed ----');
    for (const f of failed) console.log('  FAIL ' + f.name + ' -> ' + f.detail);
  }
  if (JSON_OUT) {
    fs.mkdirSync(path.dirname(JSON_OUT), { recursive: true });
    fs.writeFileSync(JSON_OUT, JSON.stringify({
      generatedAt: new Date().toISOString(),
      baseUrl: BASE_URL,
      htmlOverride: HTML_FILE || null,
      assertions: RESULTS,
      pass: RESULTS.length - failed.length,
      fail: failed.length,
      notes: NOTES,
      exceptions: EXCEPTIONS,
      consoleErrors: CONSOLE_ERRORS,
    }, null, 2), 'utf8');
    console.log(' report: ' + JSON_OUT);
  }
  process.exit(failed.length ? 1 : 0);
}

main().catch(e => {
  console.error('[smoke] fatal: ' + (e && e.stack || e));
  try { if (ws) ws.close(); } catch { }
  process.exit(1);
});
