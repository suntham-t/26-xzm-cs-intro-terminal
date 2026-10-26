# 视觉验证与自动化测试 harness（QA）

> 归属：**视觉验证 / 自动化测试负责人**。只写 `_redesign/` 下的文件，绝不改 `web/index.html` `app/main.py` `content/` `_dev/`。

这套工具解决两件事：

1. **可重复的多界面截图**：一次启动无头 Chrome，按剧本把 19 个 surface 一屏一屏截下来（`cap.ps1` + `cap.mjs` + `scenarios.json`）。
2. **功能回归**：真实点按钮、输文字、敲回车，25 条断言判断"改造后功能一个不少"（`smoke.mjs`）。

---

## 1. 一分钟上手

前置：Chrome 在 `$env:LOCALAPPDATA/Google/Chrome/Application/chrome.exe`，node 22+（内置 fetch/WebSocket，**不装任何 npm 包**）。

### 1.0 先起一个"隔离 QA 实例"（推荐，也是本文所有数字的来源）

```powershell
# 自己的数据目录（进度 / AI 配置 / 更新状态都独立，不碰真实进度，也不搅和 8800 那个日常实例）
$env:LOCALAPPDATA = "$env:TEMP/qa-harness-data"
python app/main.py --no-window --port 8811
```

**为什么要单独一个实例**：截图和回归需要"每次跑都一样的运行环境"。共享的 8800 实例有它自己的进度文件、
AI 配置和更新状态，状态一漂移，`settings` / `hw` 这类面板的内容就不可复现（实测：8800 的 `ai-config.json`
被写坏过，`/health` 与 `/ai/status` 直接超时，AI 设置面板永远卡在"正在读 AI 配置…"）。
隔离实例第一次起来时数据目录是空的，19 个 surface 每次都长得一样。

> 不隔离也能跑：把下面所有 `-Port 8811` 换成 `-Port 8800` 即可，只是 `settings` / `hw` 的内容会随那个实例
> 的状态变化（版式不受影响）。**但 before 和 after 必须用同一个端口**，否则对照会掺进"数据差异"。

### 1.1 常用命令

```powershell
# ① 截"改造前"基线（用 git HEAD 的原始字节渲染，见 §3）
powershell -ExecutionPolicy Bypass -File _redesign/tools/cap.ps1 -Port 8811 -Out _redesign/shots/before -Html _redesign/baseline/index.html

# ② 截"改造后"（直接吃 dev server 当前返回的 web/index.html）
powershell -ExecutionPolicy Bypass -File _redesign/tools/cap.ps1 -Port 8811 -Out _redesign/shots/after

# ③ 功能回归（对当前 web/index.html）
powershell -ExecutionPolicy Bypass -File _redesign/tools/cap.ps1 -Port 8811 -Smoke

# ④ 功能回归（对基线做对照：基线本来就该全绿，红了说明断言写错了）
powershell -ExecutionPolicy Bypass -File _redesign/tools/cap.ps1 -Port 8811 -Smoke -Html _redesign/baseline/index.html

# 只跑一个/几个 surface（逗号分隔；-Only= 是子串匹配）
powershell -ExecutionPolicy Bypass -File _redesign/tools/cap.ps1 -Port 8811 -Scenario search,toc
powershell -ExecutionPolicy Bypass -File _redesign/tools/cap.ps1 -Port 8811 -Only=card
```

退出码：`0` = 全部成功；`1` = 至少一个剧本/断言失败，可以直接挂 CI。

产物：`_redesign/shots/{before,after}/` 下 `<surface>@<宽>x<高>.png` + `_report.json`；
`_redesign/shots/smoke-report.json`（断言明细 + console.error + 未捕获异常 + NOTE）；失败现场图在 `_redesign/shots/_fail/`。

---

## 2. 文件清单

| 文件 | 作用 |
|---|---|
| `cap.ps1` | 启动**一个**隔离无头 Chrome（独立 `--user-data-dir`、冷缓存、CDP 端口可配）→ 调 cap.mjs / smoke.mjs → 收掉自己起的 Chrome。**ASCII-only** |
| `cap.mjs` | CDP 驱动：打开页面 → 按剧本 `Runtime.evaluate` 跑多步 → 逐张 `Page.captureScreenshot` → 输出 JSON 报告；每步都能归属 console.error / 未捕获异常 |
| `scenarios.json` | 23 个 surface 的剧本（真实点击路径、等待、滚动公式、视口、断言）；含 900x620 最小窗口与章首/章末卡 |
| `scenarios-dark.json` | 深色主题的 7 个关键 surface（由上面派生：先 html[data-theme=dark] 再跑同一批步骤） |
| `smoke.mjs` | 功能回归：25 条断言，PASS / FAIL / NOTE，最后按失败数给退出码 |
| `_redesign/baseline/index.html` | 改造前 `web/index.html` 的**原始字节**（`git show HEAD:web/index.html`，与 HEAD blob `68981e7` 一致）。基线渲染的唯一来源 |
| `_redesign/shots/before/` | 35 张 before 基线（23 个 surface；关键面补 1500x1000 / 1000x760 / 900x620） |

> 备份：`_redesign/shots/_backup_tools/` 里放了本目录 4 个文件的副本。之前发生过别的队友脚本
> 把 `_redesign/tools/` 根目录白名单式清空、我的文件被 unlink 的事故，再丢就从这里还原。

---

## 3. 关键设计：为什么"改造前基线"永远截得出来

Lead 随时可能在改 `web/index.html`，所以基线**绝不能**依赖 dev server 当前返回的页面。做法：

- `_redesign/baseline/index.html` = `git show HEAD:web/index.html` 的原始字节（用 `cmd /c "git show ... > file"` 落盘 ——
  PowerShell 5.1 的 `>` 会写成 UTF-16，两次转码就毁了）。
- `cap.ps1 -Html <file>` 打开 CDP 的 `Fetch` 域，**只拦截顶层 Document 请求**（按 `frameId` 过滤，不碰页面里的
  bilibili iframe），把这份字节当 200 响应回给浏览器。
- 于是：**基线截图 = HEAD 的 HTML + 当前 dev server 的 API**。CSS/HTML 是改造前的，接口/数据是活的。
- `_report.json` 里有两个字段自证拦截生效：`htmlOverride`、`documentsServedFromOverride`（19 个剧本 = 19 次）。

同一场景同参数下：live 344036B / baseline 213804B，像素差 70% —— 说明截的确实是两份不同的实现，
不是"假基线"。

---

## 4. 可复现性（before/after 能一张张对照的原因）

任何一处"手感"都会让构图漂移，所以下面这些全部固定：

1. **一次 Chrome，每个剧本重新导航**：`Page.navigate` → 等应用的 `__IC__.ready_()` → `settle` 1200ms。
2. **视口写死**：`name@WxH` 里的 W/H 就是实际视口（`Emulation.setDeviceMetricsOverride`），切换后等 420ms 让 `onWindowResize` 收尾。
3. **开场先归一化界面状态**（`defaults.beforeJs`）：`closeAll()`、收起 REPL、宽屏确保目录开、`main.scrollTop=0`。
   > 为什么必须做：`ui.repl` / `ui.toc` 这些偏好存在**服务端进度**里 —— 一个剧本打开了终端抽屉，后面所有截图里都会多一条，
   > before/after 就没法对位了（实测踩到）。
4. **滚动用公式**：`main.scrollTop = round((scrollHeight - clientHeight) * k)` 或
   `element.getBoundingClientRect().top + main.scrollTop - gap`，常数写死。
5. **等待是固定值**（`__cap.sleep(数字)`）；只有真异步（材料栏异步渲染、课件大图解码、作业/配置加载）才用 `waitFor` + 固定收尾。
6. **命名** `<surface>@<w>x<h>.png`，同名可以直接叠图对比。

**确定性实测**（同一套工具连跑两遍，29 张逐字节比对）：

- 首轮 29 张实测：25 张**完全一致**；
- 3 张差异 < 0.01%（`days@1500` / `hw@1500` / `repl@1280`，是 1500 宽下 `#rail` 的异步内容和输入光标级别）；
- 1 张差异大：`card-video` 里的 `iframe.bili`（**B 站播放器，外部内容**，23% 像素差）。对比时请忽略该 iframe 区域。

---

## 5. 19 个 surface 是怎么点出来的

全部走页面里**真实的操作路径**（点按钮、输文字、敲键）；只有两处用应用自己的公开 API，因为 UI 上要滚 100+ 行才点得到：
`__IC__.jumpToId(id)`（在卡片流里跳到某个知识点，等价于点目录项）和 `toast('测试 toast')`（toast 本来就是全局函数，任务书也允许）。

| # | surface | 视口 | 怎么点出来的（核心步骤） | 备注 |
|---|---|---|---|---|
| 1 | `card` | 1280x880, 1500x1000, 1000x760 | 默认落地；`closeAll()` + `main.scrollTop=0` | 第 1 章第 1 个知识点，点阵 1/3 |
| 2 | `card-video` | 1280x880, 1500x1000 | 点 `#btnVideos` → 点第一条 `[data-act=vidopen]`（"看这一条"）→ 卡片跳到该分P对应知识点 | `iframe.bili` + `.videoMeta`；外部内容 |
| 3 | `card-code` | 1280x880, 1500x1000 | `jumpToId('ch02-s01-p05')` → 滚到 `#card .codeBlock` 距顶 210px | 断言 `.codeBar .tb` >= 2（可视化 / 复制） |
| 4 | `toc` | 1280x880, 1500x1000 | 确保目录开 → `main` 滚到 45% → 把 `.tocPt.here` 居中到 `#tocBody` | 3 级结构 + 当前项高亮 |
| 5 | `rail` | 1500x1000（唯一） | `jumpToId('ch01-s01-p01')`（有课件缩略图）→ 等 `#railBody` 有内容 → `main.scrollTop=0` | 1280 下 `#rail` 隐藏，只有 >=1400 出现 |
| 6 | `search` | 1280x880, 1500x1000 | 点 `#btnSearch` → `#modal .searchInput` 输入"列表" → 20 条 `.searchHit` | 命令面板形态；命中词有 `<b>` |
| 7 | `videos` | 1280x880, 1500x1000 | 点 `#btnVideos` → `main` 滚到 42% | 内嵌面板 `#inlinePanel`，164 个分P 分组 |
| 8 | `days` | 1280x880, 1500x1000 | 点 `#btnDays` → `main` 滚到 40% | 22 天列表（`.dayRow` x22） |
| 9 | `day-reader` | 1280x880 | 点 `#btnDays` → 点第一个 `[data-act=daysopen]`（"打开 >"）→ 滚到 22% | 阅读器同样落在卡片区内嵌 |
| 10 | `hw` | 1280x880, 1500x1000 | 点 `#btnHw` → `waitFor` `.hwBlock` 出现（最多 12s） | 隔离实例下本地可见 hw1；共享实例里还有 hw2/hw3/小测 |
| 11 | `hw-problem` | 1280x880 | 点 `#btnHw` → 点第一条 `.hwRow` | `readyJs` 守门：列表为空则整个剧本 SKIP 并在报告注明 |
| 12 | `repl` | 1280x880, 1000x760 | 点 `#btnRepl` → `#replIn.value='print(1+1)'` → 派发 Enter `keydown` | 断言 `#replOut` 出现 `.rl-out` 且含 `2` |
| 13 | `settings` | 1280x880 | 点 `#btnAiSet` → `waitFor` `#aiKey` 出现（最多 12s） | 隔离实例无 Key：空 Key + 余额行 + 说明，是真实状态 |
| 14 | `update` | 1280x880 | 点 `#btnUpdate` | **不点**"检查更新"，避免真打课程站 |
| 15 | `assistant-bubble` | 1280x880 | 点 `#asFab` | 无 Key：气泡是空状态提示 |
| 16 | `assistant-panel` | 1280x880 | 点 `#asFab` → 点气泡里 `[data-act=asexpand]`（展开图标） | `#modal[data-kind=assistant]` |
| 17 | `toast` | 1280x880 | 直接调 `toast('测试 toast')`，300ms 内截图 | toast 2.4s 自动消失 |
| 18 | `modal-lightbox` | 1280x880 | `jumpToId('ch01-s01-p01')` → 点 `#card .thumbRow [data-act=slide]` → 等图片 `naturalWidth>0` | `#modal[data-kind=lightbox]` |
| 19 | `empty` | 1000x760（唯一） | 窄屏：`#toc` 变 fixed 抽屉 → 点 `#btnToc` 打开，`#scrim` 出现 | 断言 `position:fixed` + 遮罩可见（抽屉 top = 顶栏高 56） |
| 20 | `empty-900` | 900x620（唯一） | 同上，但用 brief 里的**最小窗口** 900x620 | 抽屉 340 宽 + 全屏遮罩 + 抽屉自身可滚 |
| 21 | `chapter-intro` | 1280x880 | `__IC__.goto(idx)`，idx = 第一个 `kind==="intro"` 的步骤 | 章首卡：kicker + 大标题 + 知识点清单 + 开始按钮 |
| 22 | `chapter-end` | 1280x880 | 同上，`kind==="summary"` | 章末卡「本章总结」+ 材料/继续 |
| 23 | `section-end` | 1280x880 | 同上，`kind==="end"` | 小节末卡（居中 + 大图标 + 下一节按钮），**没有 h2.cardTitle** |

另外 `search` 场景额外多一张 `search-topics@1280x880.png`：把 `#modalBody` 滚到底，看「100DAYS 主题索引」那块 chip 墙（它按 CSS 排在知识点命中之后）。

新增一个 surface：在 `scenarios.json` 的 `scenarios` 里加一条（`name` / `viewport` / `shots` / `steps[]` / `note`），
`steps` 每步可以是 `{js}`（页面里 await 的 JS，已预置 `__cap` 小工具）、`{wait}`、`{key}`、`{shot}`、`{expect}`。**不用改 cap.mjs**。

---

## 6. 功能回归（smoke.mjs）断言清单

对**改造后的页面**跑，也对**基线**跑（基线全绿才说明断言写的是"既有行为"，不是给新样式量身定做）。
每个 block 之间都**重新加载页面** —— history 层栈和键盘焦点会跨 block 泄漏（实测踩到）。

| 组 | 断言 |
|---|---|
| 落地 | `#card h2.cardTitle` 有文本；`#dots .dot` > 0 |
| 翻卡 | 按 `ArrowRight` → `#dotCount` 变；点 `#btnNext` → `#dotCount` 变 |
| 目录 | `#btnToc` 能开关 `#toc`；点 `.tocPt` → 卡片标题变 |
| 搜索 | `#btnSearch` → `#modal` 可见且 `data-kind=search`；输入"列表" → `.searchHit` > 0；点第一条 → 标题变 + `.findmark` 出现 |
| 内嵌面板 | `#btnVideos` / `#btnDays` / `#btnHw` → `#inlinePanel` 可见且 `#inlineBody` 非空；Esc → 面板关、`#card` 还在 |
| 终端 | `#btnRepl` → `#repl` 可见；`print(1+1)` 回车 → `#replOut` 含 `2`；收起后卡片还在 |
| 助教 | `#asFab` → `#asBubble` 可见；关掉后卡片还在 |
| 设置/更新 | `#btnAiSet` / `#btnUpdate` → `data-kind` 对、`#modalBody` 非空；Esc/关闭后 `#card` 仍在 |
| 收尾 | `#card` 仍完好（标题 + 点阵）；**全程零未捕获异常** |

`console.error` 允许存在但会被列出来（当前基线：0 条）。"看见但不算失败"的现象记成 `NOTE`，不进失败数。

---

## 7. 已知限制（都不是 bug，但对照时要心里有数）

1. **`card-video` 的 iframe 是 B 站播放器**（player.bilibili.com），内容取决于外网和播放器状态，两跑之间 23% 像素不同。看设计请只看 iframe 边框/圆角/`.videoMeta` 那一行。
2. **`days@1500` / `hw@1500` / `repl@1280` 有 <0.01% 像素抖动**（`#rail` 异步内容、输入光标闪烁），属正常。
3. **Esc 在输入框聚焦时不生效**（基线行为）：视频目录 / 100Days 打开时焦点被放进 `#vidQ` / `#daysSearch`，而 `handleKey` 在 `INPUT/TEXTAREA` 上直接 return。smoke 里先 blur 再按 Esc（等价于用户点一下空白处），并记一条 `NOTE`。**如果新版本顺手修了这个，NOTE 会消失，断言依旧通过。**
4. **搜索跳转后 history 层栈会留一层**（基线行为）：`closeModal()` 不清 `LAYER_STACK`，所以"搜索→点结果→开视频目录→Esc"会退回搜索面板。smoke 靠每 block 重载规避；这不是新样式引入的。
5. **AI 相关面板只能截到空状态**：隔离实例没配 API Key（`assistant.ready=false`），`assistant-bubble` / `assistant-panel` / `settings` 显示的是"未配置"的真实状态，不是占位图。
6. **进度会被写**：应用把"当前在哪一张卡"存进 `%LOCALAPPDATA%/course-terminal/progress.json`。用 §1.0 的隔离实例就完全不碰真实进度；直接对 8800 跑会改那个实例的进度（浏览器 profile 是隔离的，localStorage 不受影响）。
7. **共享 8800 实例可能"半瘫"**：它的 `ai-config.json` 被写坏后 `/health` 与 `/ai/status` 会超时（页面本身还能开）。这不是前端问题，但会让 `settings` 面板卡在 loading —— 所以验证统一走隔离实例。
8. **只截 viewport**：整页（full）能力在 `cap.mjs` 里实现了（`steps[].shot` / `shots[].full`），但 19 个 surface 当前都用 viewport —— 阅读面本来就该看"一屏"。
9. **搜索面板的两段结果有先后**：100DAYS 主题索引（`.searchTopics`）按设计排在知识点命中之后，20 条命中之后要滚动才看到 —— 单独截了一张 `search-topics@1280x880` 留证，不要以为它不见了。
10. **Chrome 版本**：只验证了本机 Chrome 155。换大版本可能字形/滚动条宽度微变（`--hide-scrollbars` 已开）。

---

## 8. 幂等与清理（不会踩到用户）

- 每次跑：先杀掉**命令行里带自己 `--user-data-dir`** 的 chrome 进程（绝不按进程名通杀用户的 Chrome），再删 profile 目录 → 冷缓存。
- CDP 端口被占（不是我们的）→ 自动 `CdpPort+1` 重试，最多 20 次；启动失败/中途异常都在 `finally` 里收进程。
- 输出目录里上一轮的 `*.png` 先删掉（防止失败时旧图冒充新图），`_report.json` 每次覆盖。
- 零第三方依赖、不写注册表、不装包。

---

## 9. 报告字段（`_report.json`）

```jsonc
{
  "generatedAt": "...", "baseUrl": "...", "htmlOverride": "基线时的 baseline/index.html 或 null",
  "documentsServedFromOverride": 19,
  "total": 19, "failed": 0, "skipped": 0, "shotCount": 29,
  "scenarios": [{
    "name": "search", "desc": "...", "note": "...", "ok": true, "ms": 4573, "skipped": false,
    "viewport": [1280, 880],
    "shots": [{ "file": "search@1280x880.png", "bytes": 155705, "w": 1280, "h": 880 }],
    "steps": [{ "i": 2, "desc": "type keyword", "kind": "js", "ok": true, "ms": 712, "value": 20 }],
    "consoleErrors": [], "exceptions": [], "logErrors": [], "warnings": []
  }]
}
```

每步的 `value` 就是那一步 JS 的返回值（命中条数、滚动位置…），方便定位"哪一步开始不对"。
`console.error` / 未捕获异常按**步骤归属**记录；任一剧本出现未捕获异常 → 该剧本 `ok:false` → 退出码 1。

---

## 10. 硬规矩（写给自己，也写给以后改这套工具的人）

1. 只写 `_redesign/`；不碰 `web/index.html` `app/main.py` `content/` `_dev/`。
2. `.ps1` **ASCII-only**（PowerShell 5.1 按 GBK 读无 BOM 脚本）；中文只进 `.mjs / .json / .md`。
3. 不开真浏览器窗口（`--headless=new`），不装 npm 包。
4. 清理只按 `--user-data-dir` 匹配自己的进程。
5. 截图必须幂等：同名同构图，重跑覆盖。

---

## 11. 深色主题截图

深色是**正式功能**（图标栏倒数第二个按钮 = 主题切换，localStorage key `ic.theme.v1`），所以照旧走"真实状态"：
`scenarios-dark.json` 里每个剧本的第一步先执行 `document.documentElement.setAttribute("data-theme","dark")`，
其余步骤和亮色完全一样。

```powershell
# 1) 先截亮色
powershell -ExecutionPolicy Bypass -File _redesign/tools/cap.ps1 -Port 8811 -Out _redesign/shots/after

# 2) 再截深色（单独目录：cap.mjs 每次会清空输出目录里的 png）
powershell -ExecutionPolicy Bypass -File _redesign/tools/cap.ps1 -Port 8811 -Scenarios _redesign/tools/scenarios-dark.json -Out _redesign/shots/_after_dark

# 3) 把深色图并进 after/，名字已经是 <surface>@dark@<w>x<h>.png
Get-ChildItem _redesign/shots/_after_dark -Filter *.png | ForEach-Object { Move-Item $_.FullName _redesign/shots/after/ }
Copy-Item _redesign/shots/_after_dark/_report.json _redesign/shots/_reports/after-dark.json
Remove-Item -Recurse _redesign/shots/_after_dark
```

深色只截 8 个关键面：**card / search / videos / hw / repl / assistant-panel / settings / toast**
（card、search、videos、hw 补 1500x1000；repl 补 1000x760；其余 1280x880）。search 还会多一张 `search-topics@dark@1280x880.png`（主题索引块）。

深色漏白自检：扫"背景亮度 > 190 且面积 > 4000px^2 的非图片元素"。当前 8 个深色 surface 的结果是 **0 处漏白**
（`#toast` 例外：深色下它是浅底深字的反色 pill，见 §7 已知限制）。
