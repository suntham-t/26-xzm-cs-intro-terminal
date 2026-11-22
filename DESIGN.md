# 前端设计系统 v3（2026-11：可读性 + 提交安全）

> 适用范围：`web/index.html`（单文件：HTML + 内联 CSS + 内联 JS，零外部依赖）。
> 分片在 `_redesign/parts/*.css`、`_redesign/shell.html`、`_redesign/src/app.js`（由补丁链生成），
> 用 `python _redesign/tools/apply.py` 拼成单文件。

## 1. v3 改了什么

| 维度 | v2 | v3 |
|---|---|---|
| 三级字色 | 3.5:1 | `#5E6A7C`，5.49:1（淡底 4.84） |
| 最弱一档 | 当文字用（2.1:1） | 只做装饰（分隔符、marker、滚动条、禁用） |
| 语义色 | ok 3.05 / err 4.24 | ok `#067647` 5.13 / err `#B42318` 5.76 |
| 正文段距 | 一句一行 `<br>` 拼成整段，段距从未生效 | 按句末标点重新分段，段距 1.15em（只对讲义/题面开） |
| 材料栏断点 | 1400（主卡被挤到 700px） | 1580（60+296+840+48+336） |
| 左栏 | 10 个纯图标 | ≥1400 加 10.5px 文字标签 |
| 卡片 kicker | 只报位置 | 「讲义原文 · 一字未改」，位置降为次要 |
| 自动提交 | 一个蓝按钮，来源只在 title 里 | 常显「将提交：…」+ 题面内确认块（钉住待提交代码） |
| 弹层 / toast | 无 dialog 语义、无 aria-live | `role="dialog" aria-modal` + 焦点进出；toast 报给读屏 |
| 小窗 | 静默裁掉面包屑 | `min-width:900px` 护栏（产品自定下限 900×620） |

## 2. 结构

```
body（横向 flex）
├─ #sideBar 60px（≥1400 时 76px）  品牌块 + 读物工具 ‖ 资源面板 ‖ 系统（搜索/更新/主题/AI/帮助）
└─ #rightPane
   ├ header 56px     品牌 › 章 › 节 + 连续天数
   ├ #resume 38px    「继续上次」（有书签才出现）
   ├ #shell           #toc 296px ‖ main（唯一纵向滚动）‖ #rail 336px（≥1580 才出现）
   ├ #repl           深色终端抽屉（高度由 ui.replh 内联控制）
   └ footer 60px     翻卡 + 点阵 + 计数 + 快捷键提示
```

层级（固定契约，只从 token 取）：遮罩 40 / 终端 45 / 图标栏 52 / 弹层 60 / 助教圆钮 70 / 气泡 75 / toast 80 / tooltip 90。

## Colors

唯一权威在 `_redesign/parts/00-tokens.css`；组件只引用变量，深色只覆盖 token。

**文字四级（v3 起全部过 AA）**

| token | 浅色 | 对比度（白底 / 淡底） | 用途 |
|---|---|---|---|
| `--c-text` | `#131A26` | 15.8 / 14.6 | 正文 |
| `--c-text-2` | `#4B5668` | 7.4 / 6.9 | 次级正文 |
| `--c-text-3` | `#5E6A7C` | 5.49 / 4.84 | 所有小字：坐标、计数、提示、小节标题、占位符 |
| `--c-text-4` | `#A8B2C1` | 2.1 —— 不是文字色 | 纯装饰 |

深色：`--c-text-3:#8794AA`（5.68:1）、`--c-text-4:#66738A`（装饰）。

**语义**：`--c-ok:#067647`（soft 底 5.13）、`--c-warn:#B45309`、`--c-err:#B42318`（5.76）；深色 `#34D399`、`#F0B25A`、`#FF8A80`。

**面与线**：`--c-canvas` 应用底、`--c-surface` 卡面、`--c-surface-2` 代码/表头、`--c-surface-3` hover/选中、
`--c-surface-4` 按下；`--c-line` 发丝线、`--c-line-2` 卡内分隔、`--c-line-strong` 可点边界。

**导航脊**：`--c-rail:#101728`、`--c-rail-2` hover、`--c-rail-3` 选中、`--c-rail-fg:#93A2BF`（≥6:1）。

**终端**（不跟主题）：`--c-term`、`--c-term-2`、`--c-term-3`、`--c-term-fg`、`--c-term-fg-dim`、
`--c-term-accent`（提示符青蓝）、`--c-term-err`、`--c-term-ok`。

> 验收只有一条：承载文字的配对 ≥ 4.5:1（大字 ≥ 3:1），用脚本按 WCAG 相对亮度算，别目测。

## Typography

- `--font-read`：中文正文必须宋体；拉丁衬线放在前面（CSS 逐字符匹配：英文命中 Georgia，中文落到宋体）。
- `--font-ui`：按钮 / chip / 计数 / 章节号 / 提示。小字号留在无衬线（宋体太细，10–12px 会糊）。
- `--font-mono`：代码 / 终端 / 行号 / 时长。
- 正文：宋体 17.5px、行高 1.95、行宽上限 `--measure-read:42em`（中文约 42 字一行）。
- **中文正文不用 `font-weight:600`**：SimSun 只有 400 与 700，中间字重靠算法合成，屏幕发糊。
- 段距用 `.body p{margin:0 0 1.15em}`，不用 `<br>` 造间距。
- 小于 12px 的文字一律用 `--c-text-3` 及以上。

## Components

| 组件 | 选择器 | 要点 |
|---|---|---|
| 阅读卡 | `#card` `#card .cardTitle` `.body` | 840px；标题衬线 28px；正文 42em；顶部 3px 渐变发丝线是**顶部**装饰 |
| kicker | `.kicker` | 12px 无衬线 + 5px 圆点；内容「讲义原文 · 一字未改」+ 位置（`.secTitleInl`） |
| 提示条 | `.warnbar` | 默认暖色 / `.novideo`（灰字 + 2px 线，104 张卡里 76 张有）/ `.info` / `.err` |
| 点阵 | `#dots` `.dotCount` | 计数写「本节 1 / 3」；内嵌面板开着时清空（它属于卡片） |
| 连续天数 | `.streak` | 0 天说「今天翻一张卡，开始记连续」，不显示 0 |
| 左栏按钮 | `.sb` + `data-label` | 40×40；≥1400 变 56×52 并显示 10.5px 标签 |
| 内嵌面板 | `#inlinePanel` | 打开时卡片让位、底栏翻卡停用（否则一点就退出面板） |
| 弹层 | `#modal` | `role="dialog" aria-modal aria-labelledby="modalTitle"`；焦点搬进 `#modalBody`，关闭还原 |
| 提交确认 | `.subConfirm` | 题面内展开（不是弹层）；显示来源 + 代码前 3 行；确认后提交 `HW.pendingSubmit` |
| 来源行 | `.probHead .subSrc` | 自动提交按钮左侧常显「将提交：…」；AI 来源用 `--c-warn` |
| 终端 | `#repl` `.termIco` | 唯一深色内容面；头部是终端字形（不再是三个窗口圆点） |
| 空/错态 | `.loadCard` `.errList` | 加载给骨架，出错列清单 + 重载 |

## 6. 布局契约

- 断点 **1100**（目录常驻/抽屉）、**1580**（材料栏常驻），必须与 JS 的 `TOCOPE_W`、`RAIL_W` 一致。
- 最小窗口 900×620，`html` 与 `body` 上写了 `min-width` 与 `min-height`（小于它出滚动条，不静默裁剪）。
- 宽度分配 60 + 296 + 840 + 48 + 336 = 1580，任何一档加宽都要重算。
- `main` 是唯一纵向滚动容器；`#toc`、`#rail` 各自滚动。

## 7. 图标

- 84 个图标在 `_redesign/icon-kit.js`（已内联为 JS 的 `ICONS`），`icon('search')` → 一段 svg；
  规格 `viewBox 0 0 24 24`、描边 1.8、圆头圆角、`currentColor`。
- emoji 由 `uiEmojiSwap()` 自动换成图标包壳；正文、代码、终端输出、AI 回复里的 emoji 属内容，不动（`EMOJI_SKIP`）。
- `settings` 用"三横+三钮"不用齿轮（20 齿在 16px 必糊）。

## 8. 主题

- `<html data-theme="light|dark">`，`applyTheme()` 只改这一个属性，不动颜色值。
- 偏好存 `localStorage['ic.theme.v1']`，三态（浅 / 深 / 跟随系统）；手动选过就不再跟随。
- 深色不是反相：纸面 `#141A26`（纯黑 + 白字读长文太累），发丝线半透明白，强调色提亮一档。

## 9. 动效

只动 `opacity` 与 `transform`，120–280ms，位移 ≤ 6px；全部在 `prefers-reduced-motion` 下退化为零。

## 10. 落地

改样式进 `_redesign/parts`；改结构/文案进 `_redesign/shell.html` 或新增 `_redesign/patches/NNNN-*.json`；
然后 `python _redesign/tools/patch_js.py` → `python _redesign/tools/apply.py`。
补丁的 `old` 必须恰好出现一次，任何一条失败整链不写（fail-closed），所以不会留下半套改动。
`apply.py` 自检：单文件结构、零外部依赖、CSS 花括号与注释配平、id 交叉检查、`node --check`、class 覆盖。

## 11. 验收

- `_redesign/tools/cap.ps1 -Port 8811 -Smoke`：25 条功能断言。
- `_redesign/tools/cap.ps1 -Port 8811 -Out _redesign/shots/after`：23 个 surface 的真实点击截图（1280/1500/1000/900 与深色）。
- `npx impeccable detect <url> --viewport 1440x900`：确定性规则体检。当前基线 0 条 low-contrast；
  仅剩 `side-tab`（目录引导线，误报）与 `dark-glow`（品牌方块，有意为之）。
