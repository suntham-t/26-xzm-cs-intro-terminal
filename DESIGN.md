# 前端设计系统 v2（2026-10 重设计）

> 适用范围：`web/index.html`（单文件：HTML + 内联 CSS + 内联 JS，零外部依赖）。
> 源码分片在 `_redesign/`，由 `_redesign/tools/apply.py` 拼成那个单文件。
> 本文件说明"新版长什么样、为什么这么做、以后改哪里"。

## 1. 一句话概括改了什么

**从「白纸卡片 + emoji」的文档风格，换成「深色导航脊 + 纸感阅读面 + 电光蓝强调」的学习工作台。**

| 维度 | 改之前 | 改之后 |
|---|---|---|
| 结构 | 浅色图标栏 52px，顶栏挤一堆按钮 | 深墨蓝图标栏 60px（品牌块 + 三组功能 + 主题开关），顶栏只回答"我在哪" |
| 阅读面 | 白卡 760px、直边、几乎无阴影 | 白卡 840px、18px 圆角、三层柔和阴影、顶部一道渐变态发丝线 |
| 排版 | 正文宋体 17px/1.95，标题与正文同族 | 正文宋体 17.5px/1.95；**kicker 无衬线小字 + 标题 serif 28px** 形成大小对比 |
| 图标 | 大量 emoji（📋🧪🏁…），不跟主题、粗细不一 | 84 个内联线性 SVG（24×24 / 1.8 描边 / currentColor）；emoji 渲染后自动替换 |
| 终端 | 白底抽屉 | **深色终端面**（唯一允许违背纸面的地方）+ 窗口圆点 + 青蓝提示符 |
| 主题 | 只有浅色 | 浅色 / 深色 / 跟随系统，一个按钮切换，偏好记在 `ic.theme.v1` |
| 面板 | 白底弹窗 + 虚线堆叠 | 命令面板式搜索、卡片化材料栏、行式作业列表、两列表单式设置页 |
| 空/加载态 | 一句"内容还在生成中" | 会呼吸的骨架 + 圆环（加载）、清单 + 重载按钮（出错） |

## 2. 结构

```
body（横向 flex）
├─ #sideBar 60px        深色活动栏：品牌块 + 目录/试一试/可视化 ‖ 视频/100Days/作业 ‖ 搜索/更新/主题/AI
└─ #rightPane（纵向 flex）
   ├ header 56px        品牌 › 章 › 节（分隔符由 CSS 的 :not(:empty)::before 生成）+ 连续天数 chip
   ├ #resume 38px       「继续上次」浅强调横幅（有书签才出现）
   ├ #shell（横向 flex，唯一可伸缩区）
   │   ├ #toc 296px     章 / 节 / 知识点三级；<1100px 变左侧抽屉 + 遮罩
   │   ├ main           唯一纵向滚动容器；#card（840px 阅读卡）/ #inlinePanel（内嵌面板）
   │   └ #rail 336px    材料栏；>=1400px 才出现；可收成 46px 窄边
   ├ #repl              深色终端抽屉（高度由 ui.replh 内联控制，顶部可拖拽）
   └ footer 60px        翻卡控件 + 进度点阵 + 计数 + 快捷键提示
```

层级（沿用并固定下来）：遮罩 40 / 终端 45 / 图标栏 52 / 弹层 60 / 助教圆钮 70 / 气泡 75 / toast 80 / tooltip 90。

## 3. Token

唯一权威定义在 `_redesign/parts/00-tokens.css`。组件里**只许引用变量**，
深色模式只覆盖 token（组件不写 `html[data-theme="dark"]` 规则）。

| 类别 | 变量 | 说明 |
|---|---|---|
| 面 | `--c-canvas` / `--c-surface` / `--c-surface-2/3/4` | 应用底 / 卡面 / 次级面 / hover / 按下 |
| 脊 | `--c-rail` `--c-rail-2/3` `--c-rail-fg` | 深色图标栏专用 |
| 线 | `--c-line` / `--c-line-2` / `--c-line-strong` | 发丝线 / 更淡分隔 / 可点边 |
| 字 | `--c-text` → `--c-text-4` | 四级字色（4 是占位/计数） |
| 强调 | `--c-accent` `--c-accent-2` `--c-accent-ink` `--c-accent-soft(-2)` `--c-accent-line` `--c-on-accent` | 主蓝 / 渐变尾 / 浅底上的强调文字 / 浅底 / 线 / 强调上的前景 |
| 语义 | `--c-ok` `--c-warn` `--c-err`（各带 -soft/-line） | 通过 / 待确认 / 错误 |
| 终端 | `--c-term` `--c-term-2/3` `--c-term-fg(-dim)` `--c-term-accent` `--c-term-line` `--c-term-err(-bg)` | 深色面专用，两套主题下都成立 |
| 字体 | `--font-read` / `--font-ui` / `--font-mono` | 宋体正文 / 无衬线 UI / 等宽代码 |
| 字号 | `--fs-11` … `--fs-28` | 11/12/12.5/13/13.5/14/15/16/17/18/20/24/28 |
| 形状 | `--r-xs`…`--r-xl` / `--sp-1`…`--sp-16` | 圆角 6–18 / 间距 4–64 |
| 阴影 | `--sh-xs/sm/md/lg/xl` `--sh-focus` `--sh-fab` | 多层叠加，单层会显脏 |
| 动效 | `--dur-1`…`--dur-4` `--ease` | 100–280ms、`cubic-bezier(.2,.7,.3,1)` |
| 尺寸 | `--w-rail` `--w-toc` `--w-materials` `--h-header` `--h-footer` `--w-card` `--measure-read` | 改一处就够 |

### 字体三套的规矩（用户硬要求）
- **中文正文用宋体**：`--font-read` 里拉丁衬线放在宋体**前面**（CSS 逐字符匹配：英文命中 Georgia，中文没有 → 落到宋体）。
- UI 小字（按钮/chip/章节号/计数）留在无衬线：宋体比无衬线细，小字号会糊。
- 代码/终端/行号/时长用等宽。
- **不要用 font-weight:600 给中文正文**：SimSun 只有 400/700，中间字重会被算法合成加粗，屏幕发糊。用 500/700 或改用颜色/字号强调。

## 4. 布局契约（改布局前必读）

- `main` 是**唯一**的纵向滚动容器；翻卡时只有它在动（`goto()` 里会把它 scrollTop 归零）。
- 断点由 JS 决定、CSS 配合，**不要在 CSS 里再写一套**：
  - >=1100px（`TOCOPE_W`）：目录常驻左栏；否则 `body[data-wide="0"]` + 抽屉 + `#scrim`。
  - >=1400px（`RAIL_W`）：材料栏出现；用户收起时 `#rail.collapsed` 只留 46px 窄边。
- 默认窗口 1280×880（最小 900×620），所以**默认体验是"无材料栏"**：材料栏只在 1400+ 出现。
- 终端高度由 JS 写内联 `height`（`ui.replh`），CSS 只给默认值与 `min-height`。
- 窄屏抽屉的 `left` 要给图标栏让位（`left:var(--w-rail)`），否则会被 60px 的脊盖掉一条。

## 5. 组件归属（`_redesign/parts/`）

| 文件 | 负责 |
|---|---|
| `00-tokens.css` | 变量（浅/深两套） |
| `10-base.css` | 复位、button/input、滚动条、选区、焦点、`.ico`、动效关键帧 |
| `20-shell.css` | 图标栏 / 顶栏 / 三栏骨架 / 目录 / 材料栏 / 底栏 / 遮罩 / 终端盒子 |
| `30-card.css` | 阅读卡：kicker/标题/正文 markdown/代码块/跑一下/参考 chip/课件缩略图/空·收尾·章首卡/视频区/提示条/`.md` |
| `40-panels.css` | 目录三级项、弹层、搜索命令面板、作业/小测、测一测、结果框、AI 设置、100 Days、OJ 提示、vfy 徽章 |
| `50-ai.css` | 终端（头/输出/输入/补全/中文报错卡）、AI 流、助教（圆钮/气泡/完整面板）、toast |
| `90-polish.css` | 跨组件收尾：`.emo` 图标包壳、加载骨架、卡片顶部发丝线、从 JS 内联样式搬出来的小类、助教圆钮抬高 |

## 6. 图标系统

- 84 个图标在 `_redesign/icon-kit.js`（已内联进 JS 的 `ICONS`），调用 `icon('search')` → 一段 svg。
  规格：`viewBox 0 0 24 24`、描边 1.8、圆头圆角、`currentColor`、实心件显式 `fill="currentColor" stroke="none"`。
- **emoji 不手改**：`uiEmojiSwap()` 在每次 DOM 变化后（MutationObserver + rAF 合并）扫一遍文本节点，
  把 `IEMOJI` 表里的 emoji 换成图标包壳 `span.emo`。
- **豁免清单**（`EMOJI_SKIP`）：`.body`、`.md`、`pre/code`、`.replOut/.rl-out`、输入框、`.vfyBox`、`.miniPre`、`.codeBlock pre` 等 ——
  **正文、代码、终端输出、AI 回复里的 emoji 是内容，不是界面**，一律不动。
- 想加图标：往 `ICONS` 加一条路径（守住"主体落在 3–21、细节别小于 2px"），再在模板里 `icon('name')`。
- 已知取舍：`settings` 用"三横+三钮"不用齿轮（20 齿在 16px 必糊）；`broom` 是全库最勉强的一个，看着糊就换 `trash`。

## 7. 主题

- `<html data-theme="light|dark">`；`applyTheme()` 只改这一个属性 + 按钮的 aria/tip，**不动任何颜色值**。
- 偏好 `localStorage['ic.theme.v1']`：`light` / `dark` / 没有则跟随系统（并监听系统变化；用户手动选过就不再跟随）。
- 图标栏倒数第二个按钮切换；按钮里两个 SVG（太阳/月亮）靠 `html[data-theme="dark"]` 的 CSS 规则显示其中一个（不重建 DOM）。
- 深色不是浅色反相：纸面用 `#141A26`（纯黑 + 白字读长文太累）、发丝线用半透明白、强调色提亮一档。

## 8. 动效

- 只动 `opacity` / `transform`（合成层，WebView 不掉帧），120–280ms，位移 <= 6px。
- 关键帧：`fadeIn` / `riseIn`（翻卡）/ `popIn` / `blink`（流式光标）/ `shimmer`（骨架）/ `loadSpin`（加载环）。
- 所有动效都在 `prefers-reduced-motion: reduce` 下退化为零时长（骨架、加载环也停）。

## 9. 改动怎么落地

```powershell
# 1) 改样式：编辑 _redesign/parts/*.css
# 2) 改结构/文案：编辑 _redesign/shell.html 或 _redesign/patches/*.json
#    （JS 不直接改：patch_js.py 每次从 git HEAD 的干净底本 + 补丁链重新生成 src/app.js）
python _redesign\tools\patch_js.py
python _redesign\tools\apply.py          # 自检 + 写 web\index.html
python _redesign\tools\preview.py        # 预览副本 web\_pv30.html（带 base href）
```

`apply.py` 的自检覆盖：单文件结构 / 只有一个 script 块 / 零外部依赖 / **CSS 注释与花括号配平** /
JS 引用的 id 与 HTML 对齐 / 关键容器齐全 / `node --check` 语法 / 老 CSS 的 class 覆盖率。
> CSS 是静默失败的：少一个 `}` 或注释没闭合，后面一大串规则会被浏览器整段丢掉，
> 页面只是"看着有点不对"。所以配平检查是硬性验收项。

## 10. 验收

- `_dev\accept.ps1`（第 207 行起）自带的 web 静态检查：id 交叉检查、`node --check`、外部主机白名单。
- `_redesign\tools\cap.ps1`：headless Chrome 按剧本截全部界面（含 1280/1500/1000 三档、深色）。
- `_redesign\tools\shot2.ps1`：单张快照（`-Width/-Height` 生效，改自 pytutor 的 shot.ps1）。
  ★ 注意上游 `pytutor/_dev/drive.mjs` 把视口写死 1500×1000，直接用它量不出 1280/1000/900 档；`drive2.mjs` 才是按参数取尺寸的那个。
- `_redesign\tools\smoke.mjs`：功能回归（翻卡 / 目录 / 搜索 / 内嵌面板 / 终端执行 / 助教 / 设置 / 更新 / 零未捕获异常）。
