// drive.mjs —— 通过 Chrome DevTools Protocol 驱动无头浏览器：
//   打开页面 → 在页面里执行一段 JS（比如点「运行」、点几次「下一步」）→ 截图存盘
//
// 用法:
//   node drive.mjs <url> <out.png> [等待毫秒] [页面里执行的JS]
//
// 前置: Chrome 必须已经带 --remote-debugging-port=9223 启动（由 shot.ps1 负责）。
// 依赖: Node 22+ 内置的全局 WebSocket 和 fetch，零第三方包。

import fs from 'node:fs';

const PORT = process.env.CDP_PORT || '9223';
const [, , url, out, waitMsArg, evalJsArg] = process.argv;

// 页面里要执行的 JS 优先从文件读（避免命令行引号地狱）
let pageJs = evalJsArg || '';
if (process.env.PAGE_JS_FILE && fs.existsSync(process.env.PAGE_JS_FILE)) {
  pageJs = fs.readFileSync(process.env.PAGE_JS_FILE, 'utf8');
}

if (!url || !out) {
  console.error('用法: node drive.mjs <url> <out.png> [等待毫秒] [页面JS]');
  console.error('   或: 设 PAGE_JS_FILE=<js文件> 代替第 4 个参数');
  process.exit(2);
}
const waitMs = Number(waitMsArg || 2500);
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function targets() {
  const res = await fetch(`http://127.0.0.1:${PORT}/json/list`);
  return res.json();
}

// 等 Chrome 的调试端口起来
let list = null;
for (let i = 0; i < 40; i++) {
  try { list = await targets(); break; } catch { await sleep(250); }
}
if (!list) { console.error('连不上 Chrome 调试端口', PORT); process.exit(1); }

let page = list.find(t => t.type === 'page');
if (!page) { console.error('没有 page target'); process.exit(1); }

const ws = new WebSocket(page.webSocketDebuggerUrl);
let seq = 0;
const pending = new Map();
// 页面里【未捕获】的异常与 console.error：光看 Runtime.evaluate 的
// exceptionDetails 抓不到 setTimeout / 事件回调里抛出来的那些（它们不在调用栈里）。
const PAGE_EXCEPTIONS = [];
const PAGE_CONSOLE_ERRORS = [];

ws.addEventListener('message', ev => {
  let msg;
  try { msg = JSON.parse(ev.data); } catch { return; }
  if (msg.method === 'Runtime.exceptionThrown') {
    const d = msg.params && msg.params.exceptionDetails;
    const txt = (d && (d.exception && d.exception.description || d.text)) || JSON.stringify(d);
    PAGE_EXCEPTIONS.push(String(txt).slice(0, 400));
    console.error('页面未捕获异常:', String(txt).slice(0, 400));
    return;
  }
  if (msg.method === 'Runtime.consoleAPICalled' && msg.params && msg.params.type === 'error') {
    const a = msg.params.args || [];
    PAGE_CONSOLE_ERRORS.push(a.map(x => (x && (x.value !== undefined ? x.value
      : (x.description || x.type))) ).join(' ').slice(0, 300));
    return;
  }
  if (msg.id && pending.has(msg.id)) {
    const { resolve, reject } = pending.get(msg.id);
    pending.delete(msg.id);
    if (msg.error) reject(new Error(JSON.stringify(msg.error)));
    else resolve(msg.result);
  }
});

const send = (method, params = {}) => new Promise((resolve, reject) => {
  const id = ++seq;
  pending.set(id, { resolve, reject });
  ws.send(JSON.stringify({ id, method, params }));
});

await new Promise((resolve, reject) => {
  ws.addEventListener('open', resolve, { once: true });
  ws.addEventListener('error', () => reject(new Error('WebSocket 连接失败')), { once: true });
});

await send('Page.enable');
await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', {
  width: Number(process.env.PAGE_W || 1500), height: Number(process.env.PAGE_H || 1000), deviceScaleFactor: 1, mobile: false,
});
await send('Page.navigate', { url });
await sleep(waitMs);

if (pageJs) {
  const r = await send('Runtime.evaluate', {
    expression: pageJs,
    awaitPromise: true,
    returnByValue: true,
  });
  if (r.exceptionDetails) {
    console.error('页面 JS 抛异常:', JSON.stringify(r.exceptionDetails).slice(0, 400));
  } else {
    console.log('  页面 JS 返回:', JSON.stringify(r.result && r.result.value));
  }
  await sleep(900);
}

const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
fs.writeFileSync(out, Buffer.from(shot.data, 'base64'));
const size = fs.statSync(out).size;
console.log(`  已截图 ${out}  (${size} 字节)`);
console.log(`  未捕获异常数: ${PAGE_EXCEPTIONS.length}` +
  (PAGE_EXCEPTIONS.length ? ' -> ' + JSON.stringify(PAGE_EXCEPTIONS.slice(0, 5)) : ''));
if (PAGE_CONSOLE_ERRORS.length)
  console.log(`  console.error: ${JSON.stringify(PAGE_CONSOLE_ERRORS.slice(0, 5))}`);
ws.close();
// ★ 退出码保持 0：这份文件被别的验收脚本共用，不能让一个新打印项改变它们的判断。
process.exit(0);
