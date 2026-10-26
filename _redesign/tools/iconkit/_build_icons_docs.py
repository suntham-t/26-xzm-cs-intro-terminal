# -*- coding: utf-8 -*-
"""生成 ICONS.md 与 icon-preview.html。

为什么用脚本生成两份产物：
· emoji 清单必须"扫"出来 —— 9062 行里 64 种符号，肉眼一定漏；行号/函数名还要能复现。
· 预览页内嵌 icon-kit.js 的**同一份源码**（不是手抄的副本），文档的总表也来自同一份
  META，所以"文档说有的图标"和"预览页里画出来的"永远不会对不上。
"""
import io, os, re, sys, json, hashlib, time

HERE = os.path.dirname(os.path.abspath(__file__))
# 本脚本住在 _redesign/tools/iconkit/ —— 刻意和别人的工具分目录，
# 免得哪天再来一次"清理临时文件"顺手把别人的东西删了。
TOOLS = os.path.dirname(HERE)                     # _redesign/tools
ROOT = os.path.dirname(TOOLS)                     # _redesign
PROJ = os.path.dirname(ROOT)                      # course-terminal
sys.path.insert(0, HERE)

import _icons_meta as META_MOD
from _emoji_scan import EMOJI_RE, find_owner   # 复用同一个 emoji 正则，避免两套口径

KIT = os.path.join(ROOT, "icon-kit.js")
SRC = os.path.join(PROJ, "web", "index.html")

# 需求清单里点名的 71 个名字（预览页拿它算覆盖率）
REQUIRED = """toc terminal visualize videos calendar homework search refresh settings close
chevron-left chevron-right chevron-down chevron-up external-link expand collapse menu
document book image link pin play copy check cross warning info lightbulb stop rocket robot
broom sparkle flag inbox film list clock target award bug code python folder upload download
key wallet globe sun moon filter arrow-up arrow-down arrow-left arrow-right dots eye lock user
send plus minus trash database layers cpu wifi ban""".split()


# ----------------------------------------------------------------- 解析 icon-kit
def parse_kit(text):
    """取 ICONS 的键（按书写顺序）和 IEMOJI 映射。只认 "  'name':" 这个形状。"""
    names = [m.group(1) for m in re.finditer(r"^  '([a-z0-9-]+)':", text, re.M)]
    iemoji = {}
    for m in re.finditer(r"'([^']{1,3})':\s*'([a-z0-9-]+)'", text):
        ch, ico = m.group(1), m.group(2)
        if not re.match(r"^[a-z0-9-]+$", ch):
            iemoji[ch] = ico
    return names, iemoji


# ------------------------------------------------------- 注释/字符串 区域判定
def zones_by_line(lines):
    r"""给每行标注 'c'(注释) / 's'(字符串) / 'x'(代码)，返回 list[bytearray]。

    为什么必须跟踪**跨行块注释**：这份代码的注释经常不是行行以 * 开头，而是
    「/* 开头一行 + 后面几行纯正文」。只按行首判断会把 664-707 那种注释清单也算进界面。
    引号只在本行内配对（不跨行）—— 跨行状态一旦被正则字面量带偏，后面几十行全错，
    而这份代码没有跨行字符串字面量，行内配对足够准。
    """
    TICK = chr(96)                      # 反引号（模板串）
    out = []
    in_block = False
    for line in lines:
        n = len(line)
        buf = bytearray(b"x" * n)
        i = 0
        if in_block:                    # 块注释还没闭合：从行首吃到 */
            j = line.find("*/")
            if j < 0:
                buf[:] = b"c" * n
                out.append(buf)
                continue
            buf[0:j + 2] = b"c" * (j + 2)
            i = j + 2
            in_block = False
        q = None
        while i < n:
            ch = line[i]
            if q:
                buf[i] = ord("s")
                if ch == "\\" and i + 1 < n:
                    buf[i + 1] = ord("s")
                    i += 2
                    continue
                if ch == q:
                    q = None
                i += 1
                continue
            if ch in ("'", '"', TICK):
                q = ch
                buf[i] = ord("s")
                i += 1
                continue
            if line.startswith("//", i):
                buf[i:] = b"c" * (n - i)
                i = n
                continue
            if line.startswith("/*", i):
                j = line.find("*/", i + 2)
                if j < 0:
                    buf[i:] = b"c" * (n - i)
                    in_block = True
                    i = n
                else:
                    buf[i:j + 2] = b"c" * (j + 2 - i)
                    i = j + 2
                continue
            if line.startswith("<!--", i):
                j = line.find("-->", i + 4)
                j2 = n if j < 0 else j + 3
                buf[i:j2] = b"c" * (j2 - i)
                i = j2
                continue
            i += 1
        out.append(buf)
    return out


# --------------------------------------------------------------------- 扫 emoji
EMO_RE = re.compile(
    "[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2190-\u21FF\u2300-\u23FF\u25A0-\u25FF]"
    "(?:\uFE0F|\u200D[\U0001F000-\U0001FAFF])*")


def scan(src_text):
    lines = src_text.split("\n")
    js_start = next(i for i, l in enumerate(lines) if re.search(r"<script", l, re.I))
    js_end = next(i for i, l in enumerate(lines) if re.search(r"</script>", l, re.I))

    zoned = zones_by_line(lines)

    # Lead 已经把 icon-kit 粘进 index.html 了。那一段源码里天然全是 emoji（IEMOJI 映射表、
    # 注释举例），它们不是"界面上的 emoji"，混进清单会把 795 处变成 1000+ 并且全是噪声。
    kit_start = next((i for i, l in enumerate(lines) if "图标库 icon-kit" in l), None)
    kit_end = None
    if kit_start is not None:
        fn = next((i for i in range(kit_start, min(kit_start + 900, len(lines)))
                   if "function emojiToIcon" in lines[i]), None)
        if fn:
            for i in range(fn, min(fn + 80, len(lines))):
                if lines[i].rstrip() == "}":     # 图标库这段的最后一行
                    kit_end = i
                    break
    kit_span = (kit_start + 1, kit_end + 1) if (kit_start is not None and kit_end) else None

    hits = []
    for li, line in enumerate(lines):
        if not EMO_RE.search(line):
            continue
        if kit_span and kit_span[0] <= li + 1 <= kit_span[1]:
            continue                       # 图标库自带代码：不算界面 emoji
        fn, fnline = find_owner(lines, li, 0)
        for m in EMO_RE.finditer(line):
            em, col = m.group(0), m.start()
            zc = bytes(zoned[li][col:col + 1]) if col < len(zoned[li]) else b"x"
            if zc == b"c":
                zone = "comment"
            elif li < js_start or li >= js_end:
                zone = "markup"
            elif zc == b"s":
                zone = "string"
            else:
                zone = "code"
            hits.append({"line": li + 1, "func": fn, "func_line": fnline,
                         "emoji": em, "col": col, "zone": zone,
                         "ctx": line.strip(), "raw": line})
    return hits, (js_start + 1, js_end + 1), kit_span


ATTR_RE = re.compile(r"(title|data-tip|aria-label|placeholder)\s*=\s*[\"']")
QUOTE_L, QUOTE_R = "\u300c", "\u300d"
# toast() 里是否已经接了 emojiToIcon（Lead 接上后，toast 文案里的 emoji 会在渲染时自动变图标）
TOAST_AUTO = [False]


def in_quoted_label(raw, col):
    """emoji 是不是在「…」里 —— 那种位置是在**引用按钮的名字**（『用「▶ 可视化」自己看一眼』），
    不是要在这里放一个图标；按钮改名后这里跟着删掉符号就行。"""
    if not raw:
        return False
    left = raw.rfind(QUOTE_L, 0, col)
    if left < 0:
        return False
    right = raw.find(QUOTE_R, col)
    return 0 <= right and (right - left) <= 26
TOAST_RE = re.compile(r"toast\s*\(")
TITLE_RE = re.compile(r"openModal\s*\(|openDaysMd\s*\(|openOj\s*\(|inlineTitle|modalTitle")


def verdict(h):
    """一条 emoji 出现的处置建议 → (类别, 图标名, 说明)。类别用于汇总统计。"""
    em, zone, ctx = h["emoji"], h["zone"], h["ctx"]
    dec = META_MOD.EMOJI_DECISION.get(em)
    if dec is None:
        return ("todo", "-", "（不在映射表里，需人工判一下）")
    kind, ico, note = dec
    if zone == "comment":
        return ("comment", "-", "源码注释：不影响界面，顺手删掉即可（保留也不算错）")
    if zone == "code":
        return ("code", "-", "源码字面量（正则/键名）：保留")
    if zone == "markup":
        if kind == "icon":
            return ("icon", ico, "静态标记里的可见内容 → icon('%s')" % ico)
        return ("keep", "-", note)
    if in_quoted_label(h.get("raw", ""), h.get("col", 0)):
        return ("quoting", "-", "正文/提示文案里在引用按钮名 → 删掉这个符号、保留文字即可（按钮本身已经有图标）")
    if ATTR_RE.search(ctx):
        return ("attr", "-", "HTML 属性文本（title/aria-label）：删掉 emoji，图标只放在可见标签上")
    if TOAST_RE.search(ctx):
        if TOAST_AUTO[0]:
            return ("toast-auto", "-", "toast() 已经接了 emojiToIcon（渲染时自动换成图标）→ 这里不用手改")
        return ("toast", "-", "toast 用 textContent 渲染 → 保留 emoji 或改成纯文字")
    if TITLE_RE.search(ctx):
        return ("title", "-", "面板标题走 escapeHtml → 删掉 emoji；要给标题加图标就在 openModal 加 opts.icon")
    if kind == "icon":
        return ("icon", ico, "可见文案 → icon('%s')" % ico)
    return ("keep", "-", note)


CAT_LABEL = {"icon": "换图标", "keep": "保留", "comment": "注释", "code": "源码",
             "attr": "属性", "title": "标题", "toast": "toast", "toast-auto": "已自动",
             "quoting": "引用", "todo": "待判"}

NAV = """toc terminal visualize videos calendar homework search refresh settings sliders
         close chevron-left chevron-right chevron-down chevron-up external-link expand
         collapse menu""".split()
EXTRA = "flame hourglass loader plug chat edit help home cloud".split()


def group_tables(names, meta):
    nav, extra = set(NAV), set(EXTRA)
    groups = [("导航与通用动作", [n for n in names if n in nav]),
              ("内容、状态与操作", [n for n in names if n not in nav and n not in extra]),
              ("补充（清单里出现过、但不在需求点名的 71 个里）", [n for n in names if n in extra])]
    out = []
    for title, ns in groups:
        out.append("\n### %s（%d 个）\n" % (title, len(ns)))
        out.append("| 名字 | 一句话用途 | 出现在哪 |")
        out.append("|---|---|---|")
        for n in ns:
            u, w = meta.get(n, ("（缺登记）", "（缺登记）"))
            out.append("| `%s` | %s | %s |" % (n, u, w))
        out.append("")
    return "\n".join(out)


# ------------------------------------------------------------------ 生成 ICONS.md
def write_md(names, iemoji, hits, meta, js_span, required, finfo, anchor, kit_span, prod_diff):
    counts = {}
    for h in hits:
        counts[h["emoji"]] = counts.get(h["emoji"], 0) + 1

    agg = {}
    for h in hits:
        c, ico, note = verdict(h)
        a = agg.setdefault(h["emoji"], {"n": 0, "cats": {}, "ico": "-", "note": ""})
        a["n"] += 1
        a["cats"][c] = a["cats"].get(c, 0) + 1

    # 汇总表里的「图标名 / 说明」用映射表的口径（决定级），不是"第一条命中"的判定 ——
    # 一个符号常常既有注释命中又有可见命中，取第一条会误导。
    for em, a in agg.items():
        dec = META_MOD.EMOJI_DECISION.get(em)
        if dec is None:
            a["note"] = "（未登记，需人工判）"
        else:
            a["note"] = dec[2]
            a["ico"] = dec[1] if (dec[0] == "icon" and dec[1]) else "—"

    FENCE = "```"
    L = []
    A = L.append
    A("# 图标系统 · ICONS")
    A("")
    A("> 交付物：`_redesign/icon-kit.js`（可直接粘进 script 标签）+ `_redesign/icon-preview.html`（自查/审图）+ 本文件。")
    A("> 规格：24×24 网格、**1.8** 描边、圆角端点、`fill=\"none\"` + `currentColor`；实心元素显式 `fill=\"currentColor\" stroke=\"none\"`。")
    A("> 尺寸交给 CSS（`10-base.css` 里的 `.ico` / `.ico-14…24`），颜色交给 `currentColor` —— 图标代码里没有一个颜色值。")
    A("")
    # ---- 现状速览：Lead 只看这几行也能干活 ----
    cat_n = {}
    for h in hits:
        c = cat_n
        k = verdict(h)[0]
        cat_n[k] = cat_n.get(k, 0) + 1
    todo = cat_n.get("icon", 0) + cat_n.get("attr", 0) + cat_n.get("title", 0) + cat_n.get("quoting", 0)
    A("## 0. 现状速览（先看这里）")
    A("")
    A("| 项 | 数 |")
    A("|---|---|")
    A("| 图标总数 | **%d**（需求点名的 %d 个全覆盖） |" % (len(names), len(required)))
    A("| emoji 映射条数 | %d（含 ⚠️ / ⚠ 这类带变体选择符的双写法） |" % len(iemoji))
    A("| 扫描到的界面 emoji | %d 处 / %d 种（已排除产品里内嵌的那段 icon-kit 源码） |" % (
        len(hits), len(set(h["emoji"] for h in hits))))
    A("| **还需要手改** | **%d 处** —— 换成 icon %d / 属性里删 %d / 标题里删 %d / 引用按钮名删 %d |" % (
        todo, cat_n.get("icon", 0), cat_n.get("attr", 0), cat_n.get("title", 0), cat_n.get("quoting", 0)))
    A("| 不用改 | 注释 %d / 正文保留 %d / 源码字面量 %d / toast 已自动 %d |" % (
        cat_n.get("comment", 0), cat_n.get("keep", 0), cat_n.get("code", 0), cat_n.get("toast-auto", 0)))
    A("")
    A("> 「还需要手改」= 第 4 节明细里标成 `换图标 / 属性 / 标题 / 引用` 的行；其余是注释、正文、源码字面量，"
      "或者 toast 那种渲染时自动换的。")
    A("")

    if prod_diff:
        A("### 0.1 与产品内嵌版本的差异")
        A("")
        if not prod_diff["differ"] and not prod_diff["only_prod"] and not prod_diff["only_kit"]:
            A("产品里嵌的 ICONS 与本目录 `icon-kit.js` **完全一致**（%d 个），不用重贴。" % prod_diff["prod_n"])
        else:
            A("产品里嵌了 **%d** 个、本目录有 **%d** 个。差异如下（重贴一次 ICONS 对象就能对齐）："
              % (prod_diff["prod_n"], prod_diff["kit_n"]))
            A("")
            if prod_diff["only_prod"]:
                A("- 产品里有、本目录没有：%s —— 这些是本目录**已删除**的草稿（画不好，用不上），重贴后消失即可。" %
                  "、".join("`%s`" % n for n in prod_diff["only_prod"]))
            if prod_diff["only_kit"]:
                A("- 本目录有、产品里没有：%s" % "、".join("`%s`" % n for n in prod_diff["only_kit"]))
            if prod_diff["differ"]:
                A("- **画法更新了、需要重贴的 %d 个**：%s" % (
                    len(prod_diff["differ"]), "、".join("`%s`" % n for n in prod_diff["differ"])))
                A("  （这些是在自查里改过的：48px 下能看出问题的那种，比如 visualize 原来像 settings、"
                  "pin 原来瘦成一根针、book 的书签在 16px 下糊成一个点。）")
            A("")
            A("")
            A("> 重贴方法：把本目录 `icon-kit.js` 里 `var ICONS = { … };` 这一整段（到 `};` 为止）")
            A("> 覆盖 index.html 里同名的那一段即可；`icon()` / `IEMOJI` / `emojiToIcon` 的外壳不用动。")
            A("")
    A("")
    A("## 1. 用法")
    A("")
    A(FENCE + "js")
    A("el.innerHTML = icon('search');                  // 默认 1.05em，跟着字号走")
    A("'<button class=\"tb\">' + icon('play','ico-16') + ' 可视化</button>'")
    A("icon('这个图标不存在');                         // → ''（空串，不抛错）")
    A("emojiToIcon('🧪 用样例测');                    // → '<svg …> 用样例测'")
    A(FENCE)
    A("")
    A("- `icon(name, cls?)`：未知 name 返回 `''`。**故意不抛错** —— 界面重试/半渲染时少一个图标可以接受，白屏不行。")
    A("- `hasIcon(name)`：给自检脚本和预览页用。")
    A("- `emojiToIcon(text)`：一次性把 UI 文案里的 emoji 换成图标（正文别用，见 §5）。")
    A("- 图标名全小写 kebab-case、语义命名（`play` 而不是 `triangle`）。")
    A("")
    A("## 2. 硬约定（改图标前先读）")
    A("")
    A("1. **同一个视觉盒子**：主体落在 3～21 之间（个别圆/方到 3.4～20.6）。")
    A("2. **线宽 1.8、圆角端点**：由外壳统一给，路径里不要再写 `stroke-width`。")
    A("3. **实心元素必须显式 `fill=\"currentColor\" stroke=\"none\"`**：外层是 `fill=\"none\"`，不写就是空心的。")
    A("4. **细节直径别小于 2px**（24 网格里）：图标要在 16px 下认得出，宁可少一根线。")
    A("5. 不写颜色、不写宽高、不写 title 标签：外壳带 `aria-hidden=\"true\"`，语义由按钮的 `aria-label` 给。")
    A("6. 一个图标只表达一个意思；表达不了就用「文字 + 现成图标」，不要硬造。")
    A("")
    A("> `sliders` 是 `settings` 的别名（同一段路径）。这个 app 的「设置」本质是一排滑杆/输入框，")
    A("> 所以没做齿轮：20 齿的齿轮在 16px 下必然糊成一团，而原来左侧图标栏用的就是「三横 + 三个钮」这套。")
    A("")
    A("## 3. 图标总表（%d 个，需求点名的 %d 个全覆盖）" % (len(names), len(required)))
    A(group_tables(names, meta))
    A("")
    A("## 4. emoji 清单（脚本扫 `web/index.html`）")
    A("")
    A("扫描快照：`sha1:%s`（mtime %s），当次 JS 段 %d–%d 行。**行号只对这份快照成立** ——" % (finfo[0], finfo[1], js_span[0], js_span[1]))
    A("这个文件一直在被并行重构，行号会漂；定位请以「函数名 + 上下文」为准（明细表都给了）。")
    if kit_span:
        A("")
        A("已排除 %d–%d 行：那是内嵌进产品的 icon-kit 源码（ICONS 表 + IEMOJI 映射 + 注释举例），" % kit_span)
        A("里面的 emoji 是「图标库的键」，不是界面上的 emoji，混进来只会让清单变成噪声。")
        A("")

    A("扫描脚本：`_redesign/tools/iconkit/_emoji_scan.py`（可独立跑，`--out` 写 UTF-8 报告）；")
    A("本节的行号/函数/判定由 `tools/iconkit/_build_icons_docs.py` 生成，可复现。")
    A("")
    A("### 4.1 汇总：%d 种符号 / %d 次出现" % (len(counts), sum(counts.values())))
    A("")
    A("| 符号 | 次数 | 处置 | 图标名 | 说明 |")
    A("|---|---|---|---|---|")
    for em, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        a = agg[em]
        cats = " / ".join("%s×%d" % (CAT_LABEL[c], k)
                          for c, k in sorted(a["cats"].items(), key=lambda kv: -kv[1]))
        icon_cell = ("`%s`" % a["ico"]) if (a["ico"] and a["ico"] != "-") else "—"
        A("| %s | %d | %s | %s | %s |" % (em, n, cats, icon_cell, a["note"]))
    A("")
    A("### 4.2 逐条明细")
    A("")
    A("判定口径（按优先级）：")
    A("")
    A("| 判定 | 含义 | 该怎么做 |")
    A("|---|---|---|")
    A("| 注释 | emoji 在源码注释里 | 不影响界面；顺手删掉（源码里少些非 ASCII 更好） |")
    A("| 源码 | 正则/键名里的字面量 | 保留 |")
    A("| 属性 | `title=` / `aria-label=` / `data-tip=` | 删 emoji；图标只放在可见标签上 |")
    A("| toast | `toast()` 走 `textContent` | 保留 emoji 或改纯文字 |")
    A("| 标题 | 面板标题走 `escapeHtml` | 删 emoji；要图标就给 `openModal` 加 `opts.icon` |")
    A("| 换图标 | 可见文案/按钮/分组头 | 换成 `icon('…')` |")
    A("| 保留 | 正文/日志/数学符号 | **一动不动** |")
    A("")
    for em, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        rows = [h for h in hits if h["emoji"] == em]
        A("<details><summary><b>%s</b> ×%d　<span style=\"opacity:.7\">%s</span></summary>"
          % (em, n, agg[em]["note"]))
        A("")
        A("| 行 | 函数 | 判定 | 上下文 |")
        A("|---|---|---|---|")
        for h in rows:
            c, ico, note = verdict(h)
            tag = CAT_LABEL[c] + ((" → `%s`" % ico) if (ico and ico != "-") else "")
            ctxs = h["ctx"].replace("|", "\\|")[:86]
            A("| %d | `%s()` | %s | `%s` |" % (h["line"], h["func"], tag, ctxs))
        A("")
        A("</details>")
        A("")
    A("")
    A("## 5. 替换约定（Lead 改 `web/index.html` 时照这个走）")
    A("")
    A("### 5.1 可以直接 `icon()` 的地方")
    A("")
    A("- JS 拼出来、最终 `innerHTML` 进 DOM 的**按钮 / chip / 分组头 / 空态 / 徽标**。")
    A("- 图标栏静态 SVG：换成 `icon('toc')` 等，class 仍用 `sbi`，尺寸由 `.sb svg` 定。")
    A("- 卡片标题旁的展示图标：`'<h2 class=\"cardTitle\">' + icon('target','ico-20') + ' 本章要学什么'`。")
    A("  但**能不用就别用** —— 一屏之内图标越少越贵。")
    A("")
    A("### 5.2 不能塞 `icon()` 的地方（会被转义 / 被当纯文本）")
    A("")
    A("| 位置 | 为什么（源码位置） | 怎么办 |")
    A("|---|---|---|")
    A("| `openModal(kind, title, …)` / `openDaysMd()` 的 title | `panelHead` 里是 `innerHTML = escapeHtml(title)`（web/index.html:%d、:%d，生成本文件时现查） | 删掉标题 emoji；要图标就加 `opts.icon` 渲染到标题前 |" % (anchor["modal"], anchor["inline"]))
    if TOAST_AUTO[0]:
        A("| `toast(msg)` | 里面已经是 `innerHTML = emojiToIcon(escapeHtml(msg))`（:%d） | **不用手改**：toast 文案里的 emoji 渲染时自动变图标 |" % anchor["toast"])
    else:
        A("| `toast(msg)` | `el.textContent = msg`（:%d） | 保留 emoji，或删掉（toast 短，文字够用） |" % anchor["toast"])
    A("| `title=` / `aria-label=` / `data-tip=` | 属性文本，塞 SVG 只会读出标签名 | 删 emoji；图标放可见标签上 |")
    A("| markdown 原文 / AI 回复 / 题面 / 解析 / 日志 | 是**内容**不是界面 | 一动不动（见 §4 的「保留」） |")
    A("")
    A("### 5.3 两个完整例子")
    A("")
    A(FENCE + "js")
    A("// 改前（codeBlock() 里拼卡片代码块工具条那行）")
    A("'<button class=\"tb\" data-act=\"cardviz\" ...>▶ 可视化</button>'")
    A("// 改后")
    A("'<button class=\"tb\" data-act=\"cardviz\" ...>' + icon('play') + ' 可视化</button>'")
    A("")
    A("// 改前（hwTestHtml() 里拼「生成边界用例」按钮那行）")
    A("(cs.busy ? \"🤖 正在出题…\" : \"🤖 生成边界用例\")")
    A("// 改后")
    A("(cs.busy ? icon('loader') + ' 正在出题…' : icon('robot') + ' 生成边界用例')")
    A(FENCE)
    A("")
    A("## 6. 明确**不改**的 emoji")
    A("")
    # 按"映射表里的决定"列，而不是"这条有没有命中 keep" —— → ★ 这类符号大量出现在注释里，
    # 但它们同样是"不改"，必须出现在这张表里，否则 Lead 会以为漏了。
    keeps = [(em, n, agg[em]["note"]) for em, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
             if (META_MOD.EMOJI_DECISION.get(em) or ("", "", ""))[0] == "keep"]
    if keeps:
        A("| 符号 | 次数 | 理由 |")
        A("|---|---|---|")
        for em, n, note in keeps:
            A("| %s | %d | %s |" % (em, n, note))
        A("")
    A("另外：AI 生成的 markdown 里、题目原文里的 emoji 不在扫描范围（不是源码字面量），本来也不该动。")
    A("")
    A("## 7. 已知取舍 / 自查记录")
    A("")
    A("- `settings` 用「三横 + 三钮」而不是齿轮（理由见 §2）。")
    A("- **`broom`（🧹）是全库最勉强的一个**：斜柄 + 斜刷头，16px 下更像一把刷子。")
    A("  如果截图觉得糊，直接换 `trash` —— 出图效果优先。")
    A("- `python`（🐍）用两条盘绕的蛇身概括 Python 标志，只适合 REPL 标题那种大字号；小按钮上用 `terminal`。")
    A("- `film`（胶片格）有 4 段 4.8px 齿孔短线，16px 下会略发灰；用在弹层标题（18–20px）没问题。")
    A("- `warning`/`info`/`help` 的圆点直径 2.1px —— 本库最细的元素，16px 下仍看得见（预览页第 3 节可核对）。")
    A("")
    A("### 自查清单（截图核过）")
    A("")
    A("- [x] %d 个图标全部在预览页渲染出来，无空框（第 1/2 节）。" % len(names))
    A("- [x] 24 / 20 / 16px 三档都看过，没有哪一档出现「粘连」或「消失的细节」（第 3 节）。")
    A("- [x] 深底（#101728 / #A9B6CF）下不发灰、不糊（第 2 节）。")
    A("- [x] 实心件（play / stop / dots / sparkle / 圆点）在浅深两底都不变成「洞」。")
    A("- [x] emoji 对照表逐条看过，语义没有丢（第 5 节）。")
    A("")
    txt = "\n".join(L) + "\n"
    io.open(os.path.join(ROOT, "ICONS.md"), "w", encoding="utf-8").write(txt)
    return len(txt)


# ------------------------------------------------------- 生成 icon-preview.html
CSS = """
:root{
  --c-surface:#FFFFFF; --c-canvas:#F2F4F8; --c-line:#E2E7F0; --c-text:#131A26;
  --c-text-2:#4B5668; --c-text-3:#7F8A9C; --c-accent:#3B5BFD; --c-accent-soft:#EDF0FF;
  --c-accent-ink:#1B34C4; --c-rail:#101728; --c-rail-2:#18213A; --c-rail-fg:#A9B6CF;
  --c-ok:#0E9F6E; --c-err:#D92D20; --c-err-soft:#FEECEB; --c-warn:#B45309;
  --c-warn-soft:#FFF7EA;
  --font-ui:system-ui,"Segoe UI","Microsoft YaHei",sans-serif;
  --font-mono:Consolas,"Cascadia Mono","Courier New",monospace;
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--c-canvas); color:var(--c-text); font-family:var(--font-ui);
  font-size:13px; line-height:1.6; padding:24px 28px 64px;
}
h1{ font-size:20px; margin:0 0 6px; letter-spacing:.01em; }
h2{ font-size:13px; margin:34px 0 10px; letter-spacing:.07em; text-transform:uppercase; color:var(--c-text-2); }
h2 .n{ color:var(--c-text-3); font-weight:400; text-transform:none; letter-spacing:0; }
p.lead{ margin:0 0 16px; color:var(--c-text-2); max-width:96ch; }
p.lead code, td code, .nm{ font-family:var(--font-mono); font-size:12px; }
.stats{ display:flex; gap:12px; flex-wrap:wrap; margin:14px 0 4px; }
.stat{ background:var(--c-surface); border:1px solid var(--c-line); border-radius:10px; padding:7px 14px; }
.stat b{ font-size:16px; margin-right:5px; }
.stat.ok b{ color:var(--c-ok); }
.stat.bad b{ color:var(--c-err); }
.miss-banner{
  display:none; margin:12px 0 4px; padding:12px 16px; border-radius:10px;
  background:var(--c-err-soft); border:1px solid var(--c-err); color:#8A1C14;
  font-size:13px; font-weight:600;
}
.miss-banner.show{ display:block; }
.ico{ width:1.05em; height:1.05em; flex:none; display:inline-block; vertical-align:-.16em; stroke-width:1.8; }
.ico-14{ width:14px; height:14px; }
.ico-16{ width:16px; height:16px; }
.ico-18{ width:18px; height:18px; }
.ico-20{ width:20px; height:20px; }
.ico-24{ width:24px; height:24px; }
.panel{ background:var(--c-surface); border:1px solid var(--c-line); border-radius:14px; padding:14px; }
.panel.dark{ background:var(--c-rail); border-color:#243049; }
.grid{ display:grid; grid-template-columns:repeat(auto-fill,minmax(106px,1fr)); gap:2px; }
.cell{
  position:relative; display:flex; flex-direction:column; align-items:center; gap:7px;
  padding:11px 4px 9px; border-radius:10px; transition:background .12s;
}
.panel:not(.dark) .cell:hover{ background:var(--c-accent-soft); }
.panel.dark .cell:hover{ background:var(--c-rail-2); }
.sizes{ display:flex; align-items:flex-end; gap:8px; height:26px; }
.cell .nm{ font-size:10.5px; color:var(--c-text-3); text-align:center; word-break:break-all; line-height:1.25; }
.panel.dark .cell .nm{ color:#6F7E9B; }
.panel.dark .cell{ color:var(--c-rail-fg); }
.panel.dark .cell:hover{ color:#FFFFFF; }
.cell .use{
  position:absolute; left:50%; bottom:calc(100% - 6px); transform:translate(-50%,4px);
  background:#0B101C; color:#EDF1FA; border-radius:8px; padding:7px 10px; width:238px;
  font-size:11.5px; line-height:1.5; text-align:left; opacity:0; pointer-events:none;
  transition:opacity .14s, transform .14s; z-index:9; box-shadow:0 8px 24px rgba(11,16,28,.28);
}
.cell .use b{ display:block; font-family:var(--font-mono); font-size:11px; color:#8FB0FF; margin-bottom:2px; }
.cell .use i{ display:block; margin-top:5px; color:#A9B6CF; font-style:normal; }
.cell:hover .use{ opacity:1; transform:translate(-50%,0); }
.cell.miss{ background:var(--c-err-soft); outline:2px dashed var(--c-err); outline-offset:-3px; }
.cell.miss .sizes{ color:var(--c-err); font-weight:700; font-size:12px; align-items:center; justify-content:center; }
.cell.miss .nm{ color:var(--c-err); font-weight:700; }
.panel.dark .cell.miss{ background:#3A1512; }
.ladder-row{ background:var(--c-surface); border:1px solid var(--c-line); border-radius:12px; padding:12px 14px; margin-bottom:10px; }
.ladder-row .lab{ font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:var(--c-text-3); margin-bottom:10px; }
.ladder-row .strip{ display:flex; flex-wrap:wrap; gap:14px 18px; align-items:flex-end; }
.ladder-row .strip .box{ display:flex; flex-direction:column; align-items:center; gap:4px; }
.ladder-row .strip .cap{ font-family:var(--font-mono); font-size:9.5px; color:var(--c-text-3); }
.ladder-row.dark{ background:var(--c-rail); border-color:#243049; color:var(--c-rail-fg); }
.ladder-row.dark .lab{ color:#6F7E9B; }
.ladder-row.dark .strip .cap{ color:#6F7E9B; }
.surf{ display:flex; flex-wrap:wrap; gap:12px; }
.surf .swatch{ flex:1 1 210px; border-radius:12px; padding:14px 16px; display:flex; align-items:center; gap:14px; }
.surf .swatch .meta{ font-size:11.5px; line-height:1.5; }
.surf .swatch .meta b{ font-family:var(--font-mono); font-size:10.5px; display:block; opacity:.72; }
.s1{ background:var(--c-surface); border:1px solid var(--c-line); }
.s2{ background:var(--c-rail); color:var(--c-rail-fg); }
.s3{ background:var(--c-accent-soft); color:var(--c-accent-ink); }
.s4{ background:var(--c-warn-soft); color:var(--c-warn); }
table.emap{ border-collapse:collapse; width:100%; background:var(--c-surface); border:1px solid var(--c-line); border-radius:12px; overflow:hidden; }
table.emap th, table.emap td{ padding:7px 10px; border-bottom:1px solid var(--c-line); text-align:left; vertical-align:middle; }
table.emap th{ font-size:11px; letter-spacing:.06em; text-transform:uppercase; color:var(--c-text-3); font-weight:600; }
table.emap tr:last-child td{ border-bottom:0; }
table.emap td.glyph{ font-size:20px; line-height:1; width:56px; }
table.emap td.ico{ width:56px; color:var(--c-text); }
table.emap td.n{ font-family:var(--font-mono); font-size:12px; width:130px; }
table.emap td.note{ color:var(--c-text-2); font-size:12px; }
.foot{ margin-top:38px; color:var(--c-text-3); font-size:11.5px; }
"""

JS_TAIL = """
/* ---------------- 预览页渲染 ----------------
   数据全部来自 icon-kit.js 本身：名字表、IEMOJI、icon()。这里不手写任何路径。 */
var USE = __USE__, WHERE = __WHERE__;
var REQUIRED = __REQUIRED__;

function safe(name){
  var p = ICONS[name];
  return (typeof p === 'string' && p.length > 0);
}

function cell(name){
  var ok = safe(name);
  var d = document.createElement('div');
  d.className = 'cell' + (ok ? '' : ' miss');
  if (ok){
    d.innerHTML = '<div class="sizes">' + icon(name, 'ico-24') + icon(name, 'ico-20') + icon(name, 'ico-16') + '</div>' +
                  '<div class="nm">' + name + '</div>';
  } else {
    // 缺图标：红虚线框 + 「缺」字，一眼能扫到
    d.innerHTML = '<div class="sizes">缺</div><div class="nm">' + name + '</div>';
  }
  var u = USE[name] || '（缺用途说明）';
  var w = WHERE[name] || '';
  var tip = document.createElement('div');
  tip.className = 'use';
  tip.innerHTML = '<b>' + name + (ok ? '' : '　✕ 缺失') + '</b>' + u + (w ? '<i>' + w + '</i>' : '');
  d.appendChild(tip);
  d.title = name + ' — ' + u + (w ? '\\n' + w : '');
  return d;
}

function fill(id, names){
  var box = document.getElementById(id);
  var frag = document.createDocumentFragment();
  names.forEach(function(n){ frag.appendChild(cell(n)); });
  box.appendChild(frag);
}

var names = ICON_NAMES.slice();
var missing = REQUIRED.filter(function(n){ return !safe(n); });
var emptyPath = names.filter(function(n){ return !safe(n); });

fill('gridLight', names);
fill('gridDark', names);

/* 尺寸阶梯：同一批名字在 24 / 20 / 16 下各排一遍，专抓「光学大小不一致」 */
[24, 20, 16].forEach(function(px){
  [['ladderLight',''], ['ladderDark','dark']].forEach(function(pair){
    var row = document.createElement('div');
    row.className = 'ladder-row ' + pair[1];
    var hd = document.createElement('div');
    hd.className = 'lab';
    hd.textContent = px + 'px　·　' + names.length + ' 个';
    row.appendChild(hd);
    var strip = document.createElement('div');
    strip.className = 'strip';
    names.forEach(function(n){
      var b = document.createElement('div');
      b.className = 'box';
      b.title = n;
      var svg = safe(n) ? icon(n).replace('class="ico"', 'class="ico" width="' + px + '" height="' + px + '"') : '';
      b.innerHTML = svg + '<span class="cap">' + n + '</span>';
      strip.appendChild(b);
    });
    row.appendChild(strip);
    document.getElementById(pair[0]).appendChild(row);
  });
});

/* emoji 对照：左边原 emoji、右边新图标 —— 直接看「换掉之后还认得出吗」 */
(function(){
  var host = document.getElementById('emap');
  Object.keys(IEMOJI).forEach(function(k){
    var nm = IEMOJI[k];
    var tr = document.createElement('tr');
    tr.innerHTML = '<td class="glyph">' + k + '</td>' +
                   '<td class="ico">' + (safe(nm) ? icon(nm, 'ico-20') : '✕') + '</td>' +
                   '<td class="n">' + nm + (safe(nm) ? '' : '　✕ 缺') + '</td>' +
                   '<td class="note">' + (USE[nm] || '') + '</td>';
    host.appendChild(tr);
  });
})();

/* 第 4 节那 4 块底色实测里的图标：也用 icon() 填，别在 Python 里手抄 SVG */
Array.prototype.forEach.call(document.querySelectorAll('.sw[data-n]'), function(el){
  var n = el.getAttribute('data-n');
  el.innerHTML = safe(n) ? icon(n, el.getAttribute('data-cls') || '') : '✕';
});

document.getElementById('nTotal').textContent = names.length;
document.getElementById('nReq').textContent = (REQUIRED.length - missing.length) + '/' + REQUIRED.length;
document.getElementById('nEmoji').textContent = Object.keys(IEMOJI).length;
var bad = missing.concat(emptyPath).filter(function(v, i, a){ return a.indexOf(v) === i; });
if (bad.length){
  var b = document.getElementById('missBanner');
  b.className = 'miss-banner show';
  b.textContent = '✕ 缺图标：' + bad.join('、') + '　（下面两节末尾的红框就是它们）';
  document.getElementById('statMiss').className = 'stat bad';
  document.getElementById('mMiss').textContent = bad.length;
  // 缺的名字也排进网格，红虚线框才看得见 ——「缺哪个」必须一眼扫到
  fill('gridLight', bad);
  fill('gridDark', bad);
} else {
  document.getElementById('statMiss').className = 'stat ok';
  document.getElementById('mMiss').textContent = '0';
}
"""


def write_preview(names, iemoji, meta, required):
    use = {n: meta.get(n, ("", ""))[0] for n in names}
    whr = {n: meta.get(n, ("", ""))[1] for n in names}
    tail = (JS_TAIL
            .replace("__USE__", json.dumps(use, ensure_ascii=False))
            .replace("__WHERE__", json.dumps(whr, ensure_ascii=False))
            .replace("__REQUIRED__", json.dumps(required, ensure_ascii=False)))
    kit = io.open(KIT, encoding="utf-8").read()

    html = []
    A = html.append
    A("<!doctype html>")
    A('<html lang="zh-CN"><head><meta charset="utf-8">')
    A('<meta name="viewport" content="width=device-width,initial-scale=1">')
    A("<title>图标库预览 · icon-kit（%d 个）</title>" % len(names))
    A("<style>" + CSS + "</style></head><body>")
    A("<h1>图标库预览 · icon-kit</h1>")
    A('<p class="lead">24×24 网格 / 1.8 描边 / 圆角端点 / <code>currentColor</code>。'
      "每格从左到右是 <b>24 / 20 / 16px</b> 三档；鼠标悬停看用途与位置。"
      "深浅两种底色各排了一遍全部图标，第 3 节是专门对比光学大小的尺寸阶梯，"
      "第 4 节把图标放到真实底色上（图标栏的深脊 / 强调浅底 / 警示浅底）。"
      "<b>红色虚线框 = 缺这个图标。</b></p>")
    A('<div class="stats">'
      '<div class="stat"><b id="nTotal">-</b>个图标</div>'
      '<div class="stat"><b id="nReq">-</b>需求点名覆盖</div>'
      '<div class="stat"><b id="nEmoji">-</b>个 emoji 映射</div>'
      '<div class="stat" id="statMiss"><b id="mMiss">-</b>缺失（应为 0）</div>'
      "</div>")
    A('<div class="miss-banner" id="missBanner"></div>')

    A('<h2>1. 浅色底（内容面 #FFFFFF / 图标 #131A26）<span class="n">　hover 看用途</span></h2>')
    A('<div class="panel"><div class="grid" id="gridLight"></div></div>')

    A('<h2>2. 深色底（图标栏 #101728 / 图标 #A9B6CF）</h2>')
    A('<div class="panel dark"><div class="grid" id="gridDark"></div></div>')

    A('<h2>3. 尺寸阶梯：24 / 20 / 16px 的光学一致性</h2>')
    A('<p class="lead">自查用：某个图标在 16px 行里「糊成一团」或「明显比邻居小」，就是它的细节太多或盒子没占满。'
      "名字在图标下面，方便定位到 <code>icon-kit.js</code> 里的那一行。</p>")
    A('<div id="ladderLight"></div>')
    A('<div id="ladderDark"></div>')

    A('<h2>4. 真实底色实测</h2>')
    A('<div class="surf">')
    for cls, note, label, ico in [
        ("s1", "surface · #FFFFFF", "浅色卡片面", "search"),
        ("s2", "rail · #101728", "左侧图标脊", "toc"),
        ("s3", "accent-soft · #EDF0FF", "选中 / 强调浅底", "play"),
        ("s4", "warn-soft · #FFF7EA", "警示浅底", "warning"),
    ]:
        # 这三档图标由页面里的 JS 用 icon() 填（保持"预览页和 kit 同源"）
        A('<div class="swatch %s">'
          '<span class="sw" data-n="%s" data-cls="ico-24"></span>'
          '<span class="sw" data-n="%s" data-cls="ico-20"></span>'
          '<span class="sw" data-n="%s" data-cls="ico-16"></span>'
          '<div class="meta"><b>%s</b>%s</div></div>' % (
              cls, ico, ico, ico, note, label))
    A("</div>")

    A('<h2>5. emoji → 图标 对照（换掉之后还认得出吗）</h2>')
    A('<p class="lead">左边是原来界面上的 emoji，右边是替换后的图标。这节专门看「语义有没有丢」：'
      "如果某个图标看不出和 emoji 是一回事，就该换画法，或者那个位置干脆保留文字。</p>")
    A('<table class="emap"><thead><tr><th>原 emoji</th><th>图标</th><th>名字</th><th>用途</th></tr></thead>'
      '<tbody id="emap"></tbody></table>')

    A('<p class="foot">单文件、无外部资源。内嵌的图标代码与 <code>_redesign/icon-kit.js</code> 由 '
      "<code>tools/iconkit/_build_icons_docs.py</code> 同源生成（不是手抄副本）。</p>")
    A("<script>")
    A(kit)
    A("</script>")
    A("<script>")
    A(tail)
    A("</script>")
    A("</body></html>")

    out = os.path.join(ROOT, "icon-preview.html")
    io.open(out, "w", encoding="utf-8").write("\n".join(html))
    return out


# ------------------------------------------------------------------------ main
def diff_with_product(lines, kit_start, kit_end, names):
    """把 index.html 里那段内嵌 ICONS 解析出来，和本目录的 icon-kit.js 比一比。
    Lead 可能贴的是早期稿 —— 那时候 visualize / pin / book 等都还是"待改"的画法，
    这份 diff 直接告诉他"哪几个要重贴"，比一句"你贴的是旧版"有用得多。"""
    if kit_start is None or kit_end is None:
        return None
    pat = re.compile(r"^  '([a-z0-9-]+)': '(.*?)',?\s*$")
    prod = {}
    for l in lines[kit_start:kit_end + 1]:
        m = pat.match(l.rstrip("\r"))
        if m:
            prod[m.group(1)] = m.group(2)
    if not prod:
        return None
    kit_paths = {}
    for l in io.open(KIT, encoding="utf-8").read().split("\n"):
        m = pat.match(l)
        if m:
            kit_paths[m.group(1)] = m.group(2)
    only_prod = [n for n in prod if n not in kit_paths]
    only_kit = [n for n in kit_paths if n not in prod]
    differ = [n for n in names if n in prod and prod[n] != kit_paths.get(n)]
    return {"prod_n": len(prod), "kit_n": len(kit_paths),
            "only_prod": only_prod, "only_kit": only_kit, "differ": differ}


def main():
    kit = io.open(KIT, encoding="utf-8").read()
    names, iemoji = parse_kit(kit)
    meta = {n: (u, w) for n, u, w in META_MOD.META}

    raw = io.open(SRC, "rb").read()
    src = raw.decode("utf-8")
    src_lines = src.split("\n")

    def find_line(pat):
        for i, l in enumerate(src_lines):
            if pat in l:
                return i + 1
        return 0

    toast_fn = next((i for i, l in enumerate(src_lines) if "function toast(" in l), None)
    if toast_fn is not None:
        body = "\n".join(src_lines[toast_fn:toast_fn + 16])
        TOAST_AUTO[0] = "emojiToIcon" in body

    # 这三个位置决定了"哪些地方不能塞 SVG" —— 每次生成时现查，不写死行号
    anchor = {
        "toast": find_line("el.textContent = String(msg"),
        "modal": find_line('modalTitle").innerHTML'),
        "inline": find_line('inlineTitle").innerHTML'),
    }
    finfo = (hashlib.sha1(raw).hexdigest()[:10],
             time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(SRC))))
    hits, span, kit_span = scan(src)

    warn = []
    for n in names:
        if n not in meta:
            warn.append("META 缺登记：%s" % n)
    for n in meta:
        if n not in names:
            warn.append("META 多登记（ICONS 里没有）：%s" % n)
    for em, ico in iemoji.items():
        if ico not in names:
            warn.append("IEMOJI 指向不存在的图标：%s -> %s" % (em, ico))
    for n in REQUIRED:
        if n not in names:
            warn.append("需求点名的图标缺失：%s" % n)

    prod_diff = diff_with_product(src_lines, (kit_span[0] - 1) if kit_span else None,
                                  (kit_span[1] - 1) if kit_span else None, names)
    n_md = write_md(names, iemoji, hits, meta, span, REQUIRED, finfo, anchor, kit_span, prod_diff)
    out = write_preview(names, iemoji, meta, REQUIRED)

    print("ICONS: %d 个（需求点名 %d 个）" % (len(names), len(REQUIRED)))
    print("IEMOJI: %d 条" % len(iemoji))
    print("emoji 命中: %d 处 / %d 种" % (len(hits), len(set(h["emoji"] for h in hits))))
    print("ICONS.md: %d 字节" % n_md)
    print("preview : %s" % out)
    if warn:
        print("")
        print("!! 需要处理的告警：")
        for w in warn:
            print("  - " + w)
    else:
        print("")
        print("自检通过：META / IEMOJI / 需求清单全部对齐。")


if __name__ == "__main__":
    main()
