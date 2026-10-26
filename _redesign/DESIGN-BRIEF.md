# 前端重设计 · 设计纲要（DESIGN BRIEF）

> 项目：\`D:\opencode\course-terminal\`（计算概论学习终端，pywebview + WebView2 桌面 app）
> 目标：**UI 大改，功能一个不少**。前端是单文件 \`web/index.html\`（HTML + 内联 CSS + 内联 JS，零外部依赖）。

## 0. 铁律（违反任何一条 = 返工）

1. **零外部资源**：不许出现 \`<link \`、\`<script src\`、\`@import\`、外部字体 URL、CDN。字体只能用系统字体。
   验收脚本 \`_dev/accept.ps1\` 会检查这一条。
2. **不许改 JS 逻辑**（除非任务明确要求）：事件、请求、存储、状态机一个字节都不动。
3. **HTML 里已有的 id 一个都不能少、不能改**：\`_dev/accept.ps1\` 会做 id 交叉检查（JS 里引用到的 id 必须在 HTML 里存在）。
4. **CSS 覆盖不能倒退**：老 \`web/index.html\` 的 249 个 class 选择器，新样式必须**全部覆盖**（可以合并/重排/改外观，但不许有类失去样式）。
5. **中文正文用宋体衬线**（用户硬要求，见现文件 CSS 注释）：阅读正文 \`--font-read\`；UI 小字、按钮、计数用无衬线 \`--font-ui\`；代码用等宽 \`--font-mono\`。
6. **颜色一律走 token（CSS 变量）**，不许在组件里写死 hex/rgba —— 深色模式只覆盖 token。例外：渐变、阴影里的 alpha 可以用 \`color-mix()\` 或 rgba 但必须基于 token 色。
7. 目标渲染引擎：Chromium 155/156（WebView2 155.0.4283）。\`:has()\`、\`color-mix()\`、容器查询、\`clamp()\`、\`light-dark()\` 都可以用；不用实验特性（\`@scope\`、\`anchor-name\`）。
8. 默认窗口 **1280×880**（最小 900×620），另外要在 1500×1000 与 1100×800 下不塌。
9. \`.ps1\` 文件必须 ASCII-only（Windows PowerShell 5.1 按 GBK 读无 BOM 脚本）。\`.html/.css/.md/.js\` 一律 UTF-8。
10. 中文注释保留项目的解释性风格：**说清"为什么"，不要只复述"是什么"**。

## 1. 设计方向

**「学术工作台」**（Scholarly Workbench）——把"终端"做成一个真正像专业工具的东西：

- **深色导航脊**：最左侧 60px 图标栏是深墨蓝（\`--c-rail\`），像 IDE 的活动栏；内容区是浅色纸面。
  深色脊 + 浅色纸形成强结构对比，一眼就能看出"这是工具，不是网页"。
- **纸感阅读面**：正文区白卡 + 极淡的发丝线 + 柔和多层阴影。不用粗边框、不用大面积灰块。
- **电光蓝强调**：DeepSeek 蓝 \`--c-accent\`（#3B5BFD）。强调只出现在：当前选中、主按钮、链接、进度、kicker。
  一屏之内强调色面积要小 —— 越少越贵。
- **衬线正文 + 无衬线 UI**：正文宋体（阅读舒适、教材感）；标题 serif 大字号；eyebrow/kicker、章节号、
  按钮、chip、计数全部无衬线。这个组合是"设计感"的主要来源。
- **克制的动效**：120–200ms，位移 ≤ 6px，只做 opacity/transform。不弹跳、不旋转。
- **深色模式**：一套完整 \`[data-theme="dark"]\` token 覆盖（默认浅色）。深色下阅读面是 #12161F 系。

## 2. Design tokens（唯一权威定义在 \`parts/00-tokens.css\`）

颜色（浅色）：

| token | 值 | 用途 |
|---|---|---|
| \`--c-canvas\` | #F2F4F8 | 应用底色（卡片区外面那层） |
| \`--c-surface\` | #FFFFFF | 卡片 / 面板 / 输入框底 |
| \`--c-surface-2\` | #F8FAFD | 次级面：代码块、表格头、静态条 |
| \`--c-surface-3\` | #EDF1F7 | hover/选中底色、chip 底 |
| \`--c-rail\` | #101728 | 左侧图标栏底 |
| \`--c-rail-2\` | #18213A | 图标栏 hover |
| \`--c-rail-fg\` | #A9B6CF | 图标栏图标色 |
| \`--c-rail-fg-on\` | #FFFFFF | 图标栏选中/悬停图标色 |
| \`--c-line\` | #E2E7F0 | 发丝线（边框/分隔） |
| \`--c-line-strong\` | #CBD3E1 | 强边框（输入框、可点边界） |
| \`--c-text\` | #131A26 | 主文字 |
| \`--c-text-2\` | #4B5668 | 次文字 |
| \`--c-text-3\` | #7F8A9C | 三级文字 / 占位 |
| \`--c-accent\` | #3B5BFD | 主强调 |
| \`--c-accent-2\` | #6C86FF | 强调渐变尾 / hover |
| \`--c-accent-ink\` | #1B34C4 | 强调文字（浅底上更深） |
| \`--c-accent-soft\` | #EDF0FF | 强调浅底（选中行、chip on） |
| \`--c-ok\` / \`--c-ok-soft\` | #0E9F6E / #E6F7F1 | 通过 / AC |
| \`--c-warn\` / \`--c-warn-soft\` | #B45309 / #FFF7EA | 待确认 / 提示 |
| \`--c-err\` / \`--c-err-soft\` | #D92D20 / #FEECEB | 错误 / WA |
| \`--c-code\` | #F6F8FC | 代码块底 |
| \`--c-scrim\` | rgba(11,16,28,.42) | 遮罩 |

深色模式 token 覆盖（选择器 \`html[data-theme="dark"]\`）由 tokens 文件负责；**组件文件不许写深色规则**。

字体：
- \`--font-read\`: Georgia, Cambria, "Times New Roman", SimSun, "宋体", "Source Han Serif SC", serif
- \`--font-ui\`: system-ui, "Segoe UI", "Microsoft YaHei", sans-serif
- \`--font-mono\`: Consolas, "Cascadia Mono", "Courier New", monospace
- 字号：11 / 12 / 12.5 / 13 / 13.5 / 14 / 15 / 16 / 17 / 18 / 20 / 24 / 28（token \`--fs-*\`）
- 行高：UI 1.6，正文 1.95，标题 1.35

半径：\`--r-xs:6px --r-sm:8px --r-md:10px --r-lg:14px --r-xl:18px --r-pill:999px\`
间距：\`--sp-1:4px\` … \`--sp-8:32px\`（4 的倍数；不用 4/8 以外的奇数）
阴影：
- \`--sh-xs\`: 0 1px 2px rgba(16,23,40,.05)
- \`--sh-sm\`: 0 2px 8px rgba(16,23,40,.06)
- \`--sh-md\`: 0 8px 24px rgba(16,23,40,.08)
- \`--sh-lg\`: 0 18px 48px rgba(16,23,40,.14)
- \`--sh-focus\`: 0 0 0 3px color-mix(in srgb, var(--c-accent) 22%, transparent)
层级：遮罩 40 / 图标栏 52 / REPL 45 / 弹层 60 / 助教圆钮 70 / 气泡 75 / toast 80 / tooltip 90（沿用现有 z-index 契约，别改）

## 3. 版式骨架（由 Lead 写的 \`20-shell.css\` 负责，组件文件不要动这些容器的布局）

\`\`\`
body                       flex row, bg --c-canvas, overflow hidden
├ #sideBar                 60px 深色脊；brand 48px + 图标 44×44(r12) + spacer + 底部组
└ #rightPane               flex col
   ├ header                56px：面包屑(章 › 节) + 右 meta（连续天数 chip）
   ├ #resume               （可选）细条：继续上次
   ├ #shell                flex row, min-height 0
   │   ├ #toc              296px 白面 + 右发丝线
   │   ├ main              滚动容器；内容居中，padding 28px 24px 64px
   │   │   ├ #card         阅读卡：max-width 840px，r--r-xl，白面，--sh-md
   │   │   └ #inlinePanel  内嵌面板：同宽度同外观
   │   └ #rail             336px（≥1400px 才出现）；内部是若干"材料卡"
   ├ #repl                 底部抽屉；**深色终端面**（--c-term），高度沿用 JS 的 ui.replh
   └ footer                60px：翻卡控件 + 点阵 + 提示
\`\`\`

窄屏契约（JS 已定，CSS 必须配合）：
- \`body[data-wide="0"]\` 时 \`#toc\` 变成 fixed 左侧抽屉（宽 340，max-width 86vw），要配 \`#scrim\`。
- \`#rail.collapsed\` 时宽 44px，只剩一个 \`‹\` 按钮（\`#railTitle\`/\`#railBody\` 被 JS 隐藏或靠 CSS 收掉）。
- \`main\` 是唯一纵向滚动区（\`overflow-y:auto\`）。

## 4. 组件契约（每个 class 的"长什么样"）

### 卡片（30-card.css 负责）
- \`#card\`：白面、1px \`--c-line\`、r 18px、\`--sh-md\`；内边距 40px 48px 44px。
- \`.kicker\`：无衬线 12px、letterspacing .08em、\`--c-accent\`、前面一个小圆点/竖条（用 ::before）。
- \`h2.cardTitle\`：serif 700、28px/1.34、\`--c-text\`、下边距 20px。
- \`.body\`：serif 17.5px/1.95、\`--c-text\`；段落间距 14px；\`h4\` 级标题无衬线 15px 600。
- 代码块：\`--c-code\` 底 + 1px \`--c-line\` + r 12；\`pre\` 内 padding 14px 16px；字号 13px/1.7 mono。
  \`.codeBar\` 是代码块下方工具条：无衬线 12px、左对齐、按钮用小 pill（\`.tb\`）。
- \`.chip\`：pill（r999）、白底、1px \`--c-line\`、12.5px、hover 变 \`--c-accent-soft\` + 强调色。
- \`.warnbar\`：左 3px 强调边的浅色块（pitfall 用 warn、info 用 accent、err 用 err），r 10。
- \`.warnbar.novideo\`：**必须弱**（104 张里有 76 张），一行 12.5px 灰色 + 左侧 2px 发丝线。
- \`.slides .thumbRow\`：缩略图网格（同宽 3–4 列，gap 12），每张 r 10 + hover 抬升 + 页码角标。
- \`.emptyCard/.endCard\`：居中；\`.endIco\` 换成大号轮廓图标（用 CSS 可以做圆环/图形，不要依赖图片）。
- 视频区：\`iframe.bili\` r 12 + 1px \`--c-line\`，\`.videoMeta\` 12.5px 灰；\`.vlink\` 行 hover 浅底 + 强调色。

### 面板（40-panels.css 负责）
- \`#modal\`：遮罩 \`--c-scrim\` + \`backdrop-filter: blur(2px)\`；\`.modalBox\` r 18、\`--sh-lg\`、max-width 780、max-height 88vh。
- \`#modal[data-kind="search"]\` 做成**命令面板**：box 贴上部（\`align-items:flex-start; padding-top:10vh\`）、输入框 15px 无边框（外层 \`.searchInput\` 用一个包边容器做 focus 环）。
- \`.searchHit\`：行式结果，hover 浅底；命中词 \`b\` 用 \`--c-accent\` + 淡色底。
- \`.tocCh/.tocSec/button.tocPt\`：三级导航；\`button.tocPt\` 左侧 1px 引导线、当前项 \`--c-accent-soft\` + 左 2px 强调条 + 强调文字。\`.tocPt.done\` 绿、\`.tocPt.tocMat\` 强调。
- 作业（\`.hwHead/.hwList/button.hwRow/.hwNo/.hwRate/...\`）：行式列表，hover 抬底；\`.hwNo\` 圆形序号；\`.tabBar/button.tab\` 页签（下划线指示器）。
- \`textarea.probCode\`：深色代码面（\`--c-code\` 或更深）+ mono 13px + 行高 1.7。
- \`details.refSol\`、\`.resBox/.resGrid\`（结果表格）、\`.caseChip\`、\`.vfy\`：一律圆角卡片化、留白充足。
- \`.setRow/.setLabel/input.setInput/select.setInput\`：设置页两列表单；label 无衬线 13px 600；输入框 focus 环。
- \`.dayRow/.topicRow/.topicHit/.daysSec\`：100 Days 列表行。
- \`.xclose\`/\`.railToggle\`/\`.panelHead\`：面板头，✕ 钉右上；\`.panelHead\` 高 52px、底部发丝线。
- \`#toast\`：底部居中深色 pill（\`--c-text\` 底 / 白字，12.5px），\`--sh-lg\`。

### REPL / AI（50-ai.css 负责）
- \`#repl\`：**深色终端**（\`--c-term\` #0B1220 面，字 \`--c-term-fg\` #D7E0F0）——这是全 app 唯一的深色内容面，
  和左侧深色脊呼应。\`.replHead\` 深色、\`.replOut\` 更深、输入行深色、\`>>>\` 提示符用 \`--c-term-accent\`（青蓝 #7DD3FC）。
- \`.rl-in\`/\`.rl-out\`/\`.rl-err\`/\`.cnTitle\`/\`.cnDetail\`/\`.cnHint\` 全部适配深色（错误块用深红底）。
- \`#replComp\` 补全面板：浮层白卡（浅色），选中项强调底。
- \`#asFab\` 圆钮：accent 渐变 + 光晕，hover 上浮 2px；\`#asBubble\` 白卡 r 16 + \`--sh-lg\`。
- \`.asBubble\`（消息气泡）：assistant 用 \`--c-surface-2\` 无边框、user 用强调渐变淡底；\`.asWho\` 11.5px 灰。
- \`.asIn/.bubIn\` 输入框 focus 环；\`.asFoot\`/\`.bubInRow\` 白底 + 上发丝线。
- \`.aiStream .cursor\`/\`.asCursor\` 闪烁光标；\`.codeBlock/.codeBar\` 与卡片一致。

## 5. 图标约定（由 icon-kit 统一出）

- 一律内联 SVG，\`viewBox="0 0 24 24"\`，\`fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"\`，
  尺寸由 CSS 控制（\`.ico{width:1em;height:1em}\` 或 16/18/20px 类）。
- 颜色永远 \`currentColor\`。不许在 SVG 里写死颜色（除了极少数需要实心的：录音键那种）。
- emoji 只保留在"内容语义"里（比如正文里的 📌 不算 UI），UI 控件上的 emoji 全部换成 SVG 图标。
- 命名：\`icon("search")\` → 字符串。

## 6. 交付与拼装约定

Lead 有一个拼装器 \`_redesign/tools/apply.py\`：把
\`parts/00-tokens.css\` + \`10-base.css\` + \`20-shell.css\` + \`30-card.css\` + \`40-panels.css\` + \`50-ai.css\` + \`90-polish.css\`
按序拼成一个 \`<style>\`，配 \`shell.html\` 与（打过补丁的）JS 生成新的 \`web/index.html\`。

所以：
- 你**只写你的 css 文件**（\`_redesign/parts/<NN>-<name>.css\`），不要动 \`web/index.html\`。
- 不要写 \`:root\` 变量（tokens 已定）；需要新变量 → 在文件顶部用 \`/* NOTE: 需要 token X */\` 说明，Lead 会加。
- 不要写 \`html[data-theme="dark"]\` 规则（深色由 token 负责）。若某个组件必须深色特判（如终端面已经是深色），
  用 \`--c-term-*\` 这套 token，别写死颜色。
- 文件头部写一段中文注释：你负责的组件、设计取舍、与老 CSS 的差异。
- 每个文件自成体系、**选择器按老 CSS 的类名来**，顺序在第 N 个文件里自洽即可。

## 7. 老 CSS 的参考位置

老样式表在 \`web/index.html\` 第 7–913 行（\`<style>…</style>\`）。等价的独立副本：
\`_redesign/ref/old.css\`（Lead 已导出）。**逐条读完再写**，尤其注意那些"为什么这样写"的注释
（宋体字重、z-index 层级、footer 让位、REPL 挡不住 C 层卡死……这些都是踩过坑的结论）。
