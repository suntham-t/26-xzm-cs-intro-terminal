# 计算概论学习终端 · 续办单

> **给新会话的第一句话**：读这个文件，然后从「§2 待办」接着做。
> 最后更新：2026-09-26 夜

---

## 0. 这是什么 / 在哪

**PKU 计算概论 B 的离线学习终端**：课程平台（`csintro2026.zhengmao.ltd`）当底子，
100Days + 黑马程序员 B 站视频当补充，每个知识点配视频，内嵌 AI 解析 + 代码可视化 + 终端。

```
主项目      D:\opencode\course-terminal\
可视化引擎   D:\opencode\tools\pytutor\          ← 引擎是独立项目，主项目引用它
打包产物     course-terminal\app\dist\计算概论学习终端.exe   （116 MB）
桌面快捷方式  %USERPROFILE%\OneDrive\Desktop\计算概论学习终端.lnk
```

**用户偏好**：说话简短、要看到截图、讨厌过度设计、对观感敏感、会直接报 bug。
**他报的 bug 大多不是"写错了"，是"设计和直觉对不上"** —— 这类最值钱。

---

## 1. 现在在哪一步

### 在跑的活（3 个代理）

```
内容管道（143e4c91）  视频映射重做
                      · key 从 "ch03-s05-p07" → "ch03|字符串的常用方法"
                      · 一个知识点挂【多个】视频，按 level 分级（basic/main/extra/adv）
                      · 字段名已冻结（见 §5）
                      · 覆盖目标：把"只有 1 个视频的 20 个点"补成多条
                      · 若"有多条的点"仍 < 15 就停下来报告（口径可能不对）
```

### 刚完成（等重打包）

```
✅ 引擎（cbfbcd20）    代码框缩进：Tab/Shift+Tab/整块缩进/回车继承/`:` 加层/Ctrl+Z 一次撤销
                       23 项，用 CDP 发【可信按键事件】测的
✅ C（b21a54b3）       /update/check：ETag 快路 + sha256 深检（8/8 PASS）
                       /update/rebuild 接口位已留，如实返回 rebuild_supported=false
                       ★ 它发现：课程站对默认 UA 回 403，必须带浏览器 UA
✅ D（719ac10f）       砍进度 + 位置书签 + 多视频 UI（30 套件全绿）
```

---

## 2. 待办（按优先级）

### 🔴 P1 · 一键重建落地（**方案丙**，已拍板）

```
背景：真自更新的重建链路要抽 PDF 文字 + 渲染 PNG。用户机器上没有 Node。
决定：丙 = 换纯 Python 的 pypdfium2（PDFium，Chrome 的 PDF 引擎），一个 wheel 同时
      替掉抽取与渲染两步，+8MB（exe 116MB → ~124MB）。app 本身就是 Python 进程，
      所以重建是**同进程一次函数调用**：无 subprocess、无 node、无临时解压目录。
★ 乙（把便携 node 塞进 exe，+72MB → ~200MB）**已被否**。别再往那边带。

⚠️ 本文件此前 §2 写"乙已拍板"、§5 写"乙已被否"，**互相矛盾**，以本节为准。
   代码（app/main.py 的 update_rebuild）一直是按丙写的。

已完成（丙落地）：
  1 `_build-json.py`：抽取与渲染换 pypdfium2（node 留作 fallback，`CT_EXTRACTOR=auto|pdfium|node`）
     并去掉写死的 `D:\opencode` 路径（`CT_ROOT` / `CT_TOOLS` / `CT_TMP`）
  2 `main.py`：`update_rebuild()` 同进程 import 调用；产物落可写层
  3 `build.ps1`：打入 pypdfium2（含 `--collect-data pypdfium2_raw`，它的 pdfium.dll
     是运行期动态加载的）+ 重建所需的 `_build-json.py`/注册表/id 基线/占位讲义
  4 `/health.update.rebuild_supported`、`/update/rebuild` 改成**实测**（探到才 true）
  5 可写层：`<exe 旁边>\content\` > `%LOCALAPPDATA%\course-terminal\content\` > 内嵌；
     写完立刻生效，不用重启
  6 重建产物：`content/chNN.json` + `content/slides/chNN/*.png` +
     `content/images/*` + `content/notes/_chapters.json`（**只动目标章那一份**）

★ 丙的真实死因不是"文本不等价"，是一处**原始文本匹配**（下一节详述）
★ 一条铁律：**别在重建里用 `--add`** —— 它会 `refresh_point_ids()` 重写
  `content/notes/_point-ids.txt`，那是 104 个知识点的漂移基线，重写=自证清白。
  单章重建走 `main.py` 自己编排（detect → render → save_registry → build）。

★ 打包时必须打**真讲义**，不能打占位文件。
  我曾经在 build.ps1 里放了个 299 字节的"占位讲义"（理由："重建时会从课程站取回真的"），
  于是 exe 内嵌的就是那 299 字节 —— **用户不重建的话讲义原文直接是坏的**。
  它是在验收输出里露出来的：`/content/notes/ch03.md → 299 B`（真的应是 56,657 B）。
  三章讲义加起来才 ~170KB，对 118MB 的 exe 毫无影响。
  同理必须带上 `100days/index.json`（缺它 build_refs 会静默清空所有 refs）。
  ★ 教训：一个"以后会被替换成真的"的占位文件，在"以后"到来之前**就是坏内容**，
    而没有任何断言在盯着它。要么打真的，要么根本别放。
★ 课件渲染风格已统一为 **pdfium 版（淡蓝灰底、投影很淡）**，三章一起换的
  （用户明确说"我喜欢蓝底的课件"）。只换 ch03 会造成同一门课两种风格。
  ch01/ch02 的旧 node 渲染版只留在 exe 内嵌层里（作为最后兜底），不再对外提供。

已实测（A 侧与线上那批 PNG **逐字节相同**，所以对照可信）：
  · 文字抽取：**74/242 页归一化后与 node 不同**（旧记录说"242/242 逐字相同"是错的）。
    差的是 97 处单字替换 + 15 处单字删除，全是**同一字的不同写法**，没有任何改词：
      - 16 类替换，其中 **14 类是 CJK 部首补充 U+2E80–U+2EF3**（`⻓`U+2ED3 → `长`U+957F）。
        ★ NFKC **不折**这一块（只折康熙部首 U+2F00–U+2FD5）—— 原注释把两者混为一谈了
      - 另 2 类：`戶`U+6236→`户`、`㬵`U+3B35→`胶`，NFKC 同样折不掉
      - 15 处删除：node 出 `〜`U+301C（存活），pdfium 出 `～`U+FF5E（被 NFKC 折成 `~` 后当标点删掉）
  · 但**这些差异不参与决策**：只影响锚点打分（ch01 30→31、ch02 67→68），违规恒 0
  · 渲染：**卡片投影基本消失**（A 卡片下沿亮度 72→227，B 恒 227~231，单像素差最大 155/255），
    底色由淡粉转极淡冷灰
  · 可读性零影响：最佳对齐位移 (0,0)、对比度 14.73→14.61（AA 门槛 4.5）、
    差异像素 87.5% 落在非边缘（= 填充/投影类，与字形无关）
  · 整页平均差 8.8~14.5/255
  ★ 用户已明确接受："内容和可读性一样即可"

★ 修掉的那个洞（**这次最有价值的发现**）：
  `detect_chapter()` 的议程页检测是**全脚本唯一一处直接匹配原始文本**的地方：
      agenda = [p for p in ... if AGENDA_MARK in ptext[p]]
  其余所有比较都先过 `pdf_norm()`。pdfium 在 ch02 P02 上**每个字符后都吐一个换行**，
  于是原文变成 `本 | 章 | 内 | 容`，`本章内容` 就再也匹配不上 → 丢一页 →
  content 数既不是 M 也不是 M+1 → **所有锚点窗口整体错位一位** → 检测器塌
  （锚点 67→3、弱 15→80、违规 0→1），而 `chNN.json` 照样"逐字节相同"（因为它读的是
  登记表里冻结的 non_content_pages）—— **一个假绿灯**。
  修复 = 那一处也走 `pdf_norm`（一行）。修后 node 路径零回归、pdfium 路径三章全对。
  ★ 教训：**"输出逐字节相同"不等于"引擎等价"**。这次的判据必须是
    `--selftest-detect`（两种抽取器都跑）+ 真的走一次 `--rebuild-one`。

★ 另一个会**静默损坏内容**的坑（已加护栏）：
  `build_refs()` 从 `content/100days/index.json` 算每个知识点的「100 Days 关联阅读」；
  **索引缺失时它只打印一行就静默返回空** → chNN.json 里所有 `refs` 变成 `[]`。
  而 id 数、知识点数、章节结构全正常，验收脚本（只查 id/点数/图片）一条都不报。
  → `main.py` 现在 (a) 预置该索引，缺了直接拒绝重建；
           (b) 落盘前做**内容校验**：对比新旧 chNN.json，任何"整类 list 字段被清空"都判失败。
  实测：漏掉索引时 ch03 的 `refs` 33 条 → 0 条；补上后恢复正常。

★ 用户报的 bug（已修）：作业「测一测」里点「📝 让 AI 看看我的代码」**没有任何输出**。
  查证结果：**后端完全正常**。三组真实请求（review+有代码 / review+空代码 / explain）
  分别返回 477 / 695 / 719 个事件、零 error、零 retry；`/ai/status` 里 key 与 model 都正常。
  真因在前端**布局**：这个按钮长在「测一测」页签里，而 AI 的回答渲染在「解析」页签，
  `aiRender()` 第一行就是 `if (HW.tab !== "analysis") return` —— 点了之后**不切页签**，
  于是流跑完了、字数也对（浏览器实测 `ai.text len=566 busy=false done=true err=null`）、
  屏幕上却一个字都没有。
  修复：`aiExplain()` 在发起请求前先把用户带到「解析」（`stashProbCode()` → 切 tab →
  `saveHwPos()` → `renderProblem()` → `syncProblemUrl()`，照抄既有 hwtab 分支的顺序）。
  另修同类静默失败：`aiRender()` 原来在**窗口被关掉**时也直接 return，
  现在会在"没开着别的东西"的前提下把题目窗口重新打开，别让花过 token 的回答掉在地上。
  回归断言：`accept.ps1` 新增 `11-ai-review`（**离线**跑：桩掉 `/ai/explain` 的 fetch，
  不花 token），判据是返回值必须含 `tabAfter=analysis` —— 也就是
  "点完之后用户确实被带到能看见回答的地方"。

★ 用户报的 bug（已修）：**分享给别人后，填完 API Key 显示「保存似乎没生效」**。
  真因是前端一个**永远不可能成立**的比较：
    `/ai/status` 的 `key_tail` 格式是 `"…" + key[-4:]`（**带前导省略号**）
    而 `wantTail` 是从输入框取的**裸末 4 位**
    → `String("…644c") === "644c"` 恒为 false
  → 任何真实 key（≥8 位）保存之后都会弹「保存似乎没生效，请重试」，
    **而它其实已经存进去了**（实测 `/ai/status` 回 `configured=true`、`key_tail="…644c"`）。
  为什么最坏发生在"分享给别人"时：对方填完 key 看到这句，会认为 app 坏了，AI 功能就不敢用了。
  修法：先 `replace(/^[…\.\s]+/, "")` 剥掉前导省略号再比尾串；并且把
  "没配置" 与 "末 4 位对不上" 拆成两种错误分开报（后者说明存的是另一个 key）。
  回归断言：`accept.ps1` 新增 `12-ai-key-save`（**离线且不写盘**：桩掉 POST `/ai/config`，
  真的 deepseek.json 一个字节都不动；它回读**真实**的 `/ai/status`），判据
  `saveVerdict=OK`。★ 这条判据是"修复会红"的：旧逻辑下 `aiSaveKey()` 返回 false。
  ★ 教训：**两个不同格式的字符串比较，只测过"能通过"的那一侧就上线。**
    这类 bug 的特征是"永远失败"或"永远通过" —— 写比较时一定要问：
    "这两个值的格式真的是同一个来源吗？"

★ 用户报的 bug（已修）：**「试一试」里敲完回车，光标要再点一下才能继续输入**。
  真因：`replBusy(true)` 会把输入框 `disabled = true`，而**浏览器在元素被 disable 的
  那一刻就让它失焦**。请求回来后 `replBusy(false)` 只把 disabled 去掉，**没有任何一处
  把焦点还回去** —— 于是每敲一行都要再点一次。
  实测现场（给网络注入 700ms 延迟才观测得到这个窗口；`6*7` 太快，不注入就测不到）：
      duringRun: disabled=true   focused=false   hint="正在跑…"
      afterRun:  disabled=false  focused=true                       ← 修复后
  修法：新增 `replFocus()`，在两个响应收尾处（成功 / 失败）各调一次。
  三条**不要抢用户东西**的守卫：面板没开不碰；用户正开着某个弹层不抢；
    焦点已在别的可输入元素上（比如他在搜索框打字）不动。
  **不去碰 selectionStart/End** —— 那是用户正在编辑的位置。
  回归断言：`accept.ps1` 新增 `13-repl-focus`，判据必须同时满足
  `focusedBefore && disabledDuringRun && !focusedDuringRun && focusedAfterRun && ran`
  —— 也就是**把"失焦的成因"也断言进去**，而不只是断言"最后有焦点"。
  ★ 教训：修"焦点/滚动/光标"这类问题，断言要覆盖**中间态**，否则一个
    "其实没 disable 过"的实现也会通过。

### B 站视频（用户报的三件事，已处理）

```
① 嵌入播放器不能调倍速/清晰度 —— 这是**B 站嵌入版的限制**，不是没写：
   player.bilibili.com 是简化播放器，控制条里没有倍速、也没有清晰度菜单；
   URL 参数只有 autoplay / danmaku / high_quality（high_quality 是"允许高清"，
   不是清晰度选择器）。唯一出路是给一个**去完整播放器的出口** →
   每张卡加「↗ 去 B 站看」，走 /open 交系统浏览器
   （`openExternalPreferred`：先 /open，失败才退到复制链接 —— 旧的 openExternal
   只试 window.open，而打包壳里那句基本必然失败、会退成"复制链接"，等于没解决）。
   用 www.bilibili.com 而不是 m.bilibili.com（手机版在桌面浏览器里排版很怪），
   autoplay=0（带声音的自动播放会被浏览器拦，写 1 只会看起来没反应）。

② 视频"不全"不是 UI 不全，是**数据不全**：videos.json 里 104 个知识点只有 28 个
   有映射（76 个是 null），形状还是旧的 {page, confidence, confirmed} ——
   没有 level / levels / key_scheme。前端分类渲染**早就写好了**（中文级别标签 +
   多视频列表），只是没数据所以显示不出来。
   → 28 条按契约重做：key 换成 "chNN|<知识点标题>"（稳定、不随 id 平移）；
     从分P 标题（"第一阶段-第二章-15-数据输入(input语句)"）解析
     stage/chapter/serial/clean_title/is_extra/is_review，据此分级
     （【拓展】/回顾 → extra，一章第 01 讲 → basic，其余 → main）。
     **没有凭空补那 76 个映射** —— 那是人工判断，本项目规矩是"宁可不给，也不挂错"。
   → 顶栏新增「📺 视频目录」：整套 164 个分P 全在里面，按 B 站的阶段/章分类
     （要先排序再分组，否则同一阶段会被切成几段）、可搜、已挂知识点的显示
     「看这一条」（点了跳过去）、其余显示「B站 ↗」。
     ★ 那个搜索框也带 .searchInput 类，而 onDocInput 是**按 id 分发**的 ——
       必须在里面加一支，否则打字会同时驱动全局搜索面板（实测过）。

③ **会自动失效，已修**。重建写的是 chNN.json / slides / images / _chapters.json，
   **完全不碰 videos.json**；而映射的 key 是位置式 id，会随讲义平移，
   所以更新之后推荐静默指错。
   → 重建成功后加一步 `_rebuild_videos_rekey()`：按映射原先记的 point_id 去
     重建后的 chNN.json 里重新解析标题、重拼 key。
   ★ 这里踩了一个**根本性的坑**：第一版就是按 point_id 反查 —— 实测
     **id 平移之后旧 id 仍然存在**（只是换了含义），于是查得到一个看起来合理的
     标题、changed=0、映射照样指错。位置式 id 在任何"插入/删除"之后都失去辨识力：
     它只能证明"这个位置有东西"，不能证明"还是原来那个东西"。
     → 结论：**point_id 不能当锚点**。稳定的锚点是**源视频分P 号**
       （"P4 讲的是怎么装 Python"不随讲义变），所以每条映射现在带 `src_pages`。
   ★ 沙箱实测（先设 CT_ROOT 再 import，否则读写会落在真项目上）：
       A 平移 id（标题不变）→ {remapped:0, kept:28}，未写盘（标题 key 本来就稳）
       B 改名             → {kept:27, dropped:1}（旧 key 丢掉，**不再挂错**）
       C 删除知识点       → {kept:27, dropped:1}
   ★ 改名/删除**无法自动跟随**：讲义是唯一真相，重命名不会在任何地方留下
     "我是原来那个"的痕迹。所以选"诚实丢掉"，不选"留着指错"。
   ★ 试过再加一层 `by_page`（分P 号 → 知识点），结论是**它解决不了重命名**：
     按分P 号查视频的前提是"这个知识点对应哪个分P"，而那个信息正是随重命名一起
     丢的东西。加它只会多一个用不上的字段 —— 已撤掉，别再加回来。
   ★ 顺带修：`CT_ROOT` 之前只被 ASSET_ROOTS 读、`EXE_DIR` 不读，导致沙箱测试里
     读写落在两个地方（读项目、写项目）。现在两边一致：CT_ROOT 一设，读写都进沙箱。
   ★ 验收脚本的数据完整性检查也改了：它原来要求"每个知识点都有视频映射"，
     而 76/104 本来就没有 —— 那不是错误。现在改成检查**映射的合法性**
     （每个 key 都要能落在一个真实知识点上），这才是能抓到"重建后指到错点"的判据。

④ 用户发现的第二个数据问题：**"有三节在讲字典，你只搞了两节"** —— 对的，而且
   不是字典特有。原来那 28 条映射只挑了"概念讲解"，把**练习/回顾全丢了**：
   全部 20 个「练习/回顾/总结/对比/拓展」型分P，**一个都没挂**
   （集合漏 P74、字符串漏 P70、列表漏 P66、函数漏 P53/P55、文件漏 P87 …）。
   特别说明：**不是我这一轮弄丢的** —— 我核对过原始备份，`ch03-s06-p09` 本来就只挂
   [75, 76]，`ch03-s06-p08` 只挂 [73]。是原始映射就没覆盖练习视频。
   补齐的办法（**不猜标题**）：遍历视频课程，对每个未挂的练习/回顾分P，
   往前找**最近的一个已挂分P**，它就是这个练习所属的主题 → 挂到同一个知识点，
   级别标成「补充」（不挤主线）。**只补 练习/回顾**，不动本来就没错的那 28 条。
   dry run 出 13 条提案，逐条核对理由后应用：
       P8→第一个Python程序  P13→方式二  P27→数值类型  P53→函数  P55→参数
       P66→列表的其他方法   P70→字符串的常用方法  P72→列表和元组的共同操作
       P74→集合 set         P77→字典 dict  P78/P79→字典 dict（第6节收尾）
       P117→类：定义与使用
   结果：映射条目 28（不变），**视频总数 28 → 50**。
   字典那节现在三节齐全：P75 定义 / P76 常用操作 / P77 课后练习。
   ★ 为什么不能"按序号批量补全"：实测讲义节与视频章**不是一一对应** ——
     讲义第4节「数据类型」对应视频 第二/三/六章，第6节「容器类型」对应
     第六章 9 条 + 第四章 1 条，第7节「控制流」对应 第三/四/九章。
     137 个带编号的分P 里只挂了 32 个（23%），按序号补必然挂错。
     所以只做"同主题紧邻"这一种确定性补全，其余仍留给人工。
```

### 应用图标（用户提供美术稿，「注意不要白边」）

```
产物：app/assets/icon.ico（7 帧：16/24/32/48/64/128/256）+ icon-NN.png + icon-512.png 母版
生成：python app\make-icon.py —— 脚本已进项目，图标可复现，**不要手改产物**
接入：build.ps1 加了 --icon；前置检查在图标缺失时直接 throw
      （PyInstaller 缺 --icon 会**静默**退回它自己的默认图标、不报错，
       唯一症状是"图标变回去了"，所以必须显式检查）
验收：新增第 1b 项 —— icon.ico 是多帧、7 个尺寸齐全、且 7 帧字节**都在 exe 里**

「不要白边」实际要做三件事（每条都是量出来的，不是看出来的）：
  1. 裁掉白边。美术稿是 **JPEG（24bpp，没有 alpha）**，蓝方块外有约 100px 白边：
     方块边缘在 x=100 / y=99，抗锯齿过渡约 5px。裁切点内缩 6px 落在纯蓝区域
     —— 正好压在边界上会把这层灰白过渡带进去。
  2. 方块**自己的四个角是白的**。量出来：蓝色圆弧在 r≈0.224（占边长），
     而白色一直延伸到 r≈0.266。所以圆角半径必须 **> 0.266**，否则留下月牙形白角。
     实测：用 0.225 时 256px 那帧还剩 83 个近白像素；改成 0.268 后 **0 个**。
  3. 圆角在 **512px 母版**上算好，小尺寸再从母版降采样。这样边界永远是
     "蓝 × alpha" 混合，不可能把白混进来；半透明环还刻意往画面自己的蓝
     (30,80,185) 上靠，保证外缘渐隐的是蓝色而不是白色。

验证方式（都很便宜，值得留着）：
  · 纯 Python PNG 解码器（这台机器没有 Pillow）数"边缘近白不透明像素" → 必须为 0
  · 四角 alpha 必须为 0
  · 深色底对照图看有没有白圈 → app/assets/icon-preview.png
  · exe 侧：7 帧字节都能在 exe 里 find 到；.rsrc 段 62,492 → 219,564 字节；
    系统 ExtractAssociatedIcon 抽出来与我们 icon-32.png 逐像素 **1024/1024 相同**

★ 途中踩的坑与结论：
  · System.Drawing 的 **LockBits 会让这个 pythonnet 致命崩溃**（不可捕获，
    连异常字符串都打不出来）；PresentationCore 在这台机器上**根本没有**。
    所以只能走普通 Graphics 调用 + 逐像素 GetPixel（慢，但一次性）。
  · `Graphics.DrawIcon` **读不了 PNG 压缩帧的 .ico**（渲染成彩色噪点）。
    这只影响"预览"，不代表图标坏 —— 别被它误导，要看就用 ExtractAssociatedIcon
    或直接读 PNG 帧。我一度因此以为图标不一致，实际是判据错了。
  · `ExtractAssociatedIcon` 只返回**一个 32×32 帧**（它自己就报告 32x32）。
    拿它和 256px 比逐像素必然"不一致"；要跟我们的 icon-32.png 比才公平。
  · `.ico` 用 PNG 压缩帧是合法且 Win7+ 全支持的，手写 6+16n 字节的头即可，
    不必做 BMP/DIB 帧（也就绕开了逐像素 GetPixel 的慢）。
```

### 100Days 两个问题（用户报的，已修）

```
① 从可视化返回时跳到那个 Day 的最上面
② 100Days 里的 LaTeX 没渲染
```

**① 滚动位置复原被一个字符串比较挡掉了**

代码里本来就有"离开前存 sessionStorage、回来按 URL 复原"的机制，而且它本身是好的
（实测往返 `savedTop=5478 → afterRestore=5478`）。真正的问题在守卫条件：

```
用户从「day=11 的阅读器」点可视化时，地址栏还是 "/"（阅读器是 SPA 内部叠的一层，
没写进 URL）→ 存的 url="/" ；回来时 bootUrl 是 "/?day=11"
→ if (s.url !== bu && s.url !== here) return;   ← 两段比较都不相等 → 直接放弃复原
```

改成按**路径 + 参数集合**比较（`samePlace()`）：参数名和值一样就算同一个地方，
顺序、多余的参数不影响。实测 `want=5478 got=5478`。

★ 教训：这类"保存时的视角"和"恢复时的视角"不一致的 bug，光看代码很难发现 ——
  两个字符串都"看起来是对的"。所以这次是**先测往返**（证明机制没坏），
  再测**守卫的两侧输入**，才定位到比较那一步。

**② LaTeX 没渲染：96 个公式卡在三个渲染器不支持的地方**

先量清楚（80 个行内 + 16 个块）：

| 写法 | 数量 | 原来为什么不行 |
|---|---|---|
| `\small{...}` | 73 | `\small` 不在符号表 → `renderMath` 判定"不认识"→ **整条按原文显示** |
| `\frac{}{}` | 5 + 块里多处 | 没有分式支持；且 `\frac{体重}{身高^{2}}` 分母**嵌套花括号**，正则拆不动 |
| `$$...$$` 块 | 16（5 个文件） | `inline()` 只认单个 `$`，`$$` **完全没处理** |

修法（`renderMath` 现在有明确的分步顺序，注释里写了每步为什么在那个位置）：
  · `\small`/`\large`/`\displaystyle` 这类**字号间距命令 = 空操作**（对内容没影响）
  · 分式：`\frac`/`\dfrac`/`\tfrac` → 竖排 `<span class="frac">`（inline-table，
    不用 `<table>` 免得继承 md-table 的边框和宽度）
  · `$$` 块：`renderTextBlock` 里认 `$$`（独占一行可跨多行，也能同行），
    跨行时行间补换行标记，`\begin{cases}` 靠它分行
  · 符号表 22 → 81 项（`\bar \vec \gt \lt \cdots \sum \sqrt` 等真用到却没登记的）
  · `\bar{x}` → `x̄`（组合附加符号紧跟在字母后；源码里用 `\u0304` 转义写，
    免得出现不可见的组合字符）

★ **这一轮踩了一长串顺序 bug，全部记在这里，别再犯**：
  1. `stripBraces`（脱花括号）跑在 `\bar{}` `\sqrt{}` `\text{}` **之前** →
     把 `\bar{x}` 变成 `\barx`、`\sqrt{...}` 变成 `\sqrt...` → 命令认不出来 → 整条放弃。
     **命令的参数靠花括号界定，所以脱括号必须排在它们之后。**
  2. 分式的分子/分母**就地拼 HTML** → 它们内部的 `^{2}`、`\sum` 全没被处理
     （占位符提前把内容藏起来了）。**分子分母要回到 renderMath 递归处理。**
  3. 递归做在 `extractFracs` 里（也就是在上下标替换**之前**）→ 内层先被处理成
     中间标记，外层再当普通文字转义 → 页面上出现字面的标记。
     **递归只能放在流程最后。**
  4. 上下标原来换成 `\u0001SUP\u0001` 中间标记、留到最后才变 `<sup>` →
     分式展开时把这个标记交给递归调用，**递归那一层不认识它**。
     **改成就地换 `<sup>` 并立刻屏蔽（shield）。**
  5. 屏蔽用的序号**每层从 0 开始** → 嵌套时两层的 0 号含义不同，还原张冠李戴
     （实测分母显示成 `\u00070\u0007`）。**改成全局唯一序号。**
  6. `renderFracs` 不小心写了两遍 → 第二遍把已渲染好的 HTML 当公式再跑一次。
  7. `renderMath("体重")` 会返回 null（纯中文判成"不是公式"）→ 直接拼进 HTML
     就在页面上出现字面的 **"null"**。**递归失败要按文字转义输出。**
  8. `looksLikeMath` 原来"含中文 → 不是公式"排在上下标**前面** → `身高^{2}`
     被判成非公式，递归失败、标记漏出。**上下标信号要排在前面。**
     （同时收紧：含中文时要求 `^_` 旁边有数字/括号，否则 `foo_bar` 这种标识符
      会被误判成公式。）
  9. 我自己给 `restoreScrollAfterLayer` 的 `guard` 变量忘了声明 → 严格模式下会报错。

★ 为什么这些只能靠"跑起来看"发现：`renderMath` 返回的是 **HTML 字符串**，
  "函数没抛异常"完全不能说明输出是对的。所以每次改完都在真浏览器里
  把真实材料（Day5/11/14/15/30）渲一遍，数**残留的 LaTeX 命令**和**控制标记**：
  修完 5 个 Day 全部 `rawCmd=0 dd=0 markers=0`（Day11/30 正文里那些 `\thello`
  `\syou` 是字符串转义示例，本来就该原样显示，判据里已排除）。
  验收新增第 15 项专门守这两件事（含 `\small` 行内、中文分式、嵌套根号、
  5 个 Day 的全量扫描、以及"存 `/` 恢复 `/?day=11`"的滚动往返）。

★ 顺带修正的一个**错判**：验收第 15 项第一版用 `\\[a-zA-Z]{3,}` 数"残留公式"，
  把 Day11 正文里的字符串转义示例算成了没渲染的公式 → 误报 BAD。
  判据改成只认真正的 LaTeX 命令名（公式里会出现、代码示例里不会出现的那批）。

### AI 助教面板（用户要的：当助教 + 合并 AI 查代码 + 多轮 + 能可视化 + 代码别丑陋 + 显示余额）

```
用户原话：「最好当助教。可以和ai查代码合并。要多轮对话。我想要的就是，我不明白的可以
直接问他，还可以让他写一段我看看。这一段代码要求可以可视化。还有就是，我感觉现在的
版本写的代码太丑陋了，完全没有你写的简洁。还有，可以在里面显示一下api的余额。」
```

**结论：五条都做了。** 契约冻结在 `_dev/assistant-contract.md`（前端/后端并行改之前先定死
端点、字段名、SSE 事件名——契约一飘两边必然对不上，而且这种错要到打包后才发现）。

**① 提示词：为什么旧版写不出简洁代码（实测，不是猜）**

用户说"丑陋"，我先去读缓存里的真实产出，再让一个代理用 **10 次真 API 调用**做新旧对照。
三层原因：

- 旧的 `DEFAULT_SYSTEM_PROMPT` 只禁了 `if __name__ == '__main__':`，模型就改用
  `def main(): ... main()` **绕过去**了 —— 等于白禁。
- 对代码本身只有一句"只用标准库"，没有任何品味规则。
- 于是模型爱写 `out = []` 攒起来再 `join`、手工索引循环、`import sys` + `sys.stdin.read()`。

实测对照（同一道餐厅订单题）：

```
旧：正文 2176 字符，5 组「自己测这几组」刷屏，两次 '\t'.join(...)，一堆中间变量
新：正文  517 字符，1 个代码块，_, table, food = input().split(',')，print(*xs, sep='\t')
```

对话式问「这段为什么 KeyError」：**6462 → 952 tokens（6.8× 差）**，正文 1669 → 456 字符。

★ **意外收获：旧提示词有一处判断错误，不只是丑。** 闰年题题面提示"能被 3200 整除的
也不是闰年"（a<3000），旧的回答是"3200 在这个范围里**永远不可能触发**"、参考代码里
干脆没判；新提示词把 `if a % 3200 == 0` 放在最前面，并解释"3200 % 400 == 0，
先判 400 就会错"——正好是本课知识点（if/elif 短路顺序）。**换提示词修掉了一个会教错学生的缺陷。**

新提示词正文在 `_dev/assistant-prompt.md`（唯一来源），调优证据与复现方式见
`_dev/prompt-tuning/README.md`。我另外补了三条它自己指出但没预算验证的规则：
一次回答最多两个代码块（治刷屏）、诊断模式必须用真实运行结果而不是猜、
演示代码用自造数据 / 题解代码该用 `input()` 就用。

**② 提示词有三份副本 —— 这是最容易埋"我改了但没生效"的地方**

```
1. %LOCALAPPDATA%\course-terminal\assistant-prompt.md   ← 用户覆盖，最高优先
2. <exe 目录>\content\assistant-prompt.md                ← 随 exe 分发（复用 find_asset）
3. app/main.py 里内置的 DEFAULT_ASSISTANT_PROMPT          ← 兜底
```
以 `_dev/assistant-prompt.md` 为准逐字同步进内置那份，并加了回读校验（改完自动比对两边）。
★ **改正文必须把 `ASSISTANT_PROMPT_VERSION` +1** —— 它进缓存键，不改的话用户拿到的
仍是按旧提示词生成、已经落缓存的回答。

**③ 一个会让用户看到"空白回答"的真实缺陷（提示词代理实测发现）**

`deepseek-flash` 在 `thinking={"type":"disabled"}` 下**仍然烧隐藏 reasoning**。
某个"为什么 KeyError"的问题烧了 **5573 reasoning tokens** 才吐正文；
`max_tokens=3000` 时**新旧提示词都返回空字符串**（`finish_reason=length`）——
正文一个字都没有，而且不报错。而 `_chat_payload` 原来**根本没设 max_tokens**。

修法：显式 `AI_MAX_TOKENS = 16384`（该模型 `max_output_tokens` 实测 393216，远在范围内），
并在"正文为空 + finish_reason=length"时发明确错误而不是安静 `done`。
★ 作业那条 `ai_explain_stream` 共用 `_chat_payload`，所以它同样受益（原来也有这个风险）。
★ 实测是折扣的：假上游喂 `finish_reason=length` 能精确触发那条分支，
但**没能用真 API 复现空正文现场**（那要构造大费 reasoning 的问题）。所以"真上游在截断时
确实会回 `finish_reason`"仍是**假设**，若上游不回这个字段，检测就不会触发。

**④ 余额**

`GET /user/balance` 实测可用，返回 `{"balance_infos":[{"currency":"CNY","total_balance":"46.50"}]}`。
`/dashboard/billing/usage` 是 404，别用。服务端 60 秒内存缓存（两次请求 `fetched_at` 相同已验证），
**不落盘**。设置面板显示 `¥xx.xx（MM-DD HH:mm 取的）`+ 刷新按钮。

★★ **铁律：余额绝不能进缓存键。** `ai_cache_key` 会把 `cfg` 整个哈希进去，
余额一旦混进 `cfg`，**余额每变一分钱，用户之前缓存的全部解析同时失效**。
所以余额走独立函数 + 独立内存变量（`_AI_BALANCE`）。验收里加了**源码级检查**守这条：
grep `ai_cache_key` 函数体里有没有 `balance`。运行时测不了这条（要测就得让余额真的变化
再观察缓存是否作废，既花钱又难复现），所以查源码站位。

**⑤ 上下文（用户要的"要看见"）**

`context` 带 章节/小节/知识点/讲义片段（截 4000 字符），服务端拼成
`## 学生现在在看什么` 一节接在提示词后面。面板顶部显示 `现在看 ch01 · 课程简介 · 课程目标`。
★ 上下文变、回答就该变 —— `assistant_cache_key` 把含上下文的**完整 system** 的 sha256
放进了键，所以这一点是对的（我专门查过，这是个容易漏的地方：
一旦漏了，在 ch01 问的问题会在 ch03 命中同一份缓存，回答里带着别的章节的内容）。

**⑥ 前端：三个"静默失效"的 bug（代理自己撞出来并修掉的）**

1. `asNormMsgs` 读错字段名 —— 存储里是契约形状 `{role,content}`，第一版读 `m.text`
   → **每条历史都被当脏数据丢掉**，"写假历史重开能恢复"这条**静默失败**（回 0 条、不报错）。
   教训和 `key_tail` 那条一模一样：**两个形状不同来源的值做比较，只测过"能通过"的那一侧。**
2. `data-assistant-msg` 挂在行和气泡**两处** → 一条消息命中两次 → 3 条数出 6 个节点、
   下标从 0 变 3 → **「▶ 可视化」取到空代码**（按钮在、点了没反应）。现在只挂行上。
3. 设置面板"慢一拍"的异步渲染会**顶掉助教面板**（`aiSettingsRender` 原来只判 `modalOpen()`）
   → 加了代数守卫 `AI.setGen`。

**⑦ 我这一轮的三个错（都是"检查本身出错，比产品 bug 更难发现"）**

1. **`11-ai-review` 的断言我改坏了**：去掉 fetch 桩时删了 `const realFetch`、
   却留了引用它的那行 → `ReferenceError: realFetch is not defined`，
   看起来像产品 bug。改成真调用后，断言又写成 `'a=1 | b=2 | c=3'` 这种**多个 `|` 的期望串**，
   匹配器不按"都要出现"解析 → 输出完全正确却报 FAIL。**最终改成让探针自己算
   `verdict=OK`**（和别的任务一致），这类歧义就没了。
2. **id 交叉检查假报 `missing=['asRow']`**：那个 id 是拼出来的
   （`id="asRow' + i + '"` / `getElementById("asRow" + n)`），旧正则把 `"asRow"`
   当成必须存在的字面量。修法是跳过后面紧跟 `+` 的引用，**并且加了负向对照**——
   往集合里塞一个确定不存在的名字，它必须出现在 `missing` 里，否则说明放宽过头成了假绿灯。
3. **`accept.ps1` 的 BOM 又丢了（第三次）**。症状是 17 项全红 + `SyntaxError: Invalid
   regular expression` + 日文乱码 `浣撻噸`，而文件在编辑器里看完全正常。
   ★ 这次不再靠"记得验一次"，而是做了固定工具 **`python _dev\fix-ps1.py`**
   （修 UTF-8 BOM + CRLF 并回读校验）。**改完任何 .ps1 都跑它，然后验 ParseFile。**

**⑧ 顺带：`drive.mjs` 的越界改动（我裁定保留）**

截图驱动 `tools/pytutor/_dev/drive.mjs` 加了 `Runtime.exceptionThrown` +
`console.error` 的监听（`process.exit(0)` 保持不变）。理由成立：`Runtime.evaluate` 的
`exceptionDetails` **抓不到 setTimeout / 事件回调里抛的异常**，而没有这条，
"页面 JS 不能抛异常"就是**假绿灯**。它是引擎和终端**共用**的文件，所以我跑了引擎那侧
的验收确认没弄坏：**PASS=8 FAIL=0 ALL GREEN**（而且新打印项生效，每张截图都有
`未捕获异常数: 0`）。

**⑨ 验收**

```
PASS=22  FAIL=0  WARN=0  ALL GREEN
新增第 16 项 16-assistant：真开面板、真发两轮对话、断言
  焦点保持 / 上下文注入 / 代码块拿到 ▶ 可视化 / 历史从 sessionStorage 恢复
第 11 项 11-ai-review 改成真调用：断言"按下去真的出答案了"
  （原始症状是"没有输出"，所以承重断言是回答真的到达，不是面板开了）
新增 1c 源码级回归：ai_cache_key 不许含 balance、助教提示词独立、作业提示词原样保留
```

**⑩ 还没做 / 没验证的**

- **`/ai/explain` 的正向非缓存路径这轮没跑**（怕花钱）。路由校验、缓存命中、
  共用 `ai_stream_chat` 都验了，但"真发一次 explain 流"没有。风险点是
  `_chat_payload` 多了 `max_tokens`，对作业那条是行为变更（我认为是修 bug，但没实测）。
- **助手给的"题解代码"用 `input()` 时点 ▶ 可视化会跑不出东西**（没人喂输入）。
  演示代码不受影响（提示词已要求自造数据）。要彻底解决得给面板加一个"样例输入"框，
  或者给代码块分别标记"演示/题解"。**这条需要产品决定。**
- **没有"主动追问"话术**：新提示词比旧版短促，不会主动说"把你的运行结果贴给我"。
- 打包后的 exe 里没有真机点过（只在开发模式 + 验收脚本里验过）；
  真 IME 下 `Enter` 发送的 `isComposing` 放行只做了代码判断。

### 📥 「我要的就是点击检查更新之后自动加最新的章」——把「加一章」打通

```
用户原话：「但是我要的就是点击检查更新之后自动加最新的章啊」
```

检查更新早就**能发现**新章了（上一节），但点到"装"就停住了：
`_rebuild_targets` 明确拒绝不在登记表里的章，而流水线对 ch04 报
`content pages 101 != markers 99 → MISMATCH` 拒绝落盘。这一次把整条路打通。

**① 先搞清 ch04 为什么对不齐（不能靠放宽判据蒙混）**

逐页算出"每页真正匹配哪个 marker 窗口"，对齐表说话：

```
p4→窗口1  p5→2  p6→3  …  p31→27   ← 到这里都正确
p35→窗口30（期望 31）  p39→34  p40→35 …   ← 从 p35 起**全部偏 -1**
```

再对候选页做排除测试（同一套 check 3 评分）：

```
排除 p3  → checked=62   （差，说明 p3 不是那个"多余页"）
排除 p31 → checked=82
排除 p32 → checked=82   ← 语义正确
```

对照课件与讲义原文，答案是：

- **p3** —— 「本章学习的目的」引言页，在第一个 marker 之前
- **p32** —— 「复习：存储层次（二）」，而讲义把"复习一 + 复习二"并进了**同一个** marker
  （marker #27 那一节同时写了 16MB 那道题和断电那道题）

101 = 99 + 2。**ch01 是 M+1（一页这种情况），ch04 是 M+2** —— 而判据把关系写死成 M 或 M+1。

**② 修法：对齐自愈（不是放宽）**

先用探针给每页算"最匹配哪个窗口"，找出第一个"落错窗口"的**断裂点**，
多余页就在它前面那一小段里；逐个试、按**同一套 check 3** 评分
（`checked` 高、`own0` 少），选最优；排除后**必须重新过一遍 check 3**
（0 违规 + 覆盖率 ≥60%），否则整体作废、仍报 MISMATCH。

```
--detect ch04
  non_content_pages = [1, 2, 7, 32, 56, 92, 104]      ← p32 被自动识别
  check 2  markers M = 99, content pages = 100  ->  relation M+1   OK
  check 3  可用窗口匹配 82（原来 21）, violations = 0
  RESULT: OK
  warning: 对齐自愈：把 [32] 当作"课件有、讲义无"的页排除…
```

★ **无回归**用两个独立证据确认：

- 检测器自测 `--selftest-detect`：ch01/ch02 **MATCH**（ch03 失败是因为站上 ch03 课件
  真的更新了：92 页、agenda 页重新编号，与旧答案本来就该不一致）
- 拿**旧的** ch03 课件重跑：`non_content_pages` 与登记表**完全一致**，且 `auto_skipped=[]`
  —— 自愈在 M/M+1 时是**空操作**

**③ 顺手修掉两个把排查带偏的坑**

1. **`ensure_pdf` 不校验缓存** → `%TEMP%\ct_pipeline\ch04.pdf` 里躺着 **ch02 的 PDF**
   时，`--detect ch04` 拿 ch02 的课件去分析，报一堆误导性的 FAILED，
   而且**不告诉你分析错了对象**（我先怀疑站点、又怀疑检测器，最后才发现是缓存）。
   修：用远端 `Content-Length` 比本地大小，不一致就重下。
2. **那个"修法"自己又踩了一个坑**：`urllib` 在这个文件里**不是顶层导入**的
   （`fetch_url` 是函数内 import），我直接写 `urllib.request` → `NameError` 被
   过宽的 `except Exception` 吞掉 → `remote` 永远是 `None` → **每次 detect 重下 19.5MB**。
   教训：过宽的 except 会把"代码写错"伪装成"网络不给"。改成函数内 import + 收窄 except。

**④ 应用侧：让 `/update/rebuild?chapter=chNN` 支持"安装新章"**

后端按"在不在本地登记表里"自动分流。新章比重建多三件事（少一件都会"装完看不到"）：

```python
entry["title"] = det["title"]          # ← 漏了这行就是 KeyError: 'title'，
                                       #   而且失败发生在渲染 107 页**之后**
order = list(module.CHAPTER_ORDER); order.append(ch)   # 新章要进 order
module.refresh_point_ids(order)                        # 新章要纳入 id 基线
```

外加：暂存目录里要**凑齐已装各章的 chNN.json**（`refresh_point_ids` 是从每章
chNN.json 重算整份基线的）—— 漏了它就是 `FileNotFoundError`，同样是白跑一场。

`_rebuild_publish` 本来就发布 `chNN.json / notes/chNN.md / _chapters.json / slides / images`，
只补了一条 `_point-ids.txt`。

**⑤ 前端：新章节那一行加「⬇ 安装这一章」**

走的就是 `/update/rebuild?chapter=chNN`（同一个动作），`upRebuild` 多收一个 label
让 toast 说人话（"开始安装新章 ch04" / "开始重建 ch03"）。

**⑥ 端到端验证（真装，两轮）**

```
装之前: chapters=[ch01,ch02,ch03]  new_chapters=[ch04 计算机系统]
POST /update/rebuild?chapter=ch04 → pending
32 秒完成: ch04 ok=True  20 卡 / 107 页
装完:   chapters=[ch01,ch02,ch03,ch04]  new_chapters=[]
        /content/ch04.json → sections=4 points=20
        /content/slides/ch04/page-107.png → HTTP 200 172031 B
```

映射正确性**独立验证**：20/20 个知识点都能在它指向的那页找到 18–40 字的逐字重合；
3 个"下一页分数更高"的逐个看过，指向页本身都是对的（下一页恰好也含相似文字）。

**⑦ 顺带发现并修掉一个真回归：安装时把 videos.json 弄坏了**

安装完成后会跑 `_rebuild_videos_rekey(targets)`，而它把"**不在 targets 里**的 key"
当成"这个知识点已经没了"直接丢掉。安装时 `targets=['ch04']` →

```
/content/videos.json  63,875 B → 42,750 B
03-video: vpageLinks=0 iframe=none          （变红）
14-video-panel: NO_POINT_WITH_VIDEO         （变红）
```

界面上**所有"这个知识点有视频"的入口一起消失**。修：把**所有已装章节**都传进去
（没被重建的章标题一个都没变，一起传就等于"原样保留"；对普通重建同样更正确 ——
重建 ch03 不该顺手抹掉 ch01/ch02 的推荐）。

修完验证：装完 `dist` 里**没有** videos.json（重挂判定"没变"而早退），
包内那份 63,875 B 原封不动，两条视频断言恢复绿色。

**⑧ 我自己在这次里犯的错（都记下来）**

1. **改 docstring 时把 main.py 改坏了**（`IndentationError`）—— 我插入的新段自己
   收尾了 `"""`，原来的剩余行成了悬空缩进。**语法检查立刻抓到**，没走到打包。
2. **又把 `build.ps1` 管道了两次**（`| Out-Null` / `| Select-String`）——
   PyInstaller 的 INFO 走 stderr + `$ErrorActionPreference='Stop'` 直接中断。
   已经是我自己文档里写过的禁忌，还是犯了两次。
3. **验收探针的桩写太宽**：`u.indexOf('/update/rebuild') >= 0` 把 **GET 能力查询**
   也拦了，返回的对象没有 `rebuild_supported` → 面板显示"不支持一键重建" →
   按钮 disabled → `click()` 无效 → 我误判成"检查按钮点了没反应"。
   **一个桩写宽了能伪造出两个假 bug。** 修成只拦 POST。
4. **运算符优先级**（这轮第二次）：`'x' + !!btn && btn.getAttribute(...)` ——
   字符串真值就继续求值，`btn` 为 null 时崩。

### 🌀 「从100days的可视化退出来之后的保持页面一直不行」——滚动容器换了，存取代码没跟上

```
用户原话：「为什么从100days的可视化退出来之后的保持页面一直不行？」
```

**① 先看证据：那条验收测试早就变成假绿灯了**

最近一次验收里两条滚动测试的实际输出：

```
15-days-math:     scroll want=0 got=0   | aged20min want=0 got=0
19-dayctx-scroll: fresh  want=0 got=0   | aged20min want=0 got=0
```

`want=0` —— 它量的是 0、断言 `|0-0|<=4`，**恒通过**。
（早先真实数据是 `want=5478 got=5478`，说明是后来退化的。）

**② 根因：我把阅读器从"弹层"改成"内嵌"时，滚动容器换了**

实测（内嵌阅读器里量一遍）：

```
main       ={scrollH:6927 clientH:903}     ← 真正在滚的是它（只有它有 overflow-y:auto）
#inlineBody={scrollH:6722 clientH:6722}    ← 它自己不滚（clientH == scrollH）
#modalBody ={scrollH:0    clientH:0}       ← 空的
window.scrollY = 0                          ← body 是 overflow:hidden 的 flex，window 永远不滚

滚 main 到 2771 后 → saveScrollBeforeLeave() 存下来的是 {"modalTop":0,"winTop":0}
```

`saveScrollBeforeLeave` 存的是 `modalBodyEl().scrollTop` + `window.scrollY`，
恢复也写回同样两处 —— **两个都不滚**，所以存 0、恢复 0，用户看到的就是"回顶"。

**阅读器还是弹层时**（我改内嵌之前）`#modalBody` 自己有 `overflow:auto`，那套代码是对的；
**改成内嵌后**滚动容器变成 `main`，而存取位置的两处代码没跟上。
→ 时间线也吻合：这个 bug 是我做完"内容也进卡片区"之后才出现的。

**③ 修法：三个容器都存、都恢复**

```js
function paneEl(){ return document.querySelector("main"); }   // 真正的滚动盒子
function paneScrollNow(){ … }
// 存：modalTop（窄屏弹层）+ paneTop（main，卡片流/内嵌面板）+ winTop（兜底）
// 恢复：三处都写回
```

实测修好：

```
存下来的={"url":"/?day=1","layer":"reader","modalTop":0,"paneTop":2771,"winTop":0,...}
恢复后 main.scrollTop=2771（期望 2771）   ★ 保持住了
```

**④ 顺手把两条假绿灯测试改成可证伪的**

两处都是 `const mb = IC.surfaceRoot()` —— 内嵌时它返回 `#inlinePanel`，而**它不是滚动容器**
（`scrollHeight == clientHeight`），所以 `mb.scrollTop = ...` 什么也没做。

- 改用 `IC.paneEl()`（= `main`）
- **加 `want > 0` 的前提**：滚动量取不到就当场判失败，不允许再退化成 `0==0`

**⑤ 还加了一条"真实整页往返"的测试**

上面那些是"直接调 save/restore"，它们全绿过、而用户那边依然回顶 ——
所以必须走一次**真的整页加载**：

```
在主页滚好 → saveScrollBeforeLeave() → 同源 iframe 加载那个 URL（= 从 /tutor 点返回时的 boot）
                                      → 读它自己的 main.scrollTop
```

同源 iframe 与顶层共享 sessionStorage，所以这条真正覆盖
"boot → restoreFromUrl 开阅读器 → restoreScrollAfterLayer 复原"整条链。实测：

```
真实往返目标=/?day=11
真实整页往返 want=5010 got=5010  阅读器开着=true
```

★ 这条测试我**自己写错过两次**，两次都是"存的和加载的不是同一个地方"：
① 写死 iframe 加载 `/?day=11`，而点开的是 Day 1（存 `/?day=1`）→ `samePlace` 正确拒绝 → 我误判成产品 bug；
② 前面的用例都用 `{push:false}`，地址栏一直是 `/` → 存 `url="/"`、iframe 也加载 `/` → 落到**卡片流**，
   而卡片流内容高度远小于阅读器里的滚动量 → 被夹成 565 → 假失败。
**教训：往返测试里"离开的地方"和"回来的地方"必须是同一个，最好从存下来的 url 里取，别写死。**

### 🔄 「网站上更新新一周资料了，怎么按检查更新按钮不行呢」

```
用户原话：「现在网站上已经更新新一周资料了，怎么按检查更新按钮不行呢。新的作业倒是抓回来了」
```

作业能看见是因为作业走 OJ 的**动态列表**（另一条路，实测 `have=['hw1','hw2']`）。
"检查更新"这条路有**三个**独立的问题叠在一起，一个比一个深：

**根因 ①：检查器只遍历"本地已装的章"，站上新增的一章不在它视野里**

`update_check_fast` 里是 `for ch in order`，而 `order` 来自本地注册表
`content/notes/_chapters.json`（只有 ch01/ch02/ch03）。站上新增的第四章**永远不会被检查**，
于是它老老实实比完那三章、回报"没发现变化"。

而课程站根页只有 515 字节（`<meta http-equiv="refresh" content="1; url=README.md">`），
真正的目录在 `README.md` 的"课程进度"表里：

```
| 第四周 | 计算机系统([md]( notes/ch04.md )｜[pdf]( slides/ch04.pdf )) | 作业二… |
```

→ 新增 `update_remote_chapters()`：拉 README.md 解析 `notes/chNN.md` / `slides/chNN.pdf`，
和本地一比，缺的就是新章。实测：

```
远端 order = ['ch01','ch02','ch03','ch04']   本地 order = ['ch01','ch02','ch03']
ch04  标题='计算机系统'  讲义=True 课件=True
```

**根因 ②：快路先看 etag 基线、而且每次检查都无条件刷新基线 → 变化会被"忘掉"**

```python
prev = 上次检查记下的基线
if prev.get("etag") and etag:
    info["same"] = (prev["etag"] == etag)      # ← 比"上次看到的远端"，不是"本地已装的"
elif clen_i is not None and local_size is not None:
    ...                                        # ← 只有"没有历史基线"时才比本地长度
```

只要某次检查发生在站点更新**之后**、用户重建**之前**，etag 基线就被刷成新值；
此后每次检查都"相同" → 永远"没发现变化"，而本地内容一直是旧的。

实测铁证（`update-state.json` 里记的正是站点当前值，而本地是旧的）：

```
ch03.notes.length  = 59,406     站点现在
content/notes/ch03.md = 56,657  本地已装   ← 变了，但基线说"一样"
```

修法两条：
### 📝 「作业ai解析可视化退出来是这个界面」——解析丢了 + 误报未配置

```
用户原话：「有小问题。作业ai解析可视化退出来是这个界面」
（截图：红框"还没配置 API Key" + "还没有解析"）
```

两个**互不相干**的缺陷，凑巧同时出现：

**① 解析结果存在内存里，整页跳转回来就归零**

`HW.ai` 是 `var HW = { ai: {}, … }` 里的纯内存对象；而点可视化是**整页跳转**
（导航桥把同源 `window.open` 改写成 `location.assign`，见前面「滚动位置」那条）。
重载后 `HW.ai` 是空的 → 用户看到"还没有解析"，刚生成的东西不见了。

→ 照抄会话历史那套（`AS_KEY` / `assistantSave` / `assistantLoad`）加 `anaSave` / `anaEnsureLoaded`：

- 存 **sessionStorage**（只活在这个标签页；解析本来也不该跨会话留着）
- **只存完整的**：跳过 `busy` / `error` / 没正文的（半截的存了反而误导）
- 最多 `ANA_MAX = 40` 题，别把配额撑爆
- `anaEnsureLoaded()` 挂在 `aiEnsure()` 开头（懒加载，内存里已有更新的就不覆盖）
- 生成完成 / 出错时各 `anaSave()` 一次

**② 面板先于 `/ai/status` 渲染 → 误报"还没配置 API Key"**

```js
function aiConfigured(){ return !!(AI.status && AI.status.configured); }
```

`aiConfigured()` 只看 `AI.status`，而它是**异步**拉的；面板渲染时还是 `null` → 报"还没配置"。
而且启动时的 `loadAiStatus();`（fire-and-forget）**加载完没有任何东西重绘** ——
所以那句假提示会一直挂着，直到用户手动重开面板。

→ 两处修：
- 警告改成 `if (AI.loaded && !aiConfigured())` —— 状态没回来就先不画
- `loadAiStatus()` 的 `.then` 里主动重绘当前层（`problem` → `renderProblem()`，`hw` → 重画面板）
  ★ 放在 `loadAiStatus` 里而不是各个调用点：这样所有调用方（含启动那次）都受益

**③ 探针我自己踩的两个坑（都写进断言旁边的注释了）**

1. **运算符优先级**：`'落盘=' + raw.indexOf(MARK) >= 0` 按 `('落盘='+n) >= 0` 解析 →
   字符串转 NaN → **恒 false**。我第一次跑就看到 `落盘=false`，差点当成产品 bug。
2. **`#modalBody || #inlineBody`**：`#modalBody` **存在但可能为空**，`||` 会选中空的那个 →
   读到空字符串就以为"解析没了"。两个容器都要读。

**④ 验收**

新增 `21-ana-restore`（不花钱：塞假解析 + `anaSave()`，再建同源 iframe 加载题目 URL
走一遍真实整页返回）：

```
落盘=true 跳过半截=true len=209
iframe 正文=" … 题面 解析 测一测 | 🔄 重新生成 | 已缓存 生成完毕 | 💭 思考过程（3 字） … "
解析还在=true 没误报未配置=true | verdict=OK
```


修完实测（连续两次检查）：

```
第 1 次：ch01 讲义变了(44550 vs 44504) / ch03 讲义变了(59406 vs 56657) / 新章节 ch04
第 2 次：**同样结果**（变化不再被忘掉）；ch02/notes 因长度一致记为 same
```

★ **ch01 和 ch03 的讲义都早就变过，按钮之前全都看不见。**

**根因 ③：`ensure_pdf` 不校验缓存 → 拿错文件分析还只报 FAILED**

排查时 `--detect ch04` 报 FAILED，且 agenda pages 与 ch02 一模一样。查下去发现：

```
%TEMP%\ct_pipeline\ch04.pdf = 23,737,618 B  sha=44b346df…  ← 就是 ch02 的 PDF
```

`ensure_pdf` 的逻辑是"文件存在且非空就直接用"，**不校验内容**。所以它拿 ch02 的课件
去分析 ch04，报出一堆误导性结论，而且**不告诉你分析错了对象**——我先怀疑站点文件、
又怀疑检测器，最后才发现是缓存放错了。修法：用远端 `Content-Length` 比本地大小，
不一致就重下（HEAD 拿不到长度时保守重下）。做了负向对照：
故意把 ch02.pdf 冒充成 ch03.pdf，它检测到不一致并重新下载。

★ 用**真的** ch04.pdf 重测后仍是 FAILED（`content pages 101 != markers 99`），
这是**另一个问题**：检测器的启发式对第四章不成立，pipeline 因此拒绝落盘（fail-safe 设计）。
所以「加第四章」现在还不能一键完成 —— 见下面的待办。

**④ 面板显示 + 诚实的边界**

- 前端 `updateReportHtml()` 里"新章节"必须排在"没有发现变化"**之前**判断
  （否则有新章时仍会显示"没变"）
- 课件那条如实说"本地没留原文件，没法用长度判，需要一次「下载核对」"，
  **不再给一个假的"没发现变化"**

**⑤ 我自己的两个错（都被机制抓住）**

1. **守卫写错**：`order_ok = s.find("A") < s.find("B")` —— 标记不存在时 `find` 返回 **-1**，
   而 `-1 < 任何正数` 都成立 → **标记被删掉时守卫照样通过**。负向对照抓到的，
   改成 `_pos_len >= 0 and _pos_etag >= 0 and _pos_len < _pos_etag`。
2. **探针作用域错**：`const pane` 只在 `roundTrip()` 函数体里声明，我在函数外用了它
   → `ReferenceError: pane is not defined`，整条 `19-dayctx-scroll` FAIL。
   **这次是全量验收抓到的**（单跑时我把 `pane` 那句当成"没跑到"忽略了 —— 不该忽略）。

**待办：站上 ch04 已发布但装不进来**

```
notes/ch04.md   HTTP 200   54,026 B
slides/ch04.pdf HTTP 200   19,557,331 B  (107 页，sha=892aee94…)
--detect ch04  →  FAILED：content pages 101 != markers 99
```

`_build-json.py` 的一致性检查对第四章不成立（第二章是 `M` 关系、第一/三章是 `M+1`，
第四章 107 页的排布又是另一种）。pipeline 拒绝落盘是**正确的 fail-safe**，
但要"一键加章"就得先弄清 ch04 的版面规律、再放宽/修正检测器。
这是加一章（要动 `_point-ids.txt` 基线），不是重跑一章 —— 需要单独确认后再做。


**⑥ 这条 bug 教给我的（比修它本身重要）**

它存在了**好几轮**：期间我跑过很多次全绿验收，还专门"修过一次"
（把时效窗口从 2 分钟放宽到 30 分钟）。**两次都是因为测试走的是"方便测的路径"**
（直接调函数、或量错了元素），而不是用户真实走的那条。
**假绿灯比没有测试更糟 —— 它让我以为修好了。**

### ⚡ 「直接跑」按钮：绕开追踪上限 + 顺带修好一个"看不到原因"的缺陷

```
用户问：「现在的版本你确定能运行任意python代码了吗」
（回答：不能。实测出硬边界后）用户说：「加一个'直接跑'的按钮吧」
```

**① 先把边界量清楚（不能拍胸脯回答"能"）**

| 限制 | 值 | 真实影响 |
|---|---|---|
| `MAX_STEPS` | 5000 | **最要命**：约 2 个快照/行事件 → `range(2500)` 就被砍 |
| 墙钟 | 30 秒 | `sleep(20)` 能过；纯计算先撞步数 |
| 单次输出 | 64KB | 截断 |
| 每容器显示 | 100 元素 | 只影响展示 |
| 堆对象 | 150000 | 大程序可能先撞 |

实测对照（`/run` vs `/run-raw`）：

```
代码              /run（追踪）            /run-raw（直接）
range(1000)     ok(2004步, 0.2s)       ok(0.00s)=499500
range(2500)     aborted(5000步)        ok(0.00s)=3123750
range(50000)    aborted(5000步)        ok(0.01s)=1249975000
range(200000)   aborted(5000步)        ok(0.08s)=19999900000
递归 f(12)       ok(1398步)            ok=144
递归 f(18)       aborted(5000步)       ok=2584
```

★ **我一开始对 `MAX_STEPS` 的理解是错的**：以为是"每行一个事件"，
所以先说 `range(3000)` 被砍，后来又把 `range(5000)`（我探针里写的）当成"没被砍"的证据，
自相矛盾。实测才发现是约 **2 个快照/行事件**（`range(1000)` → 2004 步）。
**拿错的模型去判断"哪个按钮有用"是不可靠的，必须量。**

**② 顺带发现：写文件其实能写**

我以为被 `codeRunAdvice` 的 `write` 规则挡了，实测**能写**，写到 `%TEMP%`
（`open(...,"w")` → `kind=ok`，`os.getcwd()` = `%TEMP%`）。
`subprocess` 会被挡（`kind=aborted`），`os.remove` 报 `FileNotFoundError`，网络报 `gaierror`。
→ 那条"要写文件就不挂可视化按钮"的规则**过度保守**了。

**③ 新增 `/run-raw`（不追踪，纯 CPython）**

- 走 `exec`，**不产生快照** → 没有步数上限，只留 30 秒墙钟
- 复用 `REPL_LOCK`（**不是**新开一把）：它和 REPL 都要替换全局 `sys.stdout/sys.stdin`，
  并发会互相抢流（pytracer 里那段 RLock 注释讲的就是这个坑）
- 守卫复用 `_ReplAborted`（继承 `BaseException`，不会被用户的 `except Exception` 吞掉）
- 返回形状尽量和 `trace_code` 对齐（`ok/kind/stdout_final/abort_message/error/error_cn/inputs`
  + `direct:true`），让前端能复用同一套错误面板
- 已知边界：守卫拦不住"卡在 C 调用里"（`time.sleep(600)`），因为 `settrace` 收不到
  C 函数内部事件 —— 和 REPL 一样，这是 `settrace` 方案的固有边界

**④ 顺带修好一个真实缺陷：被砍之后看不到原因**

`renderStepAlert()` 只在 `step === stepCount() - 1` 时才画提示，
而 `afterTrace()` 原来一律 `goto(0)`。所以程序被步数上限砍掉后：

```
跑 range(50000) → 追踪被砍 → 视图停在【第 1 步】→ 提示区**空的**
用户只看到"代码没动静"，必须自己点【末尾】才知道是"步数超限"
```

改成 `if (trace.aborted) { goto(stepCount() - 1); return; }`。修完实测：

```
跑完 stepText="已中断（共 5000 步）"
     notice="步数超限，已自动中断 执行超过 5000 步（很可能是死循环），只追踪了前面这些。"
```

★ 这个缺陷**用户已经踩过了**（"连这都运行不了吗"那次截图就是），
只是当时我把它当成"用户代码写错了"就没往下查。

**⑤ 前端：`viewer.html` 加「⚡ 直接跑」按钮**

- 不经过 `afterTrace()`：那是给"有 steps 的追踪结果"用的，喂给它没有 steps 的响应
  会走到"没有可显示的步骤"分支（用户明明刚跑出结果，却看到"这段代码里没有可执行的语句"）
- 给一句"这次只取结果，所以没有逐步的变量图。需要看每一步怎么变，点「▶ 运行」"
  —— 不说明的话用户会以为"忘了做追踪"

**⑤b 这个按钮我连错两次，两次都是用户先发现的**

**错 1：「你把直接跑按钮放哪里了」——我把它藏了。**
我写了 `if ($("btnRunDirect")) $("btnRunDirect").hidden = play;`，
理由是"演示态下用户在单步看，不该有按钮把整段跑掉"。**那个理由完全错了**：

```
从卡片点「🔬 可视化」进来带 ?code= → 页面自动跑一次 → 进 play 态
  play 态下「▶ 运行」被 CSS 藏起来（body[data-state=play] #btnRun{display:none}）← 原有设计
  我又把「直接跑」藏了                                                      ← 我的错
  → 用户一个重跑入口都没有
而 play 态恰恰最需要它：代码被 MAX_STEPS 砍掉、正想"我只要结果"的时候。
```

改成两种状态都显示：`$("btnRunDirect").hidden = false;`

★ 我**只在编辑态验证过这个按钮**，从没验过"从卡片点进去"这条**主路径** ——
而主路径恰好落在 play 态。自检脚本的判据也反过来了：现在是
"**不许**在演示态隐藏它"。

**错 2：「按了直接跑之后怎么啥也没有」——我把结果写进了看不见的容器。**
`runDirect()` 第一版是 `setMode("edit")` + 把结果写进 `#stdout`。但：

```css
body[data-state="edit"] #vizArea{display:none}
```

而 `#stdout` 就在 `#vizArea` 里 —— **写进了 display:none 的容器**，所以屏幕上空的。

修法是加**第三种状态** `direct`（而不是复用 edit）：

```css
body[data-state="direct"] #stepControls{display:none}
body[data-state="direct"] #legend{display:none}
body[data-state="direct"] .vizgrid{display:none}    /* 栈帧/堆：没有快照，没意义 */
body[data-state="direct"] #codeView{display:none}
body[data-state="direct"] #code{display:block}       /* 左栏保持可编辑，方便改完再跑 */
body[data-state="direct"] .right{grid-template-rows:auto}
```

外加两处细节：输出面板那句说明原本是单步语境的
（"显示到当前这一步为止"），direct 态换成"这次直接跑完的完整输出"。

★ 教训：**"切到某个已有状态"之前要先确认那个状态里"我要写的元素是不是可见的"。**
我第一次踩的是 `display:none` 的容器，第二次（错 1）踩的是同类的反向错误 ——
都是"没确认目标状态的实际可见性"。

**⑥ 我自己在验收断言上栽的坑（都记在断言旁边了）**

1. **把浏览器任务加进了 `$jobs`，但那些任务跑主页面 `/`**，而按钮在 `/tutor` 上
   → 必然炸。删掉，改在 HTTP 节断言 `/run-raw`（确定性更好、更快）。
2. **探针读错时刻**（又一次）：`renderStepAlert()` 只在最后一步画，
   我却在"第 1 步"的状态下读 `notice` → 报"对照组没被砍"，看着像产品坏了。
   真相是产品把提示放在了最后一步（而这正暴露了上面④那个缺陷）。
3. **`Start-Process -RedirectStandardOutput` 会写出乱码**（PS 5.1 用 GBK 写文件），
   验收脚本的 `页面 JS 返回` 正则因此匹配不上 → **假 FAIL**。
   ★ 和之前那次 "PASS=5 FAIL=21" 是同一个坑的不同入口。
   **不要用文件重定向跑验收**；用 `pwsh` 工具自己的后台任务（内部捕获输出，不经文件）。

### 🩺 「连这都运行不了吗」——`input` 漏括号，但提示把人带偏了

```
用户发来截图：a,b=map(int,input().split()) 报
  「没有这个方法/属性（AttributeError）：
    第 1 行用了 builtin_function_or_method 的 .split，但类 builtin_function_or_method
    里没有定义这个名字。
    💡 检查 __init__ 里是不是写成了 self.split = ...（漏了 self. 就变成了局部变量）」
用户原话：「连这都运行不了吗」
```

**① 引擎没坏；代码确实少了括号**

报错原文就是判据：`input` 是内置函数对象，它的类型正是 `builtin_function_or_method`，
而它没有 `.split` —— 这只可能是**写成 `input.split()`（漏了 `()`）**。
用真实 `/run` 把变体逐个跑了一遍，只有一种同时解释截图里的两个特征
（那句话 + **没有输入面板**）：

| 代码 | 结果 |
|---|---|
| `map(int,input().split())` 带括号 | `kind=ok` `inputs=1` `stdout='7\n'` ✅ |
| `map(int,input.split())` **少括号** | `kind=runtime` `inputs=0` ★就是那句话 |
| 带括号但 stdin 为空 | 报的是"输入用完了"（不是这句） |
| 带括号但输入不是数字 | 报的是 `int()` 转换失败 |

★ `inputs` 那条也很关键：带括号时引擎能**静态认出**"第 1 行第 12 列有个 input()"，
前端才会显示输入面板；少括号时 `inputs=[]`。所以**"截图里没有输入面板"本身就是佐证**。

**② 真正该修的是那句提示**

`explain.py::_explain_attribute` 里没有 `builtin_function_or_method` 这个类型的分支，
于是掉进最后那条**给自定义类用的**兜底（`TYPE_CN` 里也没映射这个名字，
`cls not in TYPE_CN` 成立）—— 建议用户去查"`__init__` 里是不是漏了 `self.`"，
跟漏括号**毫无关系**。两处一起改：

- `TYPE_CN` 补 `builtin_function_or_method` / `builtin_function` / `method` / `method-wrapper`
- 加一条**专门的漏括号分支**（放在自定义类兜底**之前**）

改后的提示：

```
detail: 第 1 行是在**一个函数本身上**用了 `.split`，而不是它的返回值
        —— 几乎可以肯定是**函数名后面漏了括号**。
hint  : 调用函数要带括号才拿到返回值：`名字()` 而不是 `名字`。最常见的一处是 `input`
        —— 写成 `input.split()` 就会报这个错……正确写法是 `input().split()`……
        `len` / `sum` / 你自己定义的那些函数也一样，都要带上 `()`。
```

★ 措辞刻意**通用**：错误消息里拿不到"是哪个名字漏了括号"（只有类型名），
所以不能猜成 `input`。**第一版我就写了"拿你这行来说：input 漏了括号"**，
结果 `len.split()` 那种情况也被说成 input —— 猜错比不说更糟。
同时验证了**自定义类那条兜底没被弄坏**（`a.y` 仍给出 `self.y` 建议 + 列出实际属性）。

**③ 加断言时我连着犯了两个"没先看 helper 就写"的错**

写验收断言时：

1. 用了 `post("/run", {...})` —— 这个脚本里的 POST helper **叫 `run`**，直接 `NameError`，
   把整段 HTTP 检查拖红。
2. 改完名字还错：`run(code, stdin="")` 的返回**已经是解析好的 dict**，不是 `(status, body)`。

两处都写进断言旁边的注释了。**加断言前先确认 helper 的名字和返回形状** ——
这跟前面"`#sideBar` 放错父节点""批量替换改到自己家函数"是同一类错：
**动手前先把接口看清楚**。

### 🧭 版面大改：左侧图标栏 + 三个面板内嵌到卡片区

```
用户原话：「把以前右上角那一堆统一放到左侧做出图标栏。然后图标栏往右，目录区，
再往右，卡片区，再往右，课件以及讲义。右下角还是助教按钮。这些都不变。
变的是，100days和作业，b站视频列表统一在卡片区展示。」
```

**① 新骨架**

```
body(flex row)
├── #sideBar            52px 图标栏，占满全高、常驻
│     ☰ 目录 / 🐍 试一试 / 🔬 可视化 ‖ 📺 视频 / 📅 100Days / 📝 作业
│     ────────（.sbSp 撑开）────────
│     🔍 搜索 / 🔄 检查更新 / ⚙️ AI 设置（压到底部）
└── #rightPane(flex column)
      ├── header          只放"我在哪"：计算概论 B · ch01 章节 · 第N节 · 🔥连续
      ├── #shell          目录(272) ‖ main(卡片区) ‖ 材料栏(308)
      ├── #repl           试一试（可收起）
      └── footer          ← 上一条 / 下一条 → · 进度点阵 · 计数
#asFab 仍是右下角常驻圆钮（不动）
```

**② 三个面板从"盖在卡片上"改成"在卡片区里显示"——只改落点，不改功能**

`openDaysBrowser / openHomework / openVideos` 全都是同一种写法：

```js
openModal(kind, title, xxxPanelHtml())   +   $("modalBody").innerHTML = 重画
```

所以做了两层抽象，三个功能**一行都没动**（它们内部"数据到了再重画一次"的逻辑也照旧）：

| 函数 | 作用 |
|---|---|
| `surfaceInlineOk(kind)` | 这个 kind 该内嵌吗（`INLINE_KINDS={days,hw,videos}` 且窗口 ≥900px） |
| `surfaceIsInline()` | 现在是不是内嵌模式 |
| `modalBodyEl()` | 正文写哪（`#inlineBody` 或 `#modalBody`）—— **所有**正文写入都走它 |
| `modalKind()` / `modalOpen()` | 把内嵌面板也算作"开着的一层"，Esc / 翻卡守卫 / 读屏标签全都自动认识它 |
| `surfaceRoot()` / `surfaceBodySel()` | 给验收用：在"当前面板"范围里查东西，不用关心落点 |

★ 瞬时交互（搜索 / 检查更新 / AI 设置 / 大图预览）**仍在弹层**：它们本来就是覆盖式的一次性
操作，放进卡片区反而把卡片顶掉。这个分工写在 `INLINE_KINDS` 的注释里。

**③ 这一轮踩的坑（都是"看起来对、其实静默坏"）**

1. **`#sideBar` 落进了 `#rightPane` 里**：`<div id="rightPane">` 我插在 `<header>` 之前，
   而图标栏写在 `</header>` 之后 → 它成了 rightPane 的子元素、夹在 header 和 #shell 之间，
   把 `#shell` 挤成 **`h=0`**（截图看上去"内容被挤到页面底部一小条"）。
   量出来才看到 `#shell l0 t1037 w1500 h0`。→ 用脚本把两块先后顺序重排。
2. **`dots / dotCount / secLabel` 变成对 null 赋值**：顶栏第二行随按钮一起取消，
   但 `renderTop()` 还在写这三个 id。**不抛异常**，肉眼看不见 ——
   是验收里那道 `web id cross-check` 抓到的（`missing=['dotCount','dots','secLabel']`）。
   → `secLabel` 放回顶栏（它是导航信息），点阵+计数放进 footer 翻卡那一排。
3. **`modalBodyEl()` 被批量替换写成无限递归**：我用脚本把 `$("modalBody")` 全量替换成
   `modalBodyEl()`，结果把 `modalBodyEl` **自己的函数体**也换了：
   `return surfaceIsInline() ? $("inlineBody") : modalBodyEl();`
   ★ 靠"替换后复查还剩哪些 `$("modalBody")`"发现。批量改时盯住自己家函数。
4. **`web id cross-check` 把注释里的 id 当引用**：删掉「⋯ 更多」菜单后，代码里留了一句
   注释解释 `$("headMenu")` 现在永远返回 null → 误报 missing。
   → 给那道检查加 `strip_js_comments()`（正确处理块/行注释与字符串字面量），
     并**保留负向对照**证明它没变成瞎子。
5. **`.ps1` 的 BOM 又被我自己的 Python 编辑脚本弄丢（第 4 次）**：Python 的
   `encoding='utf-8'` **不写 BOM**，而我所有"批量替换 accept.ps1"的脚本都用它。
   症状：PS 5.1 按 GBK 读 → 满屏 `鍥炬爣鏍?` → **PASS=5 FAIL=21**，报错看起来像产品坏了。
   ★ 用可复现实验确认 `fix-ps1.py` **能救**（它确实报"补上 BOM"），所以不是工具坏了，
   是**我编辑完之后没有再跑一次它**。
   **纪律：凡用 Python 改过 `.ps1`，收尾必须再跑 `python _dev\fix-ps1.py`，并核对
   `ParseFile` 报 0 错 + 文件前 3 字节是 `EF BB BF`。**

**④ 验收改动**

- `17-topbar` → 重写成 `17-sidebar`：断言图标栏在最左/占满高度/不被遮罩盖住、顶栏 0 个按钮、
  横向顺序 `图标栏 < 目录 < 卡片 < 材料栏`（比左边界，不是比 DOM 顺序）、
  三个面板 `inline=true / 在卡片区=true / 卡片让位=true / 圆钮让位=true`、
  搜索仍在弹层、Esc 能收内嵌面板。
- 探针里所有 `#modalBody` 查询改成 `IC.surfaceRoot()`（落点无关），否则内嵌模式下
  探针会去查一个隐藏的旧容器而"找不到元素"。
- **量左边界不能用 `#card` 当基准**：面板打开时它 hidden，`getBoundingClientRect()`
  返回全 0（第一版就这么错，报"不在卡片区"）。

**⑤ 已知偶发，不是产品问题**

`04-oj` 在整套长时间运行时偶发失败：截图驱动自己报
`Warning: Detected unsettled top-level await ... Page.captureScreenshot`，
那张没写成 → `no screenshot`。**单跑 3/3 全过**，且探针本身返回正常
（`NO_OJ_BUTTON` 是预期值）。属于驱动层抖动，与本次改动无关。

**⑥ 用户的三个后续修正（同一轮里补的）**

```
「问题一：这个图标无需"目录"两字
  问题二，侧边栏的图标最好加一个"鼠标放上显示功能"的功能
  问题三，我的意思是100days的内容和作业内容也要在卡片区看的。这样视野开阔一点」
```

**① "目录"两字**：按钮里本来就只有 `☰`（没有文字）。用户看到的"目录"其实是
**原生 tooltip** 里那句"目录：章节 / 小节 / 知识点" —— 所以问题②修完它自动消失。

**② 悬停提示改成自定义气泡**

原生 `title` 的两个毛病：要悬停 1 秒多才弹、只显示一长串整句。
改成 `data-tip` + 自绘气泡：

- 提示文字放 `data-tip`，**去掉 `title`**（否则两个提示会同时冒出来打架）
- 气泡 `#sbTip` 挂在 **body 上**（不是图标栏里）—— 图标栏自己 `overflow-y:auto`，
  放里面会被裁掉
- 事件**委托到 document**（`mouseover`/`mouseout`），所以以后往图标栏加按钮
  只要写 `data-tip` 就有提示，不用再挂监听
- 延迟 90ms（够快，又不会鼠标扫过时乱闪）；放不下时自动翻到按钮左侧

**③ 内容层也内嵌——这是"视野开阔"的关键**

只把**列表**内嵌是不够的：点进某一天/某道题如果又变成全屏弹层，目录和材料栏照样被盖掉。
实测确认了这个坑：

```
100 Days 点"打开"  → inline=false kind=reader  弹层可见=true   ← 又盖住了
作业   点题目      → inline=false kind=problem 弹层可见=true   ← 又盖住了
```

所以 `INLINE_KINDS` 加上 `reader` 和 `problem`。实测结果：

```
100Days内容: kind=reader  inline=true 弹层=false 正文=6905B 目录还在=true 材料栏还在=true
作业内容:    kind=problem inline=true 弹层=false 正文=2046B 目录还在=true 材料栏还在=true
```

**★ 顺手补了一个必须解决的问题：内嵌的"返回上一层"**

实测 `openDayFile` 只 push `{kind:"reader", day:N}`，**没有"从 100 Days 列表来"这条记录**。
所以直接内嵌的话，关掉某一天就回不到列表（会又开一次那一天）。
→ 加了个只记"上一层 kind"的小栈 `SURF_BACK`，关面板时复原那一层：

```
100Days: 返回栈="days" 关后回列表=true
作业:    返回栈="hw"   关后回列表=true
```

★ 这里有个**容易写错的判断**：`closeModal()` 不能无脑 restore。要分清两种情况：

```js
if (surfaceIsInline()){
  surfaceInlineOff(true);       // 用户按了关闭/Esc → 复原上一层（某天 → 它的列表）
} else {
  $("modalBody").innerHTML = "";  // 只清弹层；内嵌只是顺带清掉 → **不要** restore
}
```

不这么分的话，"看着某一天时点目录"会莫名其妙退回 100 Days 列表（两件不相干的事）。
而翻卡走的是 `renderAll()` → `surfaceInlineOff()`（**不带参数**），那是要真回卡片。

**④ 这一轮又踩的：`<div id="sbTip">` 没落地**

我给图标栏加气泡宿主元素的那次 `edit` 因为 `old_string` 不匹配**失败了**，
但我没察觉——CSS 和 JS 都加上去了，只有那个 div 没进 HTML。
症状：探针抛 `Cannot read properties of null (reading 'getBoundingClientRect')`。
★ 教训：`edit` 失败会报错、不会静默；但**同一轮里我做了多个 edit，只看到后面成功了
就以为前面也成功**。收尾要用一个"存在性检查"把这一轮加的东西**逐个点名**（我用的是
`ct_find_sbtip.py` 那种：HTML/CSS/JS/导出 各查一次）。

**⑦ 事故：助教圆钮"被我干没了"**

```
用户原话：「我右下角的ai助教的按钮你怎么给我干没了」
```

**根因就是我自己上一节那条改动**：我在 `asFabSync()` 里写了"内嵌面板开着时也让位"
（`|| surfaceIsInline()`），**凭感觉以为面板会挡住右下角**。实测：

```
内嵌面板右边界 = 1138      圆钮左边界 ≈ 1426      → 会重叠吗 = false
（视频目录是最长的内嵌面板，一样是 1138）
```

**根本不会重叠**，所以那是白让位，代价是这些状态下助教入口**全部消失**：
100 Days 列表 / 作业列表 / 视频目录 / 某一天内容 / 某一道题内容。

改回只在**完整助手面板**开着时让位（那是全屏弹层，确实会盖住右下角）。
实测所有状态：

```
圆钮各状态=卡片流=true,100Days=true/关后true,作业=true/关后true,视频=true/关后true,搜索=true/关后true
与内嵌面板重叠=false
完整助手面板: hidden=true（这里让位是对的）
★ 不该隐藏却隐藏了的状态: 无
```

**★ 教训（值得记住的规则）**：让位 = 隐藏一个**常驻入口**，代价很大（用户找不到功能），
所以必须有**实测的重叠证据**，判据是量两者的 `getBoundingClientRect` 是否真的相交 ——
不能凭"感觉会挡"。验收里已经把这条**正反两面**都断言了：

- 正面：每个状态下圆钮都必须可见（`fabAllVisible`）
- 反面：同时断言"内嵌面板与圆钮**确实不重叠**"（`!fabOverlap`）——
  以后布局真改了、开始重叠，这条会红，**那时才该去让位**

**⑧ 连带发现：端口文件会被抢写**

`%TEMP%\course-terminal-port.txt` 是**所有实例共写**的。我起测试实例时它会写我的端口，
于是用户实例的端口被覆盖：

```
端口文件: "9050\n34524"   → 解析报 nonnumeric port
```

这个文件只是"最后启动的那个实例的端口"，用来给冒烟测试探端口。多实例并存时它不可靠。
★ 不影响用户使用（窗口自己知道端口），但**用它的脚本要知道这一点**：
别把它当"当前实例的端口"，多实例时它可能是别人的。排障时直接 `netstat` 更稳。

### 👁 读屏：让助教"看得见"屏幕上有什么

```
用户原话：「我想真正让他有读屏能力，可以看见软件里前台都有什么，我在看什么，
不管是卡片，作业，100day，甚至是可视化，我都希望他能知道并给我回应」
```

**① 为什么不走截图 OCR（用户明确说了不要）**

这个前端是单文件 SPA，**所有正文都在自己的 DOM 里** —— 直接遍历可见节点拿到的就是原文，
比 OCR 准（OCR 会把代码里的括号、缩进、`_` 认错）、比 OCR 快、还零成本。
所以"读屏"= 读自己的 DOM，不是看像素。

**② 两路信息，都要给（只有一路各有各的坏法）**

```
asContextPoint()  结构化定位（S.cur / stepAt / readerDay）—— 精确但很窄
                  ↓ 只给这个 → 会出现"看 100 Days 时助教以为你在看卡片"的错位
screenText()      遍历可见 DOM 取纯文本 —— 广但必须截断
                  ↓ 只给这个 → 丢掉"这是第几天的哪一节"这种定位
```

`screenSurfaces()` 决定读哪几块、**按前台优先**：

```
有弹层  → 〔弹层:<kind>〕#modalBody 为主，卡片不再算主内容
         （弹层盖在卡片上，把卡片也读进去是误导）
无弹层  → 〔卡片〕#card 为主，再补 〔材料栏〕#railBody、〔试一试输出〕#replOut
```

界面元素（按钮文字、面包屑、进度点、计数、`⋯ 更多` 菜单）**全部排除** ——
它们会淹没真正的讲义；**助教自己的界面整个排除**（`#asBubble` 的头部/消息区/输入行、
完整面板的 `.asMsgs`），否则它把自己刚说的话读回去当"屏幕内容"。

**③ 可视化那层：整页跳转，读不到 DOM → 让 viewer 自己回报**

`openTutor` 用的是 `window.location.href = "/tutor?..."`（**不是 iframe**），
所以用户在可视化前台时，应用页面根本不在前台，读不到它的 DOM。

办法：`app/main.py` 加了**桥接 3**（只注入 `/tutor`），viewer 用 MutationObserver + 1.5s
兜底，把自己**屏幕上显示的文字**写进 `sessionStorage["ic.tutorstate.v1"]`，
主页面下次启动时读出来放进 `context.tutor`。

★ 刻意**不混进 `screen`**：用户回到主页面时，屏幕上显示的是卡片/层，**不是**可视化；
混进去就是撒谎，模型会以为他正盯着那段代码。所以 system 里是独立一节，
并明说"这是他**刚才**在可视化页面看到的，不是此刻屏幕上的"。

**④ 成本：这块是真花钱的，所以加了护栏**

`screen` 每一轮都要进 system，长度直接等于每轮成本。实测：

```
              改之前      改之后
助教提示词      2356 字     2356 字
上下文块          44 字     3000 字（screen 上限）
system 合计     2400 字     5400 字
```

两处瘦身（**两个都必要**，只做一个省不下来）：
1. `SCREEN_MAX_CHARS` 4500 → **3000**。3000 字足够描述"他在看什么"，再长边际收益很小。
2. **读屏够长时不再重复发 `notes`**（讲义片段）。`notes` 是"这一页的讲义"，
   而 `screen` 里**已经包含**屏幕上这一页的正文 —— 两个都发就是同一段文字发两遍。
   读屏 <800 字（拿不到正文）时才用 notes 兜底。
   ★ 不做这条的话 system 会顶到 9200 字（约 +6800 token/轮）。

验收任务 20 把这两条都断言了，**防止以后有人顺手把上限调大**。

**⑤ 怎么证的（判据是可反驳的，不是"看起来对"）**

免费证明（任务 20）：拦住 `/ai/chat` 看**真实 body**，断言 `context.screen` 有内容、
且不含气泡自己的话。

付费证明（一次调用，<¥0.01，可复现脚本 `%TEMP%\ct_readscreen_paid.js`）：
**先往屏幕塞一个刚生成的随机串** `ZQS1G3CNXK`，再让它复述"屏幕上写的暗号是什么" ——

```
暗号=ZQS1G3CNXK | 暗号已进screen=true | 耗时=2s | 回复="ZQS1G3CNXK" | ★复述出暗号=true
```

★ 为什么非要用随机串：只问"这里讲的什么"的话，答对也可能是靠 `chapter/section`
定位猜的，**证明不了读屏**。随机串是模型不可能见过的东西，复述出来才是证据。

**⑥ 这一轮踩到的**

- `screenTextOf` 里判可见性**必须连祖先一起看**：弹层关掉是自身 `hidden`，
  但材料栏收起是给祖先加 `.collapsed`，只看自身会读到一堆看不见的东西。
- 用 `textContent` 而不是 `innerText`（后者要触发排版、慢，且对隐藏元素行为各处不一致）。
- 第一版自测报 `卡片 len=229`，我以为是漏读，量了才发现 **`card.textContent` 本来就是
  203 字**（那张"课程目标"卡就短）—— 又一次"怀疑之前先量"。
- 注入 viewer 的那段 JS 是用 `%` 格式化的 Python 字符串拼的，里面全是转义反斜杠，
  一处写错整段 `<script>` 就语法错误、**连导航桥一起废掉**（截图里只表现为"药丸不见了"）。
  所以加了 `%TEMP%\ct_tutor_inject_check.py`：把注入的 JS 抠出来交给 `node --check`。

### 🤖 常驻助教（右下角圆钮 + 轻量气泡）

```
用户原话：「让ai助教功能常驻页面，在右下角当做一个圆形按钮，一直存在在页面上，
然后可以感知当前页面内容，从而做到哪里不会问哪里。但是我不希望只是截图并识别屏幕文字。」
```

**① 感知页面靠读结构化状态，不是截图**

基础早就有，缺的只是"常驻"：

```
asContextPoint()   → S.cur / stepAt() → chapter / section / point
asNotesSnippet()   → 按知识点的 notes_lines 去 fetch 讲义原文，截 4000 字
assistantContext() → 组装 {chapter, section, point, notes} 发给服务端
```

`renderAll()` 里挂了一次 `asRefreshCtx()`，所以每次翻卡/跳转都会重算。
实测（气泡开着翻 6 张卡）：

```
ctx1 = "ch01 · 课程简介 · 课程目标"
ctx2 = "ch01 · 计算机科学的基本概念 · 计算机科学属于信息科学的一部分"   变了=true
```

**② 为什么不复用 #modal**

`openModal` 是**单例全屏弹层 + 遮罩**，而 `modalOpen()` 被 30 多处当作"有没有弹层"
的判据（Esc、键盘翻页、拖动选中…）。把助教改成常驻会把整个层栈和浏览器后退搞坏。
所以新做一套独立浮层，**只共享 `AS.msgs` 这份会话状态**：

```
右下角圆钮 (z-index 70)  常驻；完整面板开着时让位（免得盖住弹层右上角）
   ↓ 点一下
轻量气泡 (z-index 75)    上下文 chip + 消息区 + 输入框；代码块也挂 ▶可视化/📋复制
   ↓ ⤢ 展开
完整面板（原来的 openAssistant，长对话用）—— 同一份历史，只是换个窗口
```

层级是**故意**插在中间的：`scrim 40 < repl 45 < modal 60 < 圆钮 70 < 气泡 75 < toast 80`。
验收任务 18 会断言这个顺序，因为插错一层就会被遮罩盖住或盖住弹窗。

**③ 圆钮上那个小圆点**

上下文真的变了才闪一下（1.1s），让"它正跟着你"这件事**看得见** —— 否则"感知页面"
是完全隐形的行为，用户无从察觉。判据是 `章节|小节|知识点` 是否变化，不是无脑闪；
无脑闪会变成一直在跳的干扰源。

**④ 气泡和完整面板共用同一个发送函数**

`assistantSend(text, opts)` 只多了三处分叉：从哪个输入框读、消息区画到哪、
以及流式 delta 与收尾时的渲染路由。所以两边**不可能说的不一样**（同一份 AS.msgs）。

**⑤ 这一轮我犯的错（都是"机器能查、肉眼难查"那类）**

1. **给 `asRefreshCtx` 写了个同名重复定义** —— 后定义的覆盖前一个，差点把完整面板的
   上下文显示弄丢。★ 为此在自检脚本里加了**重复定义检查**（按函数名数 `function X(`）；
   这类错误随着函数变多只会更多。
2. **展开成完整面板后圆钮不隐藏**：`openModal()` 只改 `#modal/#scrim` 的 hidden，
   **不会**调 `applyChrome()`（那是 `closeModal` 才做的），而 `closeAsBubble()` 里那次
   同步发生在 `openModal` 之前。→ 在 `openAssistant()` 里 `openModal` 之后补一次 `asFabSync()`。
3. **Esc 只认输入框**：用户点了发送按钮或头部图标后焦点就不在输入框上了，那时按 Esc
   没反应。→ 判据放宽成"气泡开着就处理"。
4. **输入框 placeholder 被裁 17px**：placeholder 太长（在 380px 宽的框里折成两行），
   而 `asAutoGrow` 只在用户开始打字后才跑，初始高度按一行算。
   实测 `textarea 高 36px / scrollHeight 53px` → 缩短 placeholder，按键说明移到 `title`。
   ★ 顺带给 `.bubInRow` 加 `flex:none`：消息一多、总高触到 `max-height` 时 flex 会把这一行
     压扁（同类隐患一起堵掉）。
5. **差点用"固定 sleep"糊过去**：验收任务 07/08/09/10/12 里有一批探针用的是
   `querySelector(...).click()` 裸调用、不等待节点出现。顶栏重排只是把时序抖了一下就红了一个。
   **那不是重排引入的 bug，是探针本来就有的脆弱性**（更早的运行里同一个探针也抛过
   `Cannot read properties of null`）。→ 批量改成 `waitFor` 轮询，**不是加长 sleep**
   （那只是把偶然性推后）。

**⑥ 顺手发现的、和代码无关但要知道的事**

- 桌面上有一份 `OneDrive\Desktop\计算概论学习终端.exe`，是 **20:29 的旧副本**，
  和快捷方式指向的 `app\dist` 那个**不是同一个文件**。双击那份跑的是旧版。
- 验收脚本的 `Stop-Terminal` 只杀 `app\dist` 里那个 exe（按 `ExecutablePath` 精确匹配），
  不会碰桌面副本；但它**会**杀掉你从 `app\dist` 打开的窗口。
- ★★ **每次跑完整验收大约花 ¥1.5**：第 11 项和第 16 项是**真调用**（不是桩）。
  余额 46.50 → 35.22 主要就是这么走的。想省钱就单跑某一个任务
  （`_dev` 里那个抽取脚本能把单个 job 单独跑起来）。

**⑦ 顶栏那个「🤖 助教」按钮删掉了**

用户问「右上角的那个助教按钮是不是可以去掉了」——可以，而且是**净收益**：

- 它和右下角圆钮**功能完全重复**。本来以为它开的是"完整面板"、圆钮开的是"气泡"，
  算两种东西；但气泡里有「⤢ 展开」直通完整面板，所以顶栏那个的**全部能力**都被
  圆钮覆盖了（`asfab` 是**开关**，再点一次收起）。
- 删之前查清了引用面：`data-act="assistant"` 全项目**只有它一个**来源，没有别处依赖
  （完整面板另有入口：作业里「让 AI 看看我的代码」合并的那条、以及 `?assistant=1` 层）。
- 顺带把窄屏折行也解决了：顶栏按钮 8 → 7 个，`≈600px` 宽度下从 **2 行变回 1 行**。
- 验收第 16 项的断言从"按钮在"改成"**按钮确实不在了、但功能还在**"
  （功能还在 = 能开面板 + 两轮对话 + 历史恢复，这三条本来就在断言里）。
- `act === "assistant"` 那条分支留着（现在没有调用方），当作 `?assistant=1` 那条路的兜底；
  它零成本，删了反而要额外记住"URL 层没有对应的 act"。

★ 代价说清楚：圆钮是个**图标**，顶栏那个是带文字的「🤖 助教」。
从"一眼能发现"的角度，带文字的更直白。如果实际用下来觉得入口太隐蔽、
或者你更想让它留在工具栏，改回去只是加回一行 HTML（那个 act 分支还在）。

### 🔴 P2 · 重打包 + 跑完整终验（**已完成**）

```
exe 125.5 MB（原 121.7MB，+3.8MB：pdfium.dll 6.92MB 减去被换掉的 node 侧代码）
★ 打包脚本自己打印的"体积 119.6 MB"是不可信的：它在写盘**中途**取尺寸。
  以 Get-Item 的结果为准。

已跑通的终验（`_dev\accept.ps1` 带截图）：PASS=14 FAIL=0 ALL GREEN
引擎（`tools\pytutor\_dev\accept.ps1 -SkipShots`）：61 项全通过
★ 加了三条**新断言**，专门盯重建能力（旧 exe 上会红，新 exe 转绿）：
    /health.update.rebuild_supported 必须为 true
    /update/rebuild 的**冻结字段**齐全（ok/phase/rebuild_supported/reason/how/upgrade_path）
    /update/status 同时带 deep 与 rebuild 两段状态

★ 真·端到端（不是探针）：对**打包好的 exe** 发一次 POST /update/rebuild?chapter=ch03，
  35.4s 走完 取件→检测→渲染90页→构建→落盘，结果：
    ok=true slides=90 points=66 anchor_violations=0 relation=M
    project_files_touched=[]        ← 护栏空：项目内容一个字节没被碰
    published = ch03.json / notes\ch03.md / notes\_chapters.json / slides 90张 / images 25张
  然后**立刻**用 HTTP 读回来验证"不用重启就生效"：
    /content/ch03.json            X-Asset-Root = <exe 旁边>\content
    /content/slides/ch03/page-01.png   X-Asset-Root 同上（新落盘那张）
  落盘的那张 PNG 尺寸 1344×756、8bit 真彩 —— 与生产渲染一致。
```

### 🟡 P3 · 数据层遗留
```
· 「收起 ▴」在 42 张缩略图末尾，要收起得滑到底（D 的已知问题，未做）
· 4 张卡的 100Days chip 略吵（3/7/10/7 天）—— 内容管道自己的取舍，已同意
· topic_index 的"提到即标注"口径 → 根治要动 _build-json.py 基线
```

### 🟢 P4 · 用户可能还会报的

```
· title 是悬停提示，触屏看不到
· refs 截断按 day 升序而非相关度
· history.back() 那条"加分项"没做（子进程里验不了 pywebview 行为）
```

---

## 3. 必须知道的硬约束（违反了会出大事）

```
★ 讲义一字不改
  body_md = 讲义原文原样切开。改内容 = 违反契约。
  唯一允许的变换：../images/ → content/images/（120 处）、YouTube iframe → 一行说明（4 处）

★ 知识点 id 是给人看的，不是主键
  形如 ch03-s05-p07。它【会随讲义更新平移】。
  所以：进度、视频映射、任何持久数据【都不许】依赖它。
  基线在 content/notes/_point-ids.txt，104 个，改动必须跑 --check 看漂移

★ 用户数据一个字都不许碰
  %LOCALAPPDATA%\course-terminal\deepseek.json    ← 用户的 API key（35 字符，末4位 644c）
  %LOCALAPPDATA%\course-terminal\progress.json
  测试脚本一律用 %TEMP%，别在项目目录里建文件

★ 别在 PowerShell 命令里放中文
  PS 5.1 + 中文路径 → spawn EPERM（实测过）。用通配符或程序拼路径。

★ 别用通配符删文件
  我干过一次：Get-ChildItem "D:\opencode" -File | Remove-Item → 误删 6 个文件。
  一律字面路径 + 先列后删（或 -WhatIf）。

★ build.ps1 不能用管道/重定向调
  & .\build.ps1 2>&1 | … 或 > log   → 它会挂（PyInstaller 往 stderr 写 INFO，
  PS 当错误 + $ErrorActionPreference='Stop'）。直接 & .\build.ps1 跑。
```

---

## 4. 怎么验证

```powershell
# 引擎（61 项 + DOM id 交叉检查）
& "D:\opencode\tools\pytutor\_dev\accept.ps1" -SkipShots

# 终端（数据完整性 + 24 项 HTTP + 截图）
& "D:\opencode\course-terminal\_dev\accept.ps1"            # 带截图
& "D:\opencode\course-terminal\_dev\accept.ps1" -SkipShots # 不带

# 打包（★ 直接跑，别加管道/重定向）
Set-Location D:\opencode\course-terminal
& ".\app\build.ps1"

# 数据管道自证
python content\notes\_build-json.py --selftest-detect   # 三章必须逐字命中
python content\notes\_build-json.py --check             # 有变化/漂移 → 退出码 1
```

**期望**：引擎 `PASS=5 FAIL=0`；终端 `PASS=5 FAIL=0 ALL GREEN`；
`--selftest-detect` 报 `SELF-TEST PASSED: all 3 chapters reproduced exactly`。

**关键判据（判断"这份文件来自哪一层"）**：看响应头 `X-Asset-Root`
```
...\_MEIxxxx\web   → 打包快照（改源码没用：要重打包，或把文件放 exe 旁边）
...\dist\web       → 便携层，生效了
```

---

## 5. 这一轮的决策记录（为什么是这样）

### 砍掉进度机制（用户拍板："在自动更新面前，进度机制其实不太必要"）

```
删：done / runs / sec / lastPointId   ← 已删（D 做的）
留：ic.ui.v1（面板开关，是设置不是进度）· days（🔥 连续天数，按日期记，id 无关）
降级：「继续上次」→ 书签 {ch,s,p}（位置式，不参与统计，讲义改了最多偏一两张卡）
```

**为什么**：进度依赖知识点 id → 讲义一更新 id 平移 → 进度全指错
→ 必须人工确认 → **就不是"自更新"了**。砍掉之后，讲义怎么改都不损坏任何东西。

**唯一例外**：新 key 还没有时会**从老 key 只读一次 `days`**（否则老用户连签归零）。
老 key 一律不回写、原样留盘。

### videos.json 新形状（内容管道冻结的契约）

```jsonc
// 顶层新增
"key_scheme": "chNN|<point title>",
"levels": {"basic":"基础","main":"主线","extra":"补充","adv":"拔高"},   // ★ UI 从这取中文，别写死
// pages[] 每元素补：stage / chapter / serial / clean_title / is_extra
// mapping 的 key = "chNN|" + chNN.json 里该点的 title
"ch03|字符串的常用方法": {
  "status": "mapped",          // mapped | unmatched（黑马没讲）| pending（待确认，绝不挂错）
  "point_id": "ch03-s04-p08",
  "confirmed": false,
  "videos": [ {page, level, stage, chapter, serial, clean_title, duration, confidence}, … ]
}
```
**过渡期 UI 要同时吃新旧两种形状**（D 已实现：三张索引 + status 缺省时按老逻辑走）。

### 自更新走**丙**（+6.9MB），不走乙（+72MB）

```
丙 = 换纯 Python 的 pypdfium2。实验证明（数字见 §2 P1，这里只留结论）：
  ✅ 抽 PDF 文字**可以换** —— 但不是因为"逐字相同"（那是旧记录的误测），
     而是因为差异只落在**字形变体与标点**上，不参与任何决策；
     真正卡住的是议程页那处原始文本匹配，一行修复即可。
  ✅ 渲染 PNG 有系统性差异，且此前把这件事**记轻了**：
       旧记录写"卡片投影变深变重" —— 方向反了，实测是投影**基本消失**。
       ch03 P86 卡片下沿同一列：A 亮度 72→139 的整条渐变，B 恒在 227~231；
       底色 ch02/ch03 由淡粉（~241,237,243）转极淡冷灰（~243,242,239）
  ✅ 可读性零影响：最佳对齐位移 (0,0)、对比度 14.73→14.61（AA 门槛 4.5）、
     差异像素 87.5% 在非边缘（属"填充/投影"而非字形抗锯齿）
决定：丙。理由不是"投影无所谓"，而是用户对"内容和可读性一样即可"明确点头，
      且乙要付的不止 72MB —— 还要多一条跨进程边界（退出码/stderr/超时/临时目录
      都得自己管），而那条边界的复杂度买不到任何功能。
      另注：乙丙**共享约九成工作量**（把写死的路径改成从 _MEIPASS/可写层取、取件、
      临时工作区、落盘），换发动机只是其中一步 —— 别以为乙是"塞个 node 就完事"。
体积实测：pypdfium2 的原生负载只有 `pypdfium2_raw\pdfium.dll` = 6.92 MB
      （PDFium 自带，不需要任何外部运行时）。这才是丙省下 72MB 的原因。

★ 关于"242/242 逐字命中"这个门槛本身的教训：
  它是个**订错了的门槛**。原始文本本来就不可能逐字相同（字形变体），
  而"输出 JSON 逐字节相同"又是**假绿灯**（build() 读的是冻结的登记表，
  根本不碰 PDF，裸跑连抽取器都不会调用）。唯一有效的判据是
  `--selftest-detect`（两种抽取器各跑一遍，比 non_content_pages 与违规数）
  + 真走一次单章重建。**订门槛时要问：这个判据真的能证伪吗？**
```

---

## 6. 踩过的坑（别再踩）

```
· PS 5.1 读无 BOM 的 .ps1 会按 GBK → 中文变乱码 + 解析失败。ps1 里别放中文字面量
  ★ build.ps1 必须保持 **UTF-8 with BOM + CRLF**。用"替换文本"的编辑方式改它会把
    BOM 和 CRLF 一起弄丢，而且丢了你未必立刻发现 —— 我是靠"解析一下"才看见
    23 个报错 + 满屏乱码（同一份文件在 Py3 里读是好的，所以光看内容看不出来）。
    改完任何 .ps1，务必验一次：首字节 EF BB BF + [Parser]::ParseFile 无错误。
  ⚠️ **这个坑我又踩了一次**（加 `--icon` 的时候），说明"改完记得验"这条不够，
    得把它做成**一步动作**。稳定做法（每改完 .ps1 就整段跑，别靠记）：
        python -c "p='FILE';r=open(p,'rb').read();b=r[3:] if r[:3]==b'\xef\xbb\xbf' else r;
                   b=b.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n');
                   open(p,'wb').write(b'\xef\xbb\xbf'+b)"
        然后 [Parser]::ParseFile 验 $errors.Count -eq 0
    验收脚本 / build.ps1 全按这条走；`_dev\accept.ps1` 与 `app\build.ps1` 都带 BOM。
· 改完 .py/.ps1 都先 `ast.parse` / `[Parser]::ParseFile` 过一遍再说"改好了"
· 通配符删文件 → 我误删过 6 个（含一个文档，从桌面副本恢复了）
· build.ps1 加 2>&1 就挂（见 §3）
· 用 Get-Process 的 $_.CommandLine 过滤 → PS 5.1 里常是空的 → 一个都没杀掉
  （我因此连着测了三轮僵尸服务器，把"修好了"误判成"没修好"）
· 同一个文件别让两个代理同时改 → 会互相覆盖。分工前先确认文件归属
  ★ 这条又应验了一次，而且是**没有并发也在踩**：我一边让子代理改 `_build-json.py`，
    一边自己在同一个内容目录里跑重建，结果我那次把 `content/slides/ch03/` 90 张
    node 渲染的 PNG 全换成了 pdfium 版、`images/_manifest.json` 被截断成 `{}`。
    教训不只是"别并发"，还有：**动共享产物前先确认它有没有别的消费者**。
· 测试桩不 faithful → 假绿灯。D 踩过两次：
    桩里 clearTimeout 是空函数 → 防抖测试"发了 5 次"也显示通过
    桩里 pushState 不改地址栏 → 滚动恢复的 URL 比对永远匹配不上，功能实际不工作
  ★ 所以：桩要照着真行为写；断言要断言"值相等"，不是"看起来差不多"
· 用模拟事件测 UI 会骗人 → 要用 CDP 发【可信按键/鼠标事件】
  （headless 里 element.click() 没有用户手势，target=_blank 会被弹窗拦截）
· 渲染路径和"判断路径"常常是两套规则 → resolveContentPath（认 100days/ 前缀）
  vs resolveContentRel（<img> 用，只认 content/ 前缀）。改路径相关的东西两边都要看
· ★ 假绿灯的三种形态（这一轮全遇到了，写下来备查）：
    1. **判据订错**：拿"原始文本逐字相同"当门槛，而它本来就不可能成立
    2. **判据退化**：拿"输出 JSON 逐字节相同"当引擎等价证明，而 build() 压根不读 PDF
    3. **判据被绕过**：检测器已经塌了（锚点 67→3、违规 1），chNN.json 却仍然逐字节相同，
       因为页序是从冻结的登记表读的。**异常在打分，输出在别处**，于是无人报警
· ★ 静默降级：`build_refs()` 缺 `100days/index.json` 时只打印一行就返回空，
  于是所有知识点的 refs 被清空，而 id/点数/结构全对 → 验收全绿。
  凡是"输入缺了就返回空集合"的函数，都要问一句：**这个空会不会被当成正常结果？**
· ★ **验收脚本不许有用户可见的副作用**。`accept.ps1` 要测 `/open` 的正向路径，
  而 `/open` 的语义就是"交给系统默认浏览器" —— 于是**每跑一次验收，用户的屏幕上
  就真的弹出一个 cs101.openjudge.cn 标签页，还把前台抢走**（用户直接报了这件事：
  "浏览器不停的跳"）。跑了 4 次验收 = 4 个标签页。
  修法：`CT_NO_BROWSER=1` 环境变量（`NO_BROWSER_ENV`），只在设了它时短路
  `os.startfile`。刻意**不用接口参数**：这样生产路径一个字节都不改，`/open` 的
  `ok`/`attempts`/`count` 语义原样保留，断言仍然测得到"它确实走到了要开浏览器这一步"。
  accept.ps1 与 build.ps1 都自己设上这个变量。
  ★ 一般化的教训：**给测试一条会外溢到桌面的路径，迟早会外溢到用户的桌面上。**
· ★ **"截图存在"不等于"探针通过"**。accept.ps1 的截图段原来是
  `if (Test-Path $png) { Ok } else { Bad }` —— 于是探针**抛异常**、什么都没测到，
  只要截了图就报 PASS。我新加的那条 AI 断言第一次跑就是**假 GREEN**：
  它抛了 `Cannot read properties of null (reading 'click')`（元素还没渲染就点了），
  却显示 [PASS]。
  现在改成三条硬判据：探针抛异常 / 返回空串 / 有 `expect` 字段但没匹配上 → 一律 **Bad**。
  ★ 教训：**"没报错"和"文件存在"都不是证据。** 验证一条断言时，先问
    "它要是坏了，我会看到什么？"—— 如果答案是"什么也看不到"，那它就不是断言。
· ★ **测试桩要按 URL 收窄**。我给 AI 断言桩了 `window.fetch`，第一版是**无条件**
  替换全局 —— 结果作业列表自己的 `/content/homework/hw1.json` 也吃到假 SSE 文本，
  `JSON.parse` 直接炸（`Unexpected token 'd'`），作业列表渲染成"数据还在生成中"，
  于是**没有作业行可点**，探针因为一个跟被测 bug 毫无关系的原因失败了。
  桩只在 `url` 含 `/ai/explain` 时才拦截，其余原样转发给真的 fetch。
  ★ 教训：**桩的作用域要精确到"它要假装的那一个请求"**，否则你会得到
    一个"因为别的东西坏了而失败"的测试 —— 它既不能证明功能好，也不能定位问题。
· ★ **共享的固定路径临时文件会互相踩**：`app/main.py` 把端口写在
  `%TEMP%\course-terminal-port.txt`（固定名）。我一边开着 `python main.py --no-window`
  调试、一边起 exe，两边都往同一个文件写，内容变成 `8881\n43584`，
  我的测试脚本只读第一行 → 拿到别人的端口 → 误判"exe 没起来"。
  测试脚本要靠**进程自己的日志行**定位端口（本项目的日志里有"HTTP 已启动：http://127.0.0.1:PORT/"），
  而不是抢那个共享文件。
```

---

## 7. 关键文件地图

```
course-terminal\
  README.md                    使用说明（给用户的，别覆盖）
  SPEC.md                      契约（数据形状、字段语义）
  NEXT-STEPS.md                ★ 本文件
  app\main.py                  HTTP 服务层（~4000 行）：路由/分层查找/SSE/REPL/AI/作业/更新检查
  app\build.ps1                PyInstaller 打包（UTF-8 带 BOM）
  web\index.html               前端全部（~5257 行）：卡片流/层栈/作业/100Days/进度
  _dev\accept.ps1              终端终验（数据 + HTTP + 截图）
  _dev\_fetch-100days-images.py  100Days 图片本地化工具
  content\
    chNN.json                  3 章讲义，按知识点切开，104 个点
    videos.json                视频映射（正在换成新形状）
    notes\_build-json.py       讲义 → JSON 管道（--check / --detect / --add / --selftest-detect）
    notes\_chapters.json       章注册表（sha256 / 页数 / non_content_pages）
    notes\_point-ids.txt       ★ id 基线（漂移检测用，别手改）
    homework\hw1.json          作业一 6 题 + 35 条边界用例
    100days\                   22 篇 md + index.json + 36 张本地图
    images\ slides\            120 张配图 + 242 张课件
tools\pytutor\
  pytracer.py                  逐行追踪引擎（Aborted 必须继承 BaseException）
  explain.py                   中文解说 + 中文报错（~2627 行）
  viewer.html                  可视化页（~1937 行）
  _dev\accept.ps1              引擎 61 项终验
```

---

## 8. 用户可能问的问题（备着）

```
"课件更新了怎么办"  → 顶栏「检查更新」：先「检查更新」（秒级，只发 HEAD），
                      变了就点「重建这一章」/「重建全部变过的章」；写完立刻生效
"怎么分享给别人"    → 一个 exe 拷过去就能用（key 不在里面）；更新内容丢个 content\ 到 exe 旁边
"100Days 在哪看"    → 顶栏 📅 100 Days
"可视化怎么用"      → 卡片代码块「▶ 可视化」，或顶栏「🔬 可视化」（空白页自己写）
```

### 顶栏「🔄 检查更新」怎么用 / 怎么实现的

```
入口   web/index.html 顶栏按钮 data-act="update" → openUpdate()
       URL 是 /?update=1（和 ?search=1 同一套层机制，刷新能回到这一层）

面板   两个动作，刻意分开（后端两种代价差三个数量级，不能混成一个按钮）：
         检查更新   GET /update/check?refresh=1   只发 HEAD 比 ETag/长度，秒级
         下载核对   GET /update/check?deep=1      真下整份算 sha256，1~3 分钟
       ★ 为什么要「下载核对」这一步：快路在**长度相同**时判不出内容是否变化
         （后端如实回 state=unknown 并置 deep_needed），只有下整份才能确定。
       变了 → 每一章一行「重建这一章」+ 一个「重建全部变过的章」

后端   POST /update/rebuild?chapter=chNN    后台线程重建（无 chapter = 重建确证变过的章）
       GET  /update/status                 一个口同时报深检与重建两段进度
       GET  /update/rebuild                能力与状态（rebuild_supported 是**实测**的）

★ 前端两个坑（都踩过）：
  1 fetchJson 加了 60s 超时兜底。所有 /update/* 都走 UPDATE_LOCK，深检在跑时它们
    会一起排队 —— 没有超时的话按钮永远停在「检查中…」，界面看起来像死了，
    而用户完全不知道后台其实在干活。
  2 关掉面板时只 clearInterval、**不清 UP 里的状态**：重建可能还在后台跑，
    重新打开面板应该接着显示进度，而不是假装什么都没发生。
```
