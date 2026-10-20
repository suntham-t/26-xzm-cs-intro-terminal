# 智能计算概论学习终端 —— 冻结规格 v1

> 本文件是**唯一接口约定**。四个并行工作必须严格遵守，不得擅自改字段名、改目录。

---

## 0. 用户已拍板的决定（不可推翻）

| # | 决定 |
|---|---|
| 1 | **桌面端**：pywebview + PyInstaller，**双击快捷方式即用** |
| 2 | **不要开机自启**（关窗即退出） |
| 3 | **UI：卡片流**（一次只看一个知识点，上下翻） |
| 4 | **视频按 B站分P标题对应**（不碰时间戳） |
| 5 | **长期使用，课件每周更新** → 必须能增量更新 |
| 6 | **黑马没讲的，尽量用 Python-100-Days 补**（文字补，不是视频） |
| 7 | **100-Days 有用的那部分 pull 到本地**，可离线直接读 |
| 8 | **讲义用原稿切开，一字不改**（不做改写、不做总结） |
| 9 | **要能激发学习兴趣**（见第 6 节，克制地做，不要徽章雨） |
| 10 | **OpenJudge 也嵌进去**（openjudge 的题目页/提交页） |

---

## 1. 目标与验收标准

做完第 1 批，用户应该能：

1. 双击桌面快捷方式 → 弹出原生窗口，**没有黑终端**
2. 看到 ch01~ch03 的全部知识点卡片流，**正文就是讲义原文**
3. 每张卡片有：视频（有就给）/ 100Days 对应篇 / 讲义出处 / 课件页原图 / **「▶ 在可视化里跑这段」**
4. 点「跑一下」→ **同一个窗口内**切换到我们做好的可视化，并**预填代码**
5. 能打开 100Days 的本地副本直接读
6. 能嵌 OpenJudge 做题
7. 进度看得见、有连续学习天数、学完一节有收尾

---

## 2. 目录与文件边界（**每个代理只能改自己的目录**）

```
D:\opencode\course-terminal\
├── SPEC.md                 ← 本文件（谁都不许改）
├── content\                ← 【代理 A】内容管道
│   ├── ch01.json  ch02.json  ch03.json
│   ├── videos.json
│   └── slides\ch01\*.png  slides\ch02\*.png  slides\ch03\*.png
├── content\100days\        ← 【代理 B】100Days 本地化
│   ├── Day01-初识Python.md ...
│   └── index.json
├── app\                    ← 【代理 C】桌面壳 + 打包
│   ├── main.py
│   ├── build.ps1
│   └── requirements.txt
└── web\                    ← 【代理 D】卡片流 UI
    ├── index.html
    └── tutor\              ← 由 app 启动时挂载，D 只写一个占位说明
```

**禁止跨目录改文件。** `SPEC.md` 只读。

> 现有的可视化引擎在 `D:\opencode\tools\pytutor\`（`pytracer.py` / `explain.py` / `server.py` / `viewer.html`），
> **已经做好、经过 61 项测试，不要改它**。终端通过 `sys.path` 复用它。

---

## 3. 数据契约（冻结）

### 3.1 `content/chNN.json`

```jsonc
{
  "chapter": "ch03",
  "title": "Python入门",
  "source": {
    "notes_url": "https://csintro2026.zhengmao.ltd/notes/ch03.md",
    "notes_sha256": "ab12…",
    "slides_url": "https://csintro2026.zhengmao.ltd/slides/ch03.pdf",
    "slides_sha256": "cd34…",
    "slides_pages": 90,
    "fetched_at": "2026-09-26T02:00:00+08:00"
  },
  "sections": [
    {
      "id": "ch03-s05",
      "no": 5,
      "title": "基本输入输出",
      "slide_range": [41, 51],
      "points": [
        {
          "id": "ch03-s05-p03",
          "no": 3,
          "title": "输入输出的细节",
          "level": 3,
          "body_md": "（讲义原文，一字不改）",
          "notes_lines": [924, 948],
          "slides": [44],
          "pitfall": null,
          "video": null,
          "refs": [ { "kind": "100days", "label": "Day11 字符串", "url": "100days/Day11-字符串.md" } ],
          "run": "'  hello  '.strip()"
        }
      ]
    }
  ]
}
```

**字段硬规定**

| 字段 | 规则 |
|---|---|
| `id` | **`chNN-sMM-pKK`**，MM/KK 补零。**必须稳定**——重新生成时同一小节必须得到同一个 id，否则用户进度会丢 |
| `body_md` | **讲义原文原样**（允许去掉最外层标题那一行）。**不许改写、不许总结、不许精简** |
| `notes_lines` | 该知识点在 `notes.md` 里的 **1-based 起止行号**，闭区间 |
| `slides` | 该知识点覆盖的课件页码（1-based）。靠讲义里的 `<!-- SLIDE -->` 标记推算 |
| `pitfall` | 若讲义里有 `>` 引用块形式的"点坑/提醒"，抽成纯文本；没有就 `null` |
| `video` | 见 3.2；**没有对应视频就 `null`，不许硬塞** |
| `refs` | 相关的 100-Days 篇 / 其他链接 |
| `run` | 可选：一段能体现这个知识点的**可运行代码**（1~3 行），给「跑一下」按钮预填 |

### 3.2 `content/videos.json`（视频映射表）

```jsonc
{
  "bvid": "BV1qW4y1a7fU",
  "title": "黑马程序员python零基础全套教程…",
  "up": "黑马程序员",
  "total_pages": 164,
  "pages": [ { "page": 28, "title": "第一阶段-第二章-15-数据输入(input语句)", "duration": 639 } ],
  "mapping": {
    "ch03-s05-p01": { "page": 28, "confidence": 0.9, "confirmed": false },
    "ch03-s05-p03": null
  }
}
```

- `confidence`：0~1，机器匹配的把握
- `confirmed`：**只有用户确认过才 true**；UI 上未确认的要标出来
- 允许 `null`（黑马没讲）

### 3.3 `content/100days/index.json`（代理 B 产出）

```jsonc
{
  "source": "https://github.com/jackfrued/Python-100-Days",
  "days": [
    { "day": 11, "title": "常用数据结构之字符串", "file": "Day11-字符串.md",
      "bytes": 16273, "topics": ["字符串方法", "切片", "转义字符"] }
  ],
  "topic_index": { "字符串方法": [11], "列表": [8, 9], "字典": [13] }
}
```

---

## 4. 内容切分规则（代理 A）

**机械切分，不做理解**：

1. 读 `notes.md`，按行扫描
2. `## XXX` → 开一个 **section**（`no` 按出现顺序 1,2,3…）
3. `### XXX` → 开一个 **point**（`title` 去掉序号和标记，`body_md` 是它到下一个 `###`/`##` 之间的原文）
4. 若某个 `###` 的 `body_md` **超过 120 行**，把它的 `####` 子标题升级成独立 point（`level: 4`）
5. 扫到 `<!-- SLIDE -->` 标记时，记下"从此处起，后续内容对应课件下一页"
   - 用这个把每个 point 映射到课件页码区间（取该 point 覆盖范围内出现的 `<!-- SLIDE -->`）
6. `pitfall`：`body_md` 里以 `>` 开头、且含「点坑/提醒/注意/注意」等词的引用块，抽出来做纯文本（markdown 去标记）
7. **必须跳过**讲义开头的 front-matter（`---` 包起来的 jupyter 配置）和 `<style>` 块
8. `ch01`、`ch02` 也要做（从课程平台抓）

**自测要求**：
- 断言 `sum(len(section.points))` 与讲义里 `###` 的实际个数对得上（ch03 应是 66 左右）
- 断言每个 point 的 `body_md` **能在原文里按 `notes_lines` 原样取回**（逐字相等）
- 断言没有空 `body_md`
- 断言 `id` 全局唯一
- **跑两次，断言两次产出的 `id` 完全一致**（稳定性）

---

## 5. 视频映射规则（代理 A）

1. 拉 B站分P列表：`https://api.bilibili.com/x/web-interface/view?bvid=BV1qW4y1a7fU`
   （需要先访问 `https://www.bilibili.com/` 拿 cookie，带 `Referer`；用 `urllib`，别装第三方包）
2. 把每个分P标题规范化：去掉 `第一阶段-第二章-03-` 这种前缀，留下知识点名
3. 对每个 point，在分P标题里找匹配：
   - 精确/包含匹配 → confidence 0.9
   - 关键词重叠（中文分词可以偷懒：按 2-gram 或直接子串）→ 0.6~0.8
   - 找不到 → `null`
4. **过滤掉非知识点分P**：标题含「案例 / 练习 / 课后 / 综合 / 拓展 / 回顾 / 导学」的，除非没有别的候选
5. 一个分P可以对应多个 point（允许）
6. 输出 `videos.json`，并**生成一份人可读的 `content/mapping-review.md`**：表格形式，列出「知识点 → 分P标题 → 置信度」，让用户过一遍

**已知事实（不用再查）**：黑马标题里**完全没有**这些 → 直接给 `null`，别硬凑：
`编译 / 解释器原理 / 字节码 / PEP8 / 缩进 / goto fail / 报错 / Traceback / 异常处理 / try / 调试 / OJ / 评测 / split / join / strip / swapcase / isclose / 动态类型 / 强类型 / 哈希`

---

## 6. UI 规格（代理 D）—— 卡片流 + 克制的激励

### 6.1 布局

```
┌─────────────────────────────────────────────────────┐
│ 计算概论 B · ch03 Python入门      🔥 连续 3 天        │  ← 顶栏
│ [☰ 目录] 第 5 节 基本输入输出  ●●●○○○○○ 3/8  [🔍]    │
├─────────────────────────────────────────────────────┤
│                                                     │
│   卡片区（一次一张，居中，最大宽度 ~760px）             │
│                                                     │
├─────────────────────────────────────────────────────┤
│      [ ← 上一条 ]    [ ✅ 学完了 ]    [ 下一条 → ]     │
└─────────────────────────────────────────────────────┘
```

### 6.2 一张卡片

从上到下：

1. **视频区**（有视频时）：B站官方 iframe
   `//player.bilibili.com/player.html?bvid=BV...&page=N&autoplay=0&high_quality=1`
   视频下面一行小字：`黑马 · 第一阶段-第二章-15-数据输入(input语句)`
   **没有视频时**：换成一条提示条
   `⚠️ 黑马这套没讲这块 → 看下面文字`
2. **标题**：`第 5 节 · 知识点 3` + `输入输出的细节`
3. **正文**：渲染 `body_md`（markdown → HTML，只支持标题/列表/代码块/行内代码/粗体/链接；**先转义再渲染**）
4. **点坑**（有 `pitfall` 时）：黄底警告条
5. **「🧪 跑一下」块**：显示 `run` 代码 + `[ ▶ 在可视化里跑这段 ]` 按钮
6. **参考区**：`📖 Python-100-Days · Day11 字符串`（点击在站内打开本地副本）+ `📄 讲义 notes.md:924-948` + `课件 P44`
7. **课件页缩略图**：点击放大

### 6.3 激励设计（**克制**，只做这四样）

1. **进度点阵**：顶栏一串小圆点/小方块代表本节全部知识点，学一个点亮一个（像 GitHub 贡献图）。**这是主要激励，不要更多。**
2. **🔥 连续学习天数**：当天学完 ≥1 个知识点算一天。断签归零（不惩罚，只是归零）。
3. **学完一节的收尾卡**：一节最后一张卡之后出现
   ```
   🏁 第 5 节 完成
   你学了 8 个知识点，跑了 3 段代码，用了 12 分钟
   [ 进入第 6 节 → ]
   ```
4. **「继续上次」**：打开时如果上次没学完，顶部一条 `[继续 第5节 · 第4个知识点 →]`

**明确不要做**：弹窗徽章雨、签到奖励、排行榜、音效、动画堆砌。

### 6.4 其他硬要求

- 全部中文；白底；和 `tools/pytutor/viewer.html` **视觉一致**（同一个设计语言）
- 单文件 `web/index.html`（内联 CSS+JS，**零外部依赖**）
- 键盘：`←` `→`（或 `J` `K`）翻卡，`空格` 标记学完
- 进度存 `localStorage`（代理 C 会把它落盘，你只要用 localStorage）
- 数据来源：`fetch('content/chNN.json')`、`fetch('content/videos.json')`、`fetch('content/100days/index.json')`
- **「▶ 在可视化里跑这段」** 点击后：跳到 `/tutor?code=<urlencoded>`（代理 C 负责让 `/tutor` 接受 `code` 参数并预填）
- OpenJudge：单独一个「做题」面板/卡片，`iframe` 嵌 `http://cs101.openjudge.cn/` 或 `xzmdsa.openjudge.cn`。
  **先测 iframe 能不能嵌**（对方可能发 `X-Frame-Options`）；**嵌不了就退化成大按钮「去 OpenJudge 做题」+ 新窗口打开**，不要假装能嵌。

---

## 7. 桌面端规格（代理 C）

### 7.1 `app/main.py`

```python
# 伪代码，说明结构
import threading, webview, sys, os
sys.path.insert(0, r"D:\opencode\tools\pytutor")   # 复用现成引擎
import pytracer, explain                             # noqa

# 起一个 ThreadingHTTPServer（线程里跑）
#   GET  /                 → web/index.html
#   GET  /content/...      → content/...
#   GET  /tutor            → tools/pytutor/viewer.html（接受 ?code= 预填）
#   POST /run              → 复用 pytracer + explain
#   GET  /health
# 然后 webview.create_window(...) 打开 http://127.0.0.1:<port>/
```

要求：
- **端口自动探测**（从 8770 起找空闲），不要写死
- 只监听 `127.0.0.1`
- `/tutor` 要能把 `?code=...` 传给 viewer.html（实现方式：读 viewer.html，把 code 注入成一个 `window.__PRESET_CODE__`，或者加一个 query 参数让 viewer 自己读；**推荐后者**：给 viewer 加一段只在存在 `?code=` 时生效的启动逻辑——但 `viewer.html` 不许改，所以用前者：**服务端注入一小段 `<script>window.__PRESET_CODE__="…"</script>` 到 viewer.html 的 `<head>` 后**，然后由代理 D 在 `web/index.html` 里……**不行，viewer 不认识这个变量**。
  → **最终方案**：`/tutor` 返回一个**极简的包装页**，里面放一个 `iframe` 指向真正的 `viewer.html`，并通过 `postMessage` 把 code 传进去；**如果 viewer 不响应 postMessage，就退化成"复制代码 + 打开 tutor"**。这个问题留给 C 和 D 协商，SPEC 只规定：**点「跑一下」必须能在同一个窗口里看到可视化，且代码已预填**。实现方式由 C 定，D 配合。
- 窗口关闭 → 进程退出（不做托盘、不做自启）

### 7.2 `app/build.ps1`

用 PyInstaller 打包成单个 exe：
```
pyinstaller --noconfirm --onefile --windowed \
  --name "计算概论学习终端" \
  --add-data "..\web;web" --add-data "..\content;content" \
  --add-data "<pytutor 目录>;tutor" \
  main.py
```
- 生成桌面快捷方式
- 打包后**必须实测**：双击 exe 能开窗、能翻卡、能跑代码

### 7.3 `app/requirements.txt`
```
pywebview
pyinstaller
```
（`@napi-rs/canvas` 那些是 Node 的，无关）

---

## 8. 100Days 本地化（代理 B）

1. **pull 有用于本课程的部分**：`Day01-20` 全部 + `Day21-30` 里挑和计概相关的
   （`21.文件读写和异常处理.md`、`30.正则表达式的应用.md` 值得要；Excel/PDF/邮件那些不要）
2. 源：`https://raw.githubusercontent.com/jackfrued/Python-100-Days/master/Day01-20/XX.YY.md`
   （**注意**：文件名里有中文和点号，要 URL 编码；之前踩过坑）
3. 存成 `content/100days/DayNN-简短名.md`（**文件名用 ASCII + 中文混排是允许的，但不要有空格**）
4. 产出 `index.json`（见 3.3），`topics` 是你从正文里抽的关键词（**20 个以内**）
5. 还要 pull **31 个 100Days 之外但更贴的**？**不要**，就 100Days。
6. **图片处理**：md 里引用 `res/...png`，本地没有 → **把图片链接改写成 GitHub 上的绝对 URL**
   `https://raw.githubusercontent.com/jackfrued/Python-100-Days/master/Day01-20/res/...`
   （联网时能显示，离线时显示裂图，可接受）

---

## 9. 自测通用要求（每个代理都要给证据）

- 不许说"应该能跑"，**必须贴真实命令输出**
- 临时文件放 `$env:TEMP`，**不许在项目目录留临时脚本**
- Python 用 `python`（3.13.15）
- 前端：`node --check` 通过 + 元素 id 交叉检查 0 缺失
- 数据：用 `python -c` 或临时脚本断言字段完整性、id 唯一性、稳定性

---

## 10. 现成可用的东西（别重复造）

| 东西 | 位置 | 状态 |
|---|---|---|
| 可视化引擎 | `D:\opencode\tools\pytutor\` | ✅ 已完成，61 项测试全绿，**只读复用** |
| ch03 课件 PNG（90 页） | `D:\opencode\course\ch03\pages\` | ✅ 已有，可直接拷到 `content\slides\ch03\` |
| ch03 讲义 | `D:\opencode\course\ch03\notes.md` | ✅ 已有 |
| ch03 课件 PDF | `D:\opencode\course\ch03\slides.pdf` | ✅ 已有 |
| 100Days Day01-13 | `D:\opencode\course\p100days\` | ✅ 已有 13 篇，缺 14-20 |
| 黑马分P列表 | 见第 5 节 API | 已拉过，164 条 |
| PDF 渲染脚本 | `D:\opencode\course\_tools\render-pdf.mjs` | ✅ 可用（pdfjs + @napi-rs/canvas） |

---

## 11. 交付时每个代理要回的话

1. 改了哪些文件（只列自己目录里的）
2. 自测的**真实输出**
3. 有没有破坏契约
4. 已知问题 / 没做到的
