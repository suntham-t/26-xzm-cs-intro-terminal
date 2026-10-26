#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""apply.py -- 把 _redesign/ 里的分片拼成 web/index.html（唯一写入口）。

重设计把前端拆成：
  · parts/*.css   分组件写（多人并行，互不冲突）
  · shell.html    外壳 DOM
  · src/app.js    逻辑（由 patch_js.py 从 ref/old-app.js 打补丁生成）
再拼回项目要求的**单文件**形式（零外部依赖，PyInstaller 直接打包 web/）。

用法：
  python _redesign/tools/apply.py            # 拼装 + 自检
  python _redesign/tools/apply.py --check     # 只自检，不写文件
  python _redesign/tools/apply.py --no-check  # 只拼装
"""
import re, sys, os, pathlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]          # course-terminal/
RD   = ROOT / "_redesign"
OUT  = ROOT / "web" / "index.html"

CSS_ORDER = ["00-tokens.css", "10-base.css", "20-shell.css",
             "30-card.css", "40-panels.css", "50-ai.css", "90-polish.css"]

def read(p):
    return p.read_text(encoding="utf-8")

def build_css():
    chunks, seen = [], []
    for name in CSS_ORDER:
        p = RD / "parts" / name
        if not p.exists():
            continue
        txt = read(p).strip("\n")
        if not txt.strip():
            continue
        chunks.append("/* ===== %s ===== */\n%s" % (name, txt))
        seen.append(name)
    return "\n\n".join(chunks), seen

def build_html(css):
    head = read(RD / "src" / "head.html").rstrip("\n")
    shell = read(RD / "shell.html").strip("\n")
    js = read(RD / "src" / "app.js").strip("\n")
    return (head + "\n<style>\n" + css + "\n</style>\n</head>\n" + shell
            + "\n<script>\n" + js + "\n</script>\n</body>\n</html>\n")

# ------------------------------------------------------- CSS 结构体检
def css_lint(css):
    """把 CSS 过一遍：注释是否闭合、花括号是否配平、有没有空规则。

    为什么必须查：CSS 是**静默失败**的 —— 少一个 } 或 /* 没闭合，
    后面一连串规则会被浏览器整段丢掉，页面看着"只是有点不对"，
    而在 CSSOM 里查半天才发现某条规则根本不存在。今天就被这个坑绊了一次。"""
    problems = []
    i, n = 0, len(css)
    depth = 0
    line = 1
    rule_start_line = None
    while i < n:
        c = css[i]
        if c == "\n":
            line += 1; i += 1; continue
        if c == "/" and i + 1 < n and css[i + 1] == "*":
            j = css.find("*/", i + 2)
            if j < 0:
                problems.append("第 %d 行开始的注释没有闭合 (*/)" % line)
                break
            line += css.count("\n", i, j + 2)
            i = j + 2
            continue
        if c == "{":
            depth += 1
            if depth == 1:
                rule_start_line = line
            i += 1
            continue
        if c == "}":
            depth -= 1
            if depth < 0:
                problems.append("第 %d 行多了一个 }" % line)
                depth = 0
            i += 1
            continue
        i += 1
    if depth != 0:
        problems.append("文件结束时还有 %d 个 { 没闭合（最后一个从第 %s 行开始）"
                        % (depth, rule_start_line))
    return problems

def strip_css_comments(css):
    """去掉 /* ... */ 再扫 class。

    ★ 为什么：老样式表的**注释**里写过 ".hrow.bottom"、"headMenu .mi" 这类历史说明，
    注释里的 ".xxx" 不是选择器。不剥注释的话，"class 覆盖"检查会永远挂几个幻影类
    （bottom / mi / dailyStreak），于是真出问题时没人再认真看那行 warn。"""
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)

def classes_in_css(css):
    return set(re.findall(r"\.(-?[A-Za-z_][\w-]*)", strip_css_comments(css)))

def strip_js_comments(src):
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "*":
            j = src.find("*/", i + 2); i = n if j < 0 else j + 2; continue
        if c == "/" and nxt == "/":
            j = src.find("\n", i); i = n if j < 0 else j; continue
        if c in ("'", chr(34), chr(96)):
            q = c; out.append(c); i += 1
            while i < n:
                if src[i] == chr(92):
                    out.append(src[i:i + 2]); i += 2; continue
                out.append(src[i])
                if src[i] == q:
                    i += 1; break
                i += 1
            continue
        out.append(c); i += 1
    return "".join(out)

def check(html):
    ok = True
    Q, DQ = chr(39), chr(34)
    print("=" * 70)
    print("自检")
    print("=" * 70)
    for pat in ["<!DOCTYPE html>", "</html>", "<style>", "</style>", "<script>", "</script>", "</body>"]:
        if pat not in html:
            print("  [BAD] 缺少 %s" % pat); ok = False
    print("  [ok ] 结构完整（doctype / style / script / body）")

    n_script = len(re.findall(r"<script>", html))
    if n_script != 1:
        print("  [BAD] script 块 %d 个（应当恰好 1 个）" % n_script); ok = False
    else:
        print("  [ok ] 单一内联 script")

    bad = [p for p in ["<script src", "<link ", "@import", "fonts.googleapis", "cdn.jsdelivr", "unpkg.com"] if p in html]
    if bad:
        print("  [BAD] 出现外部资源: %s" % bad); ok = False
    else:
        print("  [ok ] 零外部依赖（无 link / script src / @import / CDN）")

    css = re.search(r"<style>(.*?)</style>", html, re.S).group(1)
    js = re.search(r"<script>(.*?)</script>", html, re.S).group(1)

    # CSS 结构体检（静默失败的第一现场）
    problems = css_lint(css)
    if problems:
        print("  [BAD] CSS 结构问题：")
        for p in problems:
            print("        · %s" % p)
        ok = False
    else:
        print("  [ok ] CSS 注释/花括号配平")

    # id 交叉检查（判据照 _dev/accept.ps1：整份文件里出现的 id 都算）
    ids = set(re.findall(r'id="([^"]+)"', html))
    js_nc = strip_js_comments(js)
    CONCAT = r"(?!\s*\+)"
    QA = "[" + Q + DQ + "]"
    refs = set(re.findall(r"\$\s*\(\s*" + QA + r"#?([\w-]+)" + QA + r"\s*\)", js_nc))
    refs |= set(re.findall(r"getElementById\(\s*" + QA + r"([\w-]+)" + QA + CONCAT, js_nc))
    refs |= set(re.findall(r"querySelector(?:All)?\(\s*" + QA + r"#([\w-]+)" + QA + CONCAT, js_nc))
    missing = sorted(refs - ids)
    if missing:
        print("  [BAD] JS 引用了 HTML 里没有的 id: %s" % missing); ok = False
    else:
        print("  [ok ] id 交叉检查通过（js refs=%d, html ids=%d）" % (len(refs), len(ids)))

    old = classes_in_css(read(RD / "ref" / "old.css")) if (RD / "ref" / "old.css").exists() else set()
    new = classes_in_css(css)
    lost = sorted(c for c in (old - new) if c and not c[0].isdigit())
    if lost:
        print("  [warn] 老 CSS 的 class 在新样式里没出现（%d 个）: %s" % (len(lost), " ".join(lost)))
    else:
        print("  [ok ] class 覆盖完整（老 CSS 的 %d 个 class 全部保留）" % len(old))

    must = ["sideBar", "toc", "card", "rail", "repl", "modal", "toast", "asFab", "asBubble"]
    lost_ids = [m for m in must if ('id="%s"' % m) not in html]
    if lost_ids:
        print("  [BAD] 关键容器丢失: %s" % lost_ids); ok = False
    else:
        print("  [ok ] 关键容器齐全（图标栏/目录/卡片/材料栏/终端/弹层/toast/助教）")

    tmp = pathlib.Path(os.environ.get("TEMP", ".")) / "ct_apply_check.js"
    tmp.write_text(js, encoding="utf-8")
    try:
        r = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True)
        if r.returncode == 0:
            print("  [ok ] JS 语法通过（node --check）")
        else:
            print("  [BAD] JS 语法错误:\n%s" % r.stderr[:1500]); ok = False
    except FileNotFoundError:
        print("  [warn] 找不到 node，跳过 JS 语法检查")

    print("  [info] 产物 %.1f KB（css %.1f KB / js %.1f KB）" % (
        len(html.encode()) / 1024, len(css.encode()) / 1024, len(js.encode()) / 1024))
    return ok

def main():
    args = sys.argv[1:]
    css, used = build_css()
    html = build_html(css)
    # 先单独体检每个分片：哪个文件有问题要能直接指出来
    for name in used:
        probs = css_lint(read(RD / "parts" / name))
        if probs:
            print("[BAD] %s 结构问题：" % name)
            for p in probs:
                print("      · %s" % p)
    ok = True if "--no-check" in args else check(html)
    if "--check" in args:
        print("\n[--check] 未写文件")
        return 0 if ok else 1
    # ★ newline="\n"：仓库里的 web/index.html 一直是 LF。Python 在 Windows 上
    # 默认把 \n 翻译成 \r\n，那样提交上去 git 会认为**每一行都改了**（12k 行的假 diff）。
    OUT.write_text(html, encoding="utf-8", newline="\n")
    print("\n已写入 %s（%d 行, %.1f KB）" % (OUT, html.count(chr(10)) + 1, len(html.encode()) / 1024))
    print("参与拼装的样式: %s" % (", ".join(used) if used else "(无)"))
    if not ok:
        print("\n★ 自检有失败项，产物已写出但请先修")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
