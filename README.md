# 计算概论学习终端

PKU《计算概论 B》的**离线桌面学习终端**：把课程平台的讲义与课件、B 站视频、Python-100-Days、代码可视化、内置终端、OpenJudge 作业和 AI 讲解，装进一个 pywebview 原生窗口。双击即用，没有黑终端窗口。

- 内容来源：课程站 `csintro2026.zhengmao.ltd`（讲义 + 课件，权威）+ B 站「黑马程序员」Python 全套教程（视频讲解）+ Python-100-Days（文字补充）
- 形态：Windows 桌面 app，单进程，只监听 `127.0.0.1`，关窗即退出（无托盘、无开机自启）
- 状态：个人自用项目，仍在迭代。缺口清单见 [NEXT-STEPS.md](NEXT-STEPS.md)，接口契约见 [SPEC.md](SPEC.md)

---

## 组成

| 部分 | 位置 | 说明 |
|---|---|---|
| 桌面壳 | `app/main.py`（约 6000 行） | 一个进程干三件事：`ThreadingHTTPServer` + pywebview 窗口 + 复用可视化引擎 |
| 前端 | `web/index.html`（单文件，约 410 KB） | 卡片流 UI，零外部依赖；由桌面壳在返回时注入「导航桥」脚本（文件本身不改） |
| 内容 | `content/` | 讲义 markdown、课件 PNG、知识点 JSON、视频映射、作业、100days |
| 可视化引擎 | **不在本仓库** | `pytracer` / `explain` / `viewer.html` 是独立项目，见「运行」 |

---

## 现在能做什么

**卡片流**（一次只看一个知识点，上下翻）

- ch01~ch03 共 **104 个知识点**：讲义原稿按知识点切开，**正文一字不改**，渲染 markdown 原文
- 每张卡配：视频（映射到的 B 站分 P）／ 100Days 对应篇 ／ 讲义行号 ／ 课件原图缩略图（可放大）／ 可一键运行的代码片段
- 左栏常驻目录，右栏材料区；窄屏自动收成抽屉
- 进度点阵 + 连续学习天数 + 位置书签

**三种学习方式**

| 场景 | 入口 |
|---|---|
| 系统学一个知识点 | 卡片流：视频 + 讲义原文 + 课件原图 |
| 搞懂一段代码怎么跑 | 卡片上的「▶ 在可视化里跑这段」→ 同窗口打开可视化并预填代码 |
| 随手试一行 | 顶栏「🐍 试一试」→ 底部终端，**变量留在会话里**，报错给中文解释，防死循环 |

**搜索**

- 顶栏「🔍」跨全部章节搜**标题 + 正文**，命中行带章号（"ch03 · 第 5 节 · 知识点 3"）；点一下跳到那张卡，并把命中的词在正文里**高亮**出来
- 同一个搜索框也搜 100Days 的 287 个主题，点 chip 直接打开那一天

**作业与 AI**

- 从课程 OJ 抓作业（题号／通过率／截止），内联做题；`content/homework/hw1.json` 里已存 6 道题的题面、样例、边界用例、解析、参考代码
- 「测一测」：代码**草稿自动落盘**（`ic.hwdraft.v1`，按题存；关窗口、去可视化回来都还在）；参考解收在折叠块里，不预填进代码框
- **边界用例**：抓来的作业没有人工用例，点一下「🤖 生成边界用例」——AI 出输入，**期望输出由本机跑它给的参考解算出来**（跑不通的用例直接丢弃，不给你不可信的对错）；「🏁 全跑一遍」把当前代码对全部用例跑一遍，只展开没过的
- **提交助手**：「📤 复制并去提交」= 复制代码 + 打开这道题的提交页（提交那一下仍然由你点）；交完可以标「✅ AC / ❌ WA」，列表上出现自己的状态点
- **通过率是实时的**：数字来自每道题的 OJ 统计块（提交次数 / 尝试人数 / 通过人数），打开面板就把所有题集重抓一遍（每份 30 秒缓存、并发 5 个），面板开着时每 30 秒刷当前题集；右上角那行「通过率：N 秒前更新 · 点我刷新」可以手动刷。抓不到时保留上一次的数字，不会清空
- **自动提交**：「🚀 自动提交」= 用你自己的 OJ 账号直接交这道题，并把评测结果（AC/WA/CE…、内存、耗时）读回来。登录一次即可（密码只在登录时发给 OJ，**不落盘**；本机只留 session cookie），结果会自动同步到「✅ AC / ❌ WA」标记。第一次点会先说明一次，同意后不再问
- 「解析」由 DeepSeek 现场生成；生成的代码会**自动验证**：语法检查 → 用样例真跑 → 跑边界用例 → 不过就带着「代码+输入+期望+实际」回喂 AI 修一次；跑不动则标「无法自动验证」而不冤枉它
- 「✨ 全部生成解析」是两段式：先确认「生成 N 题？」，跑起来之后题目页头上能「⏹ 停止」，不会一按就跑完一整本
- AI 回复里每段 python 代码块自带 `▶ 在可视化里跑` / `🧪 用样例测` / `📋 复制`
- 右下角常驻「🤖 助教」：带上下文的多轮对话；`/ai/models` 动态拉模型列表；响应有本地缓存；`/ai/balance` 查余额

**内容更新**

- `/update/check`：快路 `HEAD` + `ETag`/`Last-Modified` 预筛，`?deep=1` 再逐份下整份算 sha256；同时读课程站的章节目录，**站上新增的整章**单独报出来（`new_chapters`）
- `/update/rebuild`：下载讲义/课件 → PDFium 抽页 → 渲染 PNG → 重切知识点 → 落盘（实测 ch03 90 页 35 s），产物**下一次请求就生效**；新章走同一条路，装完写进章节表
- 资源**三层逐文件回落**：exe 同级目录 → `%LOCALAPPDATA%` → 打包内嵌。所以改 UI 或换 `content/` **不必重打包**，放旁边就行
- 抓回来的作业写在第 2 层（可写层），不会丢

---

## 运行（源码）

前置：Windows + Python 3 + 网络（抓作业/查更新才需要）。

```powershell
pip install -r app\requirements.txt      # pywebview / pyinstaller / pypdfium2
python app\main.py                       # 开窗
python app\main.py --no-window           # 只起 HTTP，调试用
python app\main.py --port 8800           # 指定起始端口
```

- 端口从 **8770** 起试 40 个（8770–8809），全被占则交给内核随机；实际端口写入 `%TEMP%\course-terminal-port.txt`
- 日志：`%TEMP%\course-terminal.log`
- 自检：`GET /health` —— 端口、日志路径、引擎是否可用、REPL 限额、助教是否已配 key

> ### ⚠️ 可视化引擎要自己放
> 开发模式的引擎路径**写死在** `app/main.py` 的 `DEV_PYTUTOR`（默认 `D:\opencode\tools\pytutor`），需要该目录下有 `pytracer.py`、`explain.py`、`viewer.html`。换机器要改这一行。
> 缺引擎时：窗口和卡片流照常，只有 `/tutor` 与 `/run` 不可用（`/health` 的 `engine.error` 会说明原因）；**REPL 与 `/run-raw` 不受影响**。

---

## 打包成 exe

```powershell
powershell -ExecutionPolicy Bypass -File app\build.ps1
# 可选： -Clean  -NoShortcut  -SkipDeps  -Name "计算概论学习终端"
```

- 产物：`app\dist\计算概论学习终端.exe`（PyInstaller onefile，约 **147 MB**，内含 web/content/引擎）+ 桌面快捷方式
- `build.ps1` 必须保持 **UTF-8 with BOM**：Windows PowerShell 5.1 读无 BOM 的 `.ps1` 会按 GBK 解码，中文直接解析失败
- **exe 不进仓库**（超过 GitHub 单文件 100 MB 硬限制），发布在 Release 里
- 已构建版本：[Releases · v1.1.1](https://github.com/suntham-t/26-xzm-cs-intro-terminal/releases/tag/v1.1.1) —— `course-terminal-1.1.1-win64.exe`（154.7 MB，内含 web/content/引擎；双击即用）
- 历史版本：[v1.1.0](https://github.com/suntham-t/26-xzm-cs-intro-terminal/releases/tag/v1.1.0) · [v1.0.0](https://github.com/suntham-t/26-xzm-cs-intro-terminal/releases/tag/v1.0.0)（后者附 `course-terminal-manual-1.0.0.pdf` 使用说明书）

---

## 目录结构

```
course-terminal/
├─ app/
│  ├─ main.py              桌面壳：HTTP 路由 + 窗口 + REPL + AI + 作业 + 更新
│  ├─ build.ps1            PyInstaller 打包 + 快捷方式
│  ├─ requirements.txt
│  ├─ assets/              图标等
│  └─ dist/                打包产物（.gitignore 排除）
├─ web/
│  ├─ index.html           卡片流 UI（单文件）
│  └─ tutor/               占位；运行期挂载引擎的 viewer.html
├─ content/
│  ├─ ch01.json ch02.json ch03.json   知识点数据（17 / 21 / 66 个点）
│  ├─ videos.json          B 站视频目录 + 知识点→分 P 映射
│  ├─ notes/               讲义 markdown 原文 + 重建脚本
│  ├─ slides/              课件原图 PNG（62 + 90 + 90 = 242 张）
│  ├─ images/              讲义配图（179 张）
│  ├─ homework/            hw1.json（6 题）+ 抓题脚本
│  ├─ 100days/             Python-100-Days 本地副本（23 篇 markdown）
│  └─ mapping-review.md    视频匹配待确认表
├─ SPEC.md                 冻结的接口/目录契约
├─ NEXT-STEPS.md           续办单：当前进度与待办
└─ 计算概论学习终端-使用说明书.pdf
```

---

## 内容数据

### `content/chNN.json`

```jsonc
{
  "chapter": "ch03", "title": "Python入门",
  "source": { "notes_url": "...", "notes_sha256": "...", "slides_url": "...",
              "slides_sha256": "...", "slides_pages": 90, "fetched_at": "..." },
  "sections": [{
    "id": "ch03-s05", "no": 5, "title": "基本输入输出", "slide_range": [41, 51],
    "points": [{
      "id": "ch03-s05-p03", "no": 3, "title": "输入输出的细节", "level": 3,
      "body_md": "（讲义原文，一字不改）",
      "notes_lines": [924, 948],       // 对应讲义行号
      "slides": [44],                  // 对应课件页
      "pitfall": null, "video": null,  // video 目前全部为 null，视频走 videos.json
      "refs": [{ "kind": "100days", "label": "Day11 字符串", "url": "100days/Day11-字符串.md" }],
      "run": "'  hello  '.strip()"      // 卡片上的可运行片段
    }]
  }]
}
```

### `content/videos.json`

- 只挂**一个**合集：`BV1qW4y1a7fU`（黑马程序员，164 分 P），不下载、不碰时间戳，播放走 B 站
- `mapping` 的 key 是 `"chNN|<知识点标题>"`，与知识点 id 解耦（讲义增删小节不会整体错位）
- 每条映射里的 `videos[]` 带 `level`（`basic` 基础 / `main` 主线 / `extra` 补充 / `adv` 拔高）、`confidence`、`confirmed`
- **现状：28 个知识点已映射**，其余知识点视频为空 —— 卡片上安全降级（不显示视频，不报错）。机器匹配未经人工逐条确认，待确认表见 `content/mapping-review.md`

---

## HTTP 接口

只监听 `127.0.0.1`，**无鉴权**——本机任何进程都能调用。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` `/index.html` | 卡片流首页（注入导航桥） |
| GET | `/health` | 自检：端口、日志、引擎状态、REPL 限额、助教就绪 |
| GET | `/tutor` `/viewer.html` | 可视化界面（`?code=` 预填） |
| GET | `/content/...` `/web/...` | 静态资源（走三层回落） |
| GET | `/open?url=` `/open/count` | 外链交给系统浏览器（仅 http/https 白名单） |
| GET | `/progress` | 读学习进度 |
| GET | `/ai/status` `/ai/models` `/ai/balance` | AI 配置状态、模型列表、余额（`?refresh=1` 强制打上游） |
| GET | `/homework/available` | 可用作业列表（`?refresh=1` 重抓） |
| GET | `/update/check` `/update/status` `/update/rebuild/status` | 内容更新检查（`?deep=1&wait=1&refresh=1`） |
| POST | `/run` | 追踪执行（pytracer，5000 步上限，30 s 墙钟，忙则 503） |
| POST | `/run-raw` | 直接 exec，不追踪 |
| POST | `/repl` `/repl/complete` `/repl/reset` | 有状态终端：200 万步 / 5 s / 64 KB 输出上限 |
| POST | `/progress` | 写进度（2 MB 上限） |
| POST | `/ai/config` `/ai/chat` `/ai/explain` `/ai/cache/clear` | 配置、流式对话、代码解析、清缓存 |
| POST | `/homework/fetch` `/update/rebuild` | 抓题、一键重建 |
| POST | `/homework/cases` | 边界用例：`{hw,no,peek?}` 读缓存 / `{hw,no}` 生成（AI 出输入 + 本机跑参考解算期望输出）|
| POST | `/homework/submit` | 自动提交：`{hw,no,code}` → 用已登录的 OJ session 提交，轮询公开状态页读回评测结果 |
| GET/POST | `/oj/status` `/oj/login` `/oj/logout` | OJ 登录状态、登录（账号/密码只在这一次请求里出现）、退出（删 cookie）|
| GET | `/homework/stats?hw=hw2` | 实时通过率；`hw=all` 刷全部题集，`force=1` 绕过 30 秒缓存 |

**并发约定**：`/run` 与 REPL **共用同一把全局锁**（`ENGINE_LOCK`）。它们会替换进程级的 `sys.stdout`/`sys.stderr`/`sys.settrace`，并发会让两边的输出互相污染——所以宁可串行。终端会话是有状态的，这也是它必须串行的另一个原因。

---

## 数据落在哪

| 内容 | 路径 |
|---|---|
| 学习进度、WebView2 storage | `%LOCALAPPDATA%\course-terminal\progress.json` 与 `...\webview` |
| AI 配置（key / base_url / model / thinking） | `%LOCALAPPDATA%\course-terminal\deepseek.json` |
| 自动抓的作业等可写内容 | `%LOCALAPPDATA%\course-terminal\content\...` |
| AI 生成的边界用例（每题一个 json） | `%LOCALAPPDATA%\course-terminal\homework-cases\...` |
| OJ 登录状态（只有 session cookie，没有密码） | `%LOCALAPPDATA%\course-terminal\oj-session.json` |
| 上一次 OJ 登录的诊断（status/result/message，不含密码） | `%LOCALAPPDATA%\course-terminal\oj-login-last.json` |
| 日志 / 端口 | `%TEMP%\course-terminal.log` / `%TEMP%\course-terminal-port.txt` |

- 「读过哪张卡 + 连续天数」只存在 WebView2 的 localStorage（`ic.days.v1`：`days[]` + 位置书签）；`progress.json` 是砍掉进度机制之前的遗留，现在只读不写
- key 只存在那个 json 里：原子写 + Windows `icacls` 收紧权限 + **日志与报错统一打码**（`sk-****`），不进源码也不进 exe
- 想重置进度：删掉 `%LOCALAPPDATA%\course-terminal`（注意里面也有 B 站登录 cookie，删了就掉登录态）

---

## 已知限制

| 限制 | 说明 |
|---|---|
| **可视化引擎不在仓库内** | 需自备 pytutor 目录并改 `DEV_PYTUTOR`；缺它时只有可视化与 `/run` 不可用 |
| **本地 `content/` 是快照，会落后课程站** | 仓库里这份是 2026-09-26 的快照；课程站 10-14 更新了 ch03、10-20 新增 ch04「计算机系统」。用「🔄 检查更新」装新章 / 重建旧章即可（见上一节），不必重打包 |
| 视频覆盖不全 | 28/104 个知识点有映射，且为机器匹配、未经人工确认 |
| 终端挡不住 C 层卡死 | `time.sleep(10**9)` 这类不在 5 s 内返回，会占住那把锁；`/health` 与卡片流不受影响 |
| 终端是块级的，不是逐行执行 | 敲完 `for …:` 会进 `...` 续行，补齐缩进回车才执行（和真 Python REPL 一致）；从编辑器整段粘进来最省事 |
| 外链走系统浏览器 | 刻意的：WebView2 里未处理的 `window.open` 会开出没有地址栏/返回键的子窗口，把用户困住 |
| OpenJudge 不能内嵌 | 对方发 `X-Frame-Options: SAMEORIGIN`，面板里给了跳转按钮和复制链接 |
| 自动提交依赖 OJ 的页面结构 | 走的是「登录 → 提交表单 → 轮询状态页」，OJ 改版可能失效；失败会明说原因，不会假装提交成功 |
| 课件文字是图 | 课件渲染成 PNG，不可选中、不可搜索 |
| 只在 Windows 上验证过 | 用到 `icacls`、`os.startfile`、WebView2 |
| 没有测试套件 / 没有 LICENSE | 开发期的自测脚本不在仓库内 |

---

## 第三方材料与版权

| 来源 | 用在哪儿 |
|---|---|
| 课程站 `csintro2026.zhengmao.ltd` | 讲义原文（markdown）、课件（渲染为 PNG）——以原稿为准 |
| B 站「黑马程序员」Python 全套教程 `BV1qW4y1a7fU` | 视频讲解，仅保存分 P 元数据与链接，不下载视频 |
| Python-100-Days | 本地化副本，补黑马没讲到的点 |
| 本地 pytutor（`pytracer` / `explain` / `viewer.html`） | 代码追踪与可视化 |

本仓库目前**私有**：里面包含课程讲义与课件原图。若要转公开，请先确认上述材料的再分发许可。

---

## 相关文档

- [SPEC.md](SPEC.md) —— 冻结的接口与目录契约（数据字段硬规定）
- [NEXT-STEPS.md](NEXT-STEPS.md) —— 续办单：现在做到哪、下一步做什么
- [计算概论学习终端-使用说明书.pdf](计算概论学习终端-使用说明书.pdf) —— 图文使用手册
