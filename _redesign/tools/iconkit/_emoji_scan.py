# -*- coding: utf-8 -*-
"""Emoji 扫描器：把 web/index.html 的 JS 段（以及静态 HTML 段）里所有 emoji 抓出来，
连同行号、所在函数、上下文，输出成便于做替换决策的清单。
为什么用脚本：emoji 散落在 9000 行里，肉眼一定会漏，而且同一符号可能有变体选择符(U+FE0F)。
"""
import re, sys, io, json, argparse

# emoji 覆盖区（够用且不误伤中文标点）：符号/装饰、dingbats、杂项符号、交通、补充符号、
# 变体选择符 FE0F、零宽连接符 200D、以及常见箭头/几何形状（界面里也当图标用）。
EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"
    "\u2600-\u27BF"
    "\u2B00-\u2BFF"
    "\uFE0F\u200D\u20E3"
    "\u2190-\u21FF"   # 箭头
    "\u2300-\u23FF"   # 技术符号 ⏹⏸⏳ …
    "\u25A0-\u25FF"   # 几何形状 ▶◀■□
    "\u00D7\u2715\u2716\u2717\u2718"  # 乘号/叉
    "]"
)

FUNC_PATTERNS = [
    re.compile(r"^\s*(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\("),
    re.compile(r"^\s*(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function|\()"),
    re.compile(r"^\s*([A-Za-z_$][\w$]*)\s*:\s*(?:async\s*)?function\s*\("),
    re.compile(r"^\s*([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{\s*$"),   # method shorthand
]

def find_owner(lines, idx, lower_bound):
    """从 idx 往上找最近的函数定义行；找不到就返回 '<top-level>'。"""
    for j in range(idx, lower_bound - 1, -1):
        for p in FUNC_PATTERNS:
            m = p.match(lines[j])
            if m:
                return m.group(1), j + 1
    return "<top-level>", lower_bound + 1

def classify(context):
    """粗分：UI 控件 vs 正文内容。正文＝拼进 markdown/AI 回复/题面字符串的行。"""
    c = context
    content_hints = [
        "md(", "mdStr", "markdown", "renderMd", "aiText", "reply", "answer", "explain",
        "题目", "答案", "解析", "正文", "note", "desc", "prompt", "toast(", "message",
    ]
    ui_hints = [
        "innerHTML", "textContent", "title=", "aria-label", "btn", "Btn", "btnTxt",
        "placeholder", "label", "ico", "Icon", "icon", "hint", "empty", "chip", "tab",
    ]
    s = c
    ui = sum(1 for h in ui_hints if h in s)
    ct = sum(1 for h in content_hints if h in s)
    if ct > ui:
        return "content?"
    if ui > 0:
        return "ui?"
    return "?"

def cat(ch):
    """把命中字符分为两类：
    icon  = 图形符号，界面里当图标用（大多数要换 SVG）
    text  = 文字符号（箭头/星号/乘号），常常出现在正文句子里，需逐条看上下文
    """
    o = ord(ch[0])
    if 0x2190 <= o <= 0x21FF or o in (0x2605, 0x2606, 0x00D7):
        return "text"
    return "icon"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=r"D:\opencode\course-terminal\web\index.html")
    ap.add_argument("--out", default="", help="把报告写到这个 UTF-8 文件（Windows 控制台是 GBK，直接 print 会乱码）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--all", action="store_true", help="也扫描静态 HTML/CSS 段")
    a = ap.parse_args()

    raw = io.open(a.file, encoding="utf-8").read()
    lines = raw.split("\n")

    # JS 段边界
    js_start = js_end = None
    for i, l in enumerate(lines):
        if js_start is None and re.search(r"<script", l, re.I):
            js_start = i
        elif re.search(r"</script>", l, re.I) and js_start is not None:
            js_end = i
            break
    if js_start is None:
        js_start, js_end = 0, len(lines) - 1

    a_start, a_end = 0, len(lines) - 1
    if not a.all:
        a_start, a_end = js_start, js_end

    hits = []
    for i in range(a_start, a_end + 1):
        line = lines[i]
        chars = EMOJI_RE.findall(line)
        if not chars:
            continue
        # 吞掉变体选择符，保证 '⚠️' 作为一个整体
        seqs = re.findall(
            "[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2190-\u21FF\u2300-\u23FF\u25A0-\u25FF]"
            "(?:\uFE0F|\u200D[\U0001F000-\U0001FAFF])*", line)
        fn, fnline = find_owner(lines, i, a_start)
        hits.append({
            "line": i + 1,
            "func": fn,
            "func_line": fnline,
            "emoji": seqs,
            "kind": classify(line),
            "ctx": line.strip()[:170],
        })

    counts = {}
    for h in hits:
        for e in h["emoji"]:
            counts[e] = counts.get(e, 0) + 1

    if a.json:  # json_out: 结构化输出，方便进一步分组统计
        payload = json.dumps({"hits": hits, "counts": counts}, ensure_ascii=False, indent=1)
        if a.out:
            io.open(a.out, "w", encoding="utf-8").write(payload)
        else:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stdout.write(payload)
        return

    out = io.StringIO()
    def P(*a):
        out.write(" ".join(str(x) for x in a) + "\n")
    print = P
    print("=" * 78)
    print("扫描区间: %d-%d 行 (JS <%d 行 … %d 行>)" % (a_start + 1, a_end + 1, js_start + 1, js_end + 1))
    print("命中行数: %d   唯一 emoji: %d   总出现次数: %d"
          % (len(hits), len(counts), sum(counts.values())))
    print("=" * 78)
    print("\n--- 频次表 ---")
    for e, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        cp = " ".join("%04X" % ord(c) for c in e)
        print("  %-4s x%-3d  [%s] U+%s" % (e, n, cat(e), cp))

    print("\n--- 明细（按行号） ---")
    last_fn = None
    for h in hits:
        tag = "%s() @%d" % (h["func"], h["func_line"])
        if tag != last_fn:
            print("\n  ## %s" % tag)
            last_fn = tag
        print("   L%-5d %-2s %-28s | %s" % (h["line"], "".join(h["emoji"]), h["kind"], h["ctx"][:150]))

    if a.out:
        io.open(a.out, "w", encoding="utf-8").write(out.getvalue())
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(out.getvalue())

if __name__ == "__main__":
    main()
