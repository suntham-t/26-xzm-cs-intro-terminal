#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓取 OpenJudge（xzmdsa.openjudge.cn）题集，生成作业解析 JSON。

用法
----
    python _fetch-oj.py --set 2026ci13hw1 --out hw1.json
    python _fetch-oj.py --set 2026ci13hw2 --out hw2.json --id hw2 --title 作业二
    python _fetch-oj.py --list-sets          # 只列出首页/归档里看到的题集，不抓题
    python _fetch-oj.py --set 2026ci13hw1 --out hw1.json --fetched-at 2026-09-26T15:00:00+08:00

设计要点
--------
* **只用标准库**（urllib / re / json / html / argparse），抓取失败重试 3 次。
* 抓下来的只有「题面」部分（描述/输入/输出/提示/来源 + 样例 + 统计），
  这三样是机器能给的；**解析、坑点、边界用例、参考代码**由人写，
  统一放在下面的 ``AUTHORED`` 表里，按题号索引。抓取时合并进去。
  也就是说：重跑脚本不会覆盖手写内容，只会刷新题面。
* **确定性**：``fetched_at`` 在输出文件已存在时沿用旧值（除非显式给 --fetched-at），
  所以同样的题面反复抓，产出字节级一致，方便 diff / 校验。
* 样例规范化：``\\r\\n`` 和 ``\\r`` 一律变 ``\\n``，结尾补一个 ``\\n``，其余一字不改
  （前导空格、行内空格、空行全部保留）。

加新作业
--------
1. ``python _fetch-oj.py --set <题集slug> --out <hwN>.json --id hwN --title 作业N``
   先跑一遍，题面就抓好了，脚本会在 stderr 提示哪几题还缺 AUTHORED 解析。
2. 给 ``AUTHORED`` 补上对应题号的 ``analysis_md`` / ``pitfalls`` / ``extra_cases`` /
   ``solution_code`` / ``points``（模板见已有题目）。
3. 再跑一遍脚本，然后用 README 里的自测脚本实测每份 solution_code。
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

DEFAULT_BASE = "http://xzmdsa.openjudge.cn"
UA = "Mozilla/5.0 (compatible; course-terminal-homework-fetcher/1.0)"
RETRIES = 3

SECTION_ORDER = ["描述", "输入", "输出", "提示", "来源"]
# P6 的描述里那张「字母 -> 数字」对照表，在页面上是一行一条的 <div>。
# 连续多行这种行会被包成 ``` 代码块，否则 markdown 渲染器会把它们粘成一段。
MAP_LINE = re.compile(r"^[A-Z](,[A-Z])* -> \d$")


# ----------------------------------------------------------------- 抓取

def fetch(url: str, retries: int = RETRIES, timeout: int = 20) -> str:
    last = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            return raw.decode("utf-8")
        except Exception as exc:  # noqa: BLE001  网络问题一律重试
            last = exc
            sys.stderr.write("[warn] 第 %d/%d 次抓取失败 %s：%r\n" % (attempt, retries, url, exc))
            if attempt < retries:
                time.sleep(1.5 * attempt)
    raise RuntimeError("抓取失败（已重试 %d 次）：%s（%r）" % (retries, url, last))


# ----------------------------------------------------------------- HTML -> 文本

def strip_tags(raw: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", raw))


def html_to_lines(raw: str) -> list:
    """把一段 HTML 转成纯文本行列表（丢掉空行与行尾空白）。

    页面上换行有两种意思，得分开处理：

    * ``</p>`` / ``</div>`` / ``</li>`` 和连续两个 ``<br>`` 是**真的分段**，
      无条件断成两行（第 6 题的「字母 -> 数字」对照表就是一行一个 `<div>`）；
    * 单个 ``<br>`` 只是**句内折行**：老师排版时随手敲的。
      这种要看上下文——上一段以句号/分号结尾、或者下一段是 `1.` `2.` 这种编号，
      就当成新行；否则用空格接回同一行。第 5 题的「给定k（1<br/> < k < 100）」
      就是被这个规则救回来的，而第 3 题提示里 `1.…;<br />2.…` 仍然是一行一条。
    """
    s = re.sub(r"<br\s*/?>\s*<br\s*/?>", "\x00", raw, flags=re.I)          # 连续 br = 分段
    s = re.sub(r"</(?:p|div|li|tr|h[1-6])\s*>", "\x00", s, flags=re.I)      # 块级标签 = 分段
    s = re.sub(r"<br\s*/?>", "\x01", s, flags=re.I)                        # 单个 br = 句内折行
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\xa0", " ")

    lines = []
    for block in re.split("\x00", s):
        parts = [p.strip() for p in block.split("\x01")]
        parts = [p for p in parts if p]
        merged = ""
        for part in parts:
            if not merged:
                merged = part
                continue
            prev = merged.rstrip()
            if re.search(r"[。；;：:！!？?]$", prev) or re.match(r"^\d+\s*[.、)]", part):
                lines.append(merged.rstrip())
                merged = part
            else:
                merged = prev + " " + part
        if merged:
            lines.append(merged.rstrip())
    return [ln for ln in lines if ln.strip()]


def section_md(name: str, lines: list) -> str:
    blocks = []
    i = 0
    while i < len(lines):
        if MAP_LINE.match(lines[i]):
            j = i
            while j < len(lines) and MAP_LINE.match(lines[j]):
                j += 1
            if j - i >= 2:
                blocks.append("```\n" + "\n".join(lines[i:j]) + "\n```")
                i = j
                continue
        blocks.append(lines[i])
        i += 1
    return "## %s\n\n" % name + "\n\n".join(blocks)


def norm_sample(text: str) -> str:
    """样例规范化：换行统一成 \\n，结尾补一个 \\n，其余原样保留。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.endswith("\n"):
        text += "\n"
    return text


# ----------------------------------------------------------------- 题集页

def parse_set(page: str, set_url: str) -> dict:
    m = re.search(r'<dd class="end-time-dd">\s*([^<]+?)\s*</dd>', page)
    deadline = None
    if m:
        raw = m.group(1).strip()
        # 页面是 2026-10-10 13:00:00，契约要 2026-10-10 13:00
        mm = re.match(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})", raw)
        deadline = "%s %s" % (mm.group(1), mm.group(2)) if mm else raw

    problems = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        no_m = re.search(r'class="problem-id"><a href="([^"]+)">(.*?)</a>', row, re.S)
        ti_m = re.search(r'class="title"><a href="([^"]+)">(.*?)</a>', row, re.S)
        if not (no_m and ti_m):
            continue
        href = ti_m.group(1)
        problems.append({
            "no": int(re.sub(r"<[^>]+>", "", no_m.group(2)).strip()),
            "title": strip_tags(ti_m.group(2)).strip(),
            "oj_url": href if href.startswith("http") else DEFAULT_BASE + href,
        })
    problems.sort(key=lambda p: p["no"])
    return {"deadline": deadline, "problems": problems}


def list_sets(page: str, base: str = DEFAULT_BASE) -> list:
    """首页上能看到的所有题集：正在进行的 + 计划中 + 已结束（首页只给最近几条）。"""
    found = []

    def add(href, title, when, kind):
        url = href if href.startswith("http") else base + href
        if any(f["url"] == url for f in found):
            return
        found.append({"url": url, "title": strip_tags(title).strip(),
                      "when": strip_tags(when).strip(), "kind": kind})

    cur = re.search(r'<ul class="current-contest label">(.*?)</ul>', page, re.S)
    if cur:
        for href, title in re.findall(r'<a href="([^"]+)">(.*?)</a>', cur.group(1), re.S):
            add(href, title, "", "current")
    for cls, kind in (("coming-contest", "coming"), ("past-contest", "past")):
        blk = re.search(r'<div class="%s label">(.*?)</div>' % cls, page, re.S)
        if not blk:
            continue
        for href, title, when in re.findall(
                r'<li><a href="([^"]+)">(.*?)</a><span>(.*?)</span></li>', blk.group(1), re.S):
            add(href, title, when, kind)
    return found


def fetch_archive_sets(base: str = DEFAULT_BASE, max_pages: int = 5) -> list:
    """/contests/past 的归档表：一次给 20 条，翻页继续。"""
    found = []
    for page_no in range(1, max_pages + 1):
        url = "%s/contests/past" % base + ("" if page_no == 1 else "?page=%d" % page_no)
        page = fetch(url)
        rows = re.findall(
            r'<td class="date">([^<]*)</td>\s*<td class="title"><a href="([^"]+)">(.*?)</a></td>',
            page, re.S)
        if not rows:
            break
        for when, href, title in rows:
            found.append({"url": href if href.startswith("http") else base + href,
                          "title": strip_tags(title).strip(),
                          "when": strip_tags(when).strip(), "kind": "past"})
        if "past?page=%d" % (page_no + 1) not in page:
            break
    return found


# ----------------------------------------------------------------- 题目页

def norm_label(raw: str) -> str:
    """<dt> 里的标签页面上带冒号（「总时间限制: 」「内存限制: 」），统一去掉再比对。"""
    return strip_tags(raw).strip().rstrip(":：").strip()


def parse_problem(page: str, url: str) -> dict:
    limits = {}
    params = re.search(r'<dl class="problem-params">(.*?)</dl>', page, re.S)
    if params:
        for label, value in re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", params.group(1), re.S):
            label = norm_label(label)
            value = strip_tags(value).strip()
            if label == "总时间限制":
                limits["time"] = value
            elif label == "内存限制":
                limits["memory"] = value

    sections, samples = [], {}
    content = re.search(r'<dl class="problem-content">(.*?)</dl>', page, re.S)
    if content:
        for label, body in re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", content.group(1), re.S):
            label = norm_label(label)
            if label in ("样例输入", "样例输出"):
                pre = re.search(r"<pre>(.*?)</pre>", body, re.S)
                samples[label] = html.unescape(pre.group(1) if pre else body)
            else:
                sections.append((label, html_to_lines(body)))

    statement = "\n\n".join(section_md(name, lines) for name, lines in sections
                            if name in SECTION_ORDER)

    stats = {"submitted": None, "tried": None, "passed": None}
    gid = None
    side = re.search(r'<div class="problem-statistics[^"]*">(.*?)</div>', page, re.S)
    if side:
        fields = dict((strip_tags(k).strip(), strip_tags(v).strip())
                      for k, v in re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", side.group(1), re.S))
        gid = fields.get("全局题号") or None
        for key, label in (("submitted", "提交次数"), ("tried", "尝试人数"), ("passed", "通过人数")):
            val = fields.get(label)
            stats[key] = int(val) if val and val.isdigit() else None

    return {
        "oj_url": url,
        "global_id": gid,
        "limits": {"time": limits.get("time"), "memory": limits.get("memory")},
        "statement_md": statement,
        "sample_in": norm_sample(samples.get("样例输入", "")),
        "sample_out": norm_sample(samples.get("样例输出", "")),
        "stats": stats,
    }


# ----------------------------------------------------------------- 手写内容
# 键 = 题号；title 只用来在题目被老师改名/换题时报警。
# extra_cases 的 out 必须是自己推过、实测过的；solution_code 必须能过 sample + 全部 extra。
# 注意 solution_code 一律用 r'''...''' 包，好让代码里的 \t、\n 保持成两个字符。

AUTHORED = {}

AUTHORED[1] = {
    "title": "判断闰年",
    "points": ["ch03-s07-p10", "ch03-s04-p06"],
    "analysis_md": """### 一句话
给一个年份，判断它是不是闰年，输出 `Y` 或 `N`。

### 思路
闰年的定义是「能被 4 整除但不能被 100 整除，或者能被 400 整除」，把它直接翻译成 Python 就是两段用 `or` 连起来的条件：

- `a % 4 == 0 and a % 100 != 0`：普通闰年，比如 2004、2024；
- `a % 400 == 0`：整百年里的特例，比如 2000。

难点全在**整百年**。1900 既能被 4 整除也能被 100 整除，但它不是闰年，所以要靠「不能被 100 整除」把它挡掉；而 2000 又得被 400 整除重新放回来。这两个例外必须写在同一个条件里判断，不能拆成两条独立的 `if` 分别决定输出。

题面提示里还提到「能被 3200 整除的也不是闰年」，但输入范围是 `0 < a < 3000`——**3200 永远不会出现**，不用为它写代码。真加了反而容易踩 `and` 优先级比 `or` 高、括号漏写的坑。

### 常见坑
- 只写 `a % 4 == 0`：输入 `1900` 会输出 `Y`，正确答案是 `N`。
- 漏了 `a % 400 == 0`：输入 `2000` 会输出 `N`，正确答案是 `Y`。
- 用 `or` 把条件放宽，比如 `a % 4 == 0 or a % 100 != 0`：输入 `2999` 会输出 `Y`，正确答案是 `N`。`or` 只要一边成立就为真，`a % 100 != 0` 几乎对所有年份都成立。
- 被提示里的 3200 带偏，写成 `a % 3200 == 0 or a % 400 != 0 or ...`：`and` 比 `or` 先算，条件一长意思就不是你想的了。
- 输出写成 `Yes` / `No` 或小写 `y`：本题只认大写 `Y` 和 `N`。""",
    "pitfalls": [
        "`1900` 要输出 `N`：整百年必须单独判断，光有 `a % 4 == 0` 不够。",
        "`2000` 要输出 `Y`：1900 被 100 挡掉，2000 得靠 `a % 400 == 0` 放回来。",
        "`2999` 要输出 `N`：写成 `a % 4 == 0 or a % 100 != 0` 会输出 `Y`，`or` 把条件放得太松。",
        "提示里的 3200 不用管：输入范围是 0 < a < 3000，加 `a % 3200` 只会引入优先级的新 bug。",
        "只认大写 `Y` / `N`：写成 `Yes`、`No`、小写 `y` 都会 WA。",
    ],
    "extra_cases": [
        {"in": "1900\n", "out": "N\n", "why": "整百年但不能被 400 整除，最经典的坑"},
        {"in": "2000\n", "out": "Y\n", "why": "整百年且能被 400 整除"},
        {"in": "2400\n", "out": "Y\n", "why": "另一个能被 400 整除的整百年，别写成只认 2000"},
        {"in": "4\n", "out": "Y\n", "why": "范围内最小的闰年"},
        {"in": "1\n", "out": "N\n", "why": "最小输入（0 < a），不是闰年"},
        {"in": "2999\n", "out": "N\n", "why": "最大输入，且不能被 4 整除"},
    ],
    "solution_code": r'''a = int(input())
if (a % 4 == 0 and a % 100 != 0) or a % 400 == 0:
    print('Y')
else:
    print('N')''',
}

AUTHORED[2] = {
    "title": "鸡兔同笼",
    "points": ["ch03-s07-p02", "ch03-s05-p01"],
    "analysis_md": """### 一句话
知道笼子里脚的总数是 `a`，求动物总数最少、最多各是多少；一只都凑不出来就输出 `0 0`。

### 思路
设鸡 `c` 只、兔 `r` 只，那么 `2c + 4r = a`，两边除以 2 得 `c + 2r = a/2`。这个式子直接给出两件事：

1. **`a` 必须是偶数**。脚数是 2 的倍数，`a` 是奇数时方程无解，输出 `0 0` 就完事——这是本题唯一的分支，必须先判掉。
2. 动物总数 `c + r = a/2 - r`。**兔子越多总数越少，兔子越少总数越多**（兔子 4 条腿顶两只鸡）。所以：
   - 最多：`r = 0`，全是鸡，`a // 2` 只；
   - 最少：`r` 尽量大，`r = a // 4`，再拿剩下的 2 条腿凑一只鸡，合起来是 `(a + 3) // 4`（也就是 ceil(a/4)）。

也可以不推公式：从小到大枚举兔子数，第一个满足 `(a - 4r) >= 0` 且是偶数就是最少，`r = 0` 就是最多。`a` 最大 32767，循环几万次完全跑得动。公式法更快也不容易写错，推荐。

### 常见坑
- **`a` 为奇数忘了输出 `0 0`**：输入 `21`，不少同学继续往下算，输出 `5 10` 之类的假答案。奇数必须单独一个分支。
- `if` 漏了 `else`，写成两段独立的 `if`：奇数时先打印 `0 0`，又被后面的公式覆盖，`32767` 的输出就错了。
- 最少写成 `a // 4`：那是「全是兔子」的腿数上限，不是答案。输入 `6` 的正确答案是 `2 3`，写 `6 // 4` 会得到 1。
- 两个数写反了：输出顺序是**先最少、后最多**，`20` 的答案是 `5 10`。
- 用了 `input('请输入')`：提示文字会被当成输出，直接 WA。""",
    "pitfalls": [
        "`a` 是奇数就无解：输入 `21`，一只动物都凑不出来，要输出 `0 0`。",
        "`if a % 2` 这个分支必须和后面的计算互斥（要有 `else`），否则输入 `32767` 会先打 `0 0` 再被打公式覆盖。",
        "最少动物数是 `(a + 3) // 4` 而不是 `a // 4`：输入 `6` 的答案是 `2 3`。",
        "输出顺序是先最少、后最多：`20` 是 `5 10`，别写反。",
        "别写 `input('请输入')`：提示文字会被当成输出，本题输入只有一行。",
    ],
    "extra_cases": [
        {"in": "2\n", "out": "1 1\n", "why": "最小的偶数脚数，只能是 1 只鸡"},
        {"in": "6\n", "out": "2 3\n", "why": "检验「最少」的向上取整：1 兔 1 鸡 = 2 只，3 只鸡 = 3 只"},
        {"in": "1\n", "out": "0 0\n", "why": "最小输入且是奇数，无解"},
        {"in": "16384\n", "out": "4096 8192\n", "why": "大偶数，最少是 4096 只兔子"},
        {"in": "32766\n", "out": "8192 16383\n", "why": "范围内最大偶数"},
        {"in": "32767\n", "out": "0 0\n", "why": "范围内最大输入，奇数无解"},
    ],
    "solution_code": r'''a = int(input())
if a % 2 != 0:
    print(0, 0)
else:
    print((a + 3) // 4, a // 2)''',
}

AUTHORED[3] = {
    "title": "餐厅订单页面设计",
    "points": ["ch03-s06-p09", "ch03-s06-p08", "ch03-s07-p09"],
    "analysis_md": """### 一句话
把订单列表汇总成一张表：行是桌号（按数值升序），列是餐品名（按字母升序），格子里是数量，列之间用制表符分隔。

### 思路
这题本质是「分组计数 + 排版」，拆成三步就清楚了。

1. **收集所有餐品名**：扫一遍订单，用集合去重，再 `sorted()` 得到列顺序。题目说「按字母顺序」，Python 对字符串默认按字符编码比较，正好就是题目要的顺序。
2. **收集所有桌号**，同样去重后排序。桌号是整数，要按**数值**升序（样例里 3、5、10 就是这个意思），千万别按字符串排——字符串序会把 `10` 排到 `5` 前面。
3. **计数**：用字典，键是 `(桌号, 餐品)` 这个二元组，值是数量。输出时对每张桌子把**所有列**都过一遍，字典里查不到的就写 0。

读入是本题真正的陷阱。每行是 `姓名,桌号,餐品`，而姓名和餐品里**允许有空格和连字符**（比如 `Fried Chicken`、`Cha-Cha`）。所以只能按逗号切分；对整个行用 `split()` 按空白切的话，`John Smith,7,Pizza` 会被切成 4 段，行就散架了。姓名对答案完全没用，切出来丢掉即可。

输出格式：第一行是 `Table` 加各餐品名；**每行数据之间空一行**；最后一行数据后面不要再补空行。样例输出在网页上看起来是空格对齐的，那只是因为制表符被按 8 列宽度展开显示了，真要提交必须输出 `\\t`。

### 常见坑
- 桌号按字符串排序：输入桌号 `100`、`2`、`10`，字符串序会输出 10、100、2，正确顺序是 2、10、100。
- 对整行用 `split()` 或 `split(', ')`：姓名或餐品里有空格就会切多段，试试 `John Smith,7,Fried Chicken`。
- 漏掉数量为 0 的格子：只有 `1` 号桌点了 `Water`、`2` 号桌点了 `Ceviche` 时，两张桌子都要把两列写全，缺的补 0。
- 用空格而不是制表符分隔列：题目明确要求 `\\t`。""",
    "pitfalls": [
        "桌号要按数值排序：输入桌号 2、10、100，字符串排序会得到 10、100、2。",
        "姓名和餐品里有空格（`John Smith,7,Fried Chicken`），只能按逗号切分，不能对整行用 `split()`。",
        "每张桌子都要把所有餐品列写全，没点的写 0，不能空着。",
        "列之间用制表符 `\\t` 而不是空格；样例在网页上显示成空格，是制表符被按 8 列展开了。",
        "数据行之间要空一行，但最后一行后面不要再补空行。",
    ],
    "extra_cases": [
        {"in": "1\nAlice,1,Pizza\n",
         "out": "Table\tPizza\n\n1\t1\n",
         "why": "只有一张桌子、一个餐品的最小情形"},
        {"in": "3\nBob,10,Water\nAnn,2,Water\nCid,10,Water\n",
         "out": "Table\tWater\n\n2\t1\n\n10\t2\n",
         "why": "同一餐品按桌号汇总，且桌号要按数值升序：2 在 10 前面"},
        {"in": "3\nA,100,X\nB,2,X\nC,10,X\n",
         "out": "Table\tX\n\n2\t1\n\n10\t1\n\n100\t1\n",
         "why": "字符串排序会把 10、100 排到 2 前面，这里检验数值排序"},
        {"in": "2\nJohn Smith,7,Fried Chicken\nAmy,7,Fried Chicken\n",
         "out": "Table\tFried Chicken\n\n7\t2\n",
         "why": "姓名和餐品里都有空格，只能按逗号切分"},
        {"in": "4\nA,500,Water\nB,1,Ceviche\nA,500,Ceviche\nB,1,Ceviche\n",
         "out": "Table\tCeviche\tWater\n\n1\t2\t0\n\n500\t1\t1\n",
         "why": "没点的餐品要补 0，桌号 500 是上界"},
        {"in": "4\nA,1,X\nA,1,X\nA,1,Y\nB,1,X\n",
         "out": "Table\tX\tY\n\n1\t3\t1\n",
         "why": "同一桌重复点同一道菜要累加；列按字母序 X 在 Y 前"},
    ],
    "solution_code": r'''import sys

data = sys.stdin.read().split('\n')
n = int(data[0])

records = []
foods = set()
tables = set()
for i in range(1, n + 1):
    name, table, food = data[i].rstrip('\r').split(',')
    t = int(table)
    records.append((t, food))
    foods.add(food)
    tables.add(t)

count = {}
for t, food in records:
    count[(t, food)] = count.get((t, food), 0) + 1

rows = ['\t'.join(['Table'] + sorted(foods))]
for t in sorted(tables):
    rows.append('\t'.join([str(t)] + [str(count.get((t, f), 0)) for f in sorted(foods)]))

print('\n\n'.join(rows))''',
}

AUTHORED[4] = {
    "title": "Say hello to new friends",
    "points": ["ch03-s04-p08", "ch03-s07-p09"],
    "analysis_md": """### 一句话
读入 N 句自我介绍，每句都长成 `My name is XXX!`，把名字抠出来，输出 `Hello, XXX!`。

### 思路
第一行是 N，后面 N 行是自我介绍。名字就是固定前缀 `My name is ` 之后、结尾 `!` 之前的那一段。

抠法有两种：
- **按固定前缀切**：`line[len('My name is '):]` 拿到后半段，再去掉末尾的 `!`。这样名字里带空格（`My name is Li Ming!`）也能整段保留。
- 按空白切再取最后一个词 `line.split()[-1]`：样例能过，但名字带空格就只剩最后一段，不推荐。

循环次数由第一行的 N 决定，所以读 N 行就停，别用 `while True` 读到文件尾。两种写法这题都能过，但按 N 读最直接，也方便以后处理「N 后面还有别的内容」的题。

输出用字符串拼接或 f-string，注意 `print` 逗号分隔会自动加空格。

### 常见坑
- 题面的「输出」一栏只写了「老师向每一位同学say hello!」，没写格式——**真正的格式在样例里**：`Hello, 名字!`，逗号后面有空格，感叹号是英文 `!`。
- 忘了去掉结尾的 `!`：输出变成 `Hello, Chicky!!`。
- 用 `print('Hello, ', name, '!')`：逗号会自带一个空格，输出 `Hello,  Chicky !`，多两个空格。
- 名字带空格时用 `split()[-1]`：`My name is Li Ming!` 会变成 `Hello, Ming!`。
- 行尾的 `\\r` 没处理：用 `sys.stdin.read().split('\\n')` 时，Windows 换行会让最后一列带上 `\\r`，输出里混进回车。用 `strip()` 清一下最稳。
- 读了 N-1 行或 N+1 行：输出行数就错了，核对一下题目给的 N 是「同学数」还是「总行数」。""",
    "pitfalls": [
        "结尾的 `!` 要去掉，否则输出 `Hello, Chicky!!`。",
        "`print('Hello, ', name, '!')` 会多出空格（逗号自带空格），得到 `Hello,  Chicky !`。",
        "名字可能带空格，用 `split()[-1]` 会把 `Li Ming` 砍成 `Ming`，要按固定前缀 `My name is ` 切。",
        "`sys.stdin.read().split('\\n')` 在 Windows 换行下会留下行尾 `\\r`，输出里会混进回车。",
        "按第一行的 N 决定读几行，多读或少读都会错位。",
    ],
    "extra_cases": [
        {"in": "1\nMy name is A!\n", "out": "Hello, A!\n", "why": "N = 1 的最小情形"},
        {"in": "2\nMy name is Cha-Cha!\nMy name is Boom-Boom!\n",
         "out": "Hello, Cha-Cha!\nHello, Boom-Boom!\n", "why": "名字里有连字符"},
        {"in": "1\nMy name is Li Ming!\n", "out": "Hello, Li Ming!\n",
         "why": "名字里有空格：按固定前缀切才拿得到全名，用 split()[-1] 会变成 Ming"},
        {"in": "3\nMy name is Chicky!\nMy name is Cha-Cha!\nMy name is Lya-Lya!\n",
         "out": "Hello, Chicky!\nHello, Cha-Cha!\nHello, Lya-Lya!\n", "why": "三行输出，别多别少"},
        {"in": "2\nMy name is R2-D2!\nMy name is Li Ming!\n",
         "out": "Hello, R2-D2!\nHello, Li Ming!\n",
         "why": "名字里有数字、连字符和空格，整段照抄，别自己裁剪"},
    ],
    "solution_code": r'''import sys

data = sys.stdin.read().split('\n')
n = int(data[0])

out = []
for i in range(1, n + 1):
    line = data[i].strip()
    name = line[len('My name is '):]
    if name.endswith('!'):
        name = name[:-1]
    out.append('Hello, ' + name + '!')

print('\n'.join(out))''',
}

AUTHORED[5] = {
    "title": "整数的个数",
    "points": ["ch03-s05-p02", "ch03-s07-p04"],
    "analysis_md": """### 一句话
读入 k 个 1 到 10 之间的正整数，分别数出 `1`、`5`、`10` 各出现了几次，输出三行。

### 思路
数据量不到 100 个数，怎么写都能过，重点是把「数数」做干净、别在读入上翻车。

最省事的一种：`sys.stdin.read().split()` 把所有 token 都读成字符串，`data[0]` 是 k，后面就是那 k 个数，然后直接 `nums.count('1')`、`nums.count('5')`、`nums.count('10')`。字符串比较在这里恰好是对的——`'10'` 和 `'1'` 是两个不同的 token，不会互相干扰。用 `split()` 还有个好处：行尾多余的空格（样例第二行末尾就有一个）自动被吃掉。

喜欢整数也行：转成 `int` 之后 `nums.count(1)`、`nums.count(5)`、`nums.count(10)`，结果一样。

再多想一步，这类「取值只有 1~10」的统计可以用桶计数：开一个长度 11 的数组，读一个数就 `cnt[x] += 1`，最后直接输出 `cnt[1]`、`cnt[5]`、`cnt[10]`。这是统计题的通用套路，遇到取值范围大的时候换成 `collections.Counter` 就行。

### 常见坑
- 用 `input().count('1')` 去数字符：`10` 里面也含一个 `1`，会被多算。输入 `10 10` 应该输出 `0 0 2`。
- 用 `if '1' in token` 之类的判断：`10` 同样会命中 `'1'`。
- 没按 k 截断：多读或者读串了行，答案就偏了。稳妥做法是只取前 k 个 token。
- 少输出行：题目要求**三行**，次数是 0 也要老老实实输出 `0`。
- 用 `input('请输入 k:')`：提示文字会被当成输出，直接 WA。

顺便记住 k 的范围是 1 < k < 100，也就是至少 2 个、最多 99 个数。""",
    "pitfalls": [
        "`10` 里也含字符 `1`，用 `count('1')` 数字符会把 `10` 多算一次：输入 `10 10` 应输出 `0 0 2`。",
        "要按第一行的 k 只取前 k 个数，多读或少读都会算错。",
        "次数为 0 也要输出，题目要的是固定三行。",
        "样例第二行末尾有一个多余空格，用 `split()` 读就不用管这些。",
        "别写 `input('请输入 k:')`：提示文字会被当成输出。",
    ],
    "extra_cases": [
        {"in": "2\n1 1\n", "out": "2\n0\n0\n", "why": "某个数出现 0 次也要输出 0"},
        {"in": "2\n10 10\n", "out": "0\n0\n2\n", "why": "`10` 不能算进 `1` 的次数里"},
        {"in": "2\n1 10\n", "out": "1\n0\n1\n", "why": "`1` 和 `10` 是两个不同的数，各自算一次"},
        {"in": "3\n5 5 5\n", "out": "0\n3\n0\n", "why": "只统计 5 的情形"},
        {"in": "3\n1 5 10\n", "out": "1\n1\n1\n", "why": "三个目标数各一个"},
        {"in": "99\n" + "10 " * 99, "out": "0\n0\n99\n", "why": "k 的上界 99，且每行末尾带空格"},
    ],
    "solution_code": r'''import sys

data = sys.stdin.read().split()
k = int(data[0])
nums = data[1:1 + k]

print(nums.count('1'))
print(nums.count('5'))
print(nums.count('10'))''',
}

AUTHORED[6] = {
    "title": "方便记忆的电话号码",
    "points": ["ch03-s06-p09", "ch03-s04-p08", "ch03-s06-p03"],
    "analysis_md": """### 一句话
把一堆「方便记忆的电话号码」都翻译成标准格式 `xxx-xxxx`，找出出现次数 ≥ 2 的，按升序输出号码和次数；一个都没有就输出 `No duplicates.`。

### 思路
三步：**翻译 → 计数 → 排序输出**。

**翻译**：字母按对应表换成数字、去掉所有 `-`、剩下的 7 位数字在第 4 位前插一个 `-`。对应表是 `ABC→2`、`DEF→3`、`GHI→4`、`JKL→5`、`MNO→6`、`PRS→7`、`TUV→8`、`WXY→9`——注意**没有 Q 和 Z**。

建表有个经典写法是「一组字母当一个键」：

```python
l2n = {'ABC': '2', 'DEF': '3', 'GHI': '4'}
```

写成这样，查表时必须拿**单个字母**去查，不能写 `if ch in l2n`——`'I' in l2n` 永远是 `False`，因为键是 `'ABC'`、`'DEF'` 这种整串，单个字母不在里面。要么把每个字母都展开成键，要么干脆用 `str.maketrans` 一次建好转换表，`'ABCDEFG'.translate(table)` 直接出结果，又快又不容易写错。

还有一点：**映射出来的必须是字符串**。写 `'ABC': 2`（整数）的话，`'4' + 2` 会直接 `TypeError`，得处处 `str()`。

**计数**：字典 `count[号码] = count.get(号码, 0) + 1`。

**排序输出**：号码格式固定 7 位数字加一个 `-`，位宽一样，所以按字符串排序和按数值排序结果相同，`sorted(count)` 就够。只输出次数 ≥ 2 的；如果一行都没有，输出一行 `No duplicates.`（结尾有句点）。

### 常见坑
- 映射表用整组字母当键：`'I' in l2n` 恒为 `False`，`888-GLOP` 直接翻译不出来。
- 映射值写成整数 `2`：和数字字符拼接时 `TypeError`。
- `-` 没全部丢掉：`-4-8-7-3-2-7-9-` 首尾都有 `-`，翻译后必须正好 7 位。
- 没有重复号码时忘了输出 `No duplicates.`（少个句点也是 WA），或者干脆什么都不输出。
- 次数为 1 的号码也输出了：题目只要重复出现的。""",
    "pitfalls": [
        "映射表若写成 `{'ABC': '2'}`，查表要用单个字母，`'I' in l2n` 恒为 False。",
        "映射值要用字符串 `'2'`，用整数 `2` 和数字字符拼会 TypeError。",
        "`-` 必须全部丢掉，包括首尾：`-4-8-7-3-2-7-9-` 翻译后也是 487-3279。",
        "没有重复号码时输出一行 `No duplicates.`（带句点），次数为 1 的号码不输出。",
        "第一行的 n 就是记录条数，后面正好 n 行；再多读一行会把第一条记录吃掉。",
    ],
    "extra_cases": [
        {"in": "2\n0000000\n000-0000\n", "out": "000-0000 2\n", "why": "全 0 号码 + 两种写法（不写分隔符 / 写了分隔符）"},
        {"in": "1\n4873279\n", "out": "No duplicates.\n", "why": "只有一条，必然没有重复"},
        {"in": "4\nWXY2345\n9992345\n9999999\n0000000\n", "out": "999-2345 2\n",
         "why": "W/X/Y 都映射成 9，和数字 9 等价；只出现 1 次的两个号码不输出"},
        {"in": "4\n2222222\n1111111\n1111111\n2222222\n", "out": "111-1111 2\n222-2222 2\n", "why": "多个重复号码要按号码升序输出"},
        {"in": "2\nADGJMPT\n2345678\n", "out": "234-5678 2\n", "why": "字母逐组验证：A→2 D→3 G→4 J→5 M→6 P→7 T→8"},
        {"in": "5\n4873279\n4873279\n4873279\n3101010\n3101010\n",
         "out": "310-1010 2\n487-3279 3\n", "why": "两个号码各重复，次数不同也要正确"},
    ],
    "solution_code": r'''import sys

TABLE = str.maketrans('ABCDEFGHIJKLMNOPRSTUVWXY', '222333444555666777888999')

data = sys.stdin.read().split()
n = int(data[0])

count = {}
for token in data[1:1 + n]:
    digits = token.upper().replace('-', '').translate(TABLE)
    number = digits[:3] + '-' + digits[3:]
    count[number] = count.get(number, 0) + 1

out = []
for number in sorted(count):
    if count[number] >= 2:
        out.append(number + ' ' + str(count[number]))

if out:
    print('\n'.join(out))
else:
    print('No duplicates.')''',
}


# ----------------------------------------------------------------- 实测（走本地运行器）

DEFAULT_RUNNER = "http://127.0.0.1:8896"


def _norm_for_cmp(text: str) -> str:
    """比较输出用的规范化：换行统一、去掉行尾空白和末尾空行；行内空格保留。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def out_matches(got: str, want: str) -> bool:
    """先严格比；再按 expandtabs(8) 比一次。

    第 3 题要求列之间用制表符，但 OJ 页面上的样例输出把制表符按 8 列展开成了空格
    （页面存的字面量就是空格），所以那题的样例只能靠展开对齐来比。
    """
    a, b = _norm_for_cmp(got), _norm_for_cmp(want)
    return a == b or a.expandtabs(8) == b.expandtabs(8)


def run_on_runner(endpoint: str, code: str, stdin: str, timeout: int = 60):
    """调用终端自己的 /run（逐行追踪的教学运行器），拿 kind / stdout_final。"""
    body = json.dumps({"code": code, "stdin": stdin}).encode("utf-8")
    req = urllib.request.Request(endpoint.rstrip("/") + "/run", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("kind"), data.get("stdout_final") or ""


def verify(problem: dict, endpoint: str) -> dict:
    """把一份 solution_code 真跑一遍：sample + 全部 extra_cases。"""
    code = problem.get("solution_code") or ""
    extras = problem.get("extra_cases") or []
    if not code.strip():
        return {"sample": "fail", "extra_passed": 0, "extra_total": len(extras)}
    try:
        kind, got = run_on_runner(endpoint, code, problem["sample_in"])
        sample_ok = kind == "ok" and out_matches(got, problem["sample_out"])
        passed = 0
        for case in extras:
            ckind, cgot = run_on_runner(endpoint, code, case["in"])
            if ckind == "ok" and out_matches(cgot, case["out"]):
                passed += 1
            else:
                sys.stderr.write("[warn] 第 %s 题 extra_case 没过：in=%r 期望=%r 实际=%r kind=%s\n"
                                 % (problem.get("no"), case["in"], case["out"], cgot, ckind))
        return {"sample": "pass" if sample_ok else "fail",
                "extra_passed": passed, "extra_total": len(extras)}
    except Exception as exc:  # noqa: BLE001  运行器没起来就别把整个抓取搞挂
        sys.stderr.write("[warn] 连不上运行器 %s（%r），第 %s 题的 verified 记不了。\n"
                         "       先起服务：python app\\main.py --no-window --port 8896\n"
                         % (endpoint, exc, problem.get("no")))
        return None


# ----------------------------------------------------------------- 组装

def build(set_slug: str, hw_id: str, title: str, base: str, fetched_at: str,
          runner: str = None) -> dict:
    set_url = "%s/%s/" % (base, set_slug.strip("/"))
    page = fetch(set_url)
    meta = parse_set(page, set_url)

    problems = []
    for item in meta["problems"]:
        detail = parse_problem(fetch(item["oj_url"]), item["oj_url"])
        authored = AUTHORED.get(item["no"])
        if authored is None:
            sys.stderr.write("[warn] 第 %d 题《%s》还没有手写解析（AUTHORED[%d]），"
                             "本次只抓题面。\n" % (item["no"], item["title"], item["no"]))
            authored = {}
        elif authored.get("title") and authored["title"] != item["title"]:
            sys.stderr.write("[warn] 第 %d 题的标题变了：AUTHORED 里是《%s》，页面上是《%s》，"
                             "请核对解析是否还适用。\n"
                             % (item["no"], authored["title"], item["title"]))
        problem = {
            "no": item["no"],
            "title": item["title"],
            "oj_url": item["oj_url"],
            "global_id": detail["global_id"],
            "limits": detail["limits"],
            "statement_md": detail["statement_md"],
            "sample_in": detail["sample_in"],
            "sample_out": detail["sample_out"],
            "extra_cases": authored.get("extra_cases", []),
            "analysis_md": authored.get("analysis_md", ""),
            "pitfalls": authored.get("pitfalls", []),
            "solution_code": authored.get("solution_code", ""),
            "points": authored.get("points", []),
            "stats": detail["stats"],
            "verified": None,
        }
        if runner:
            problem["verified"] = verify(problem, runner)
        problems.append(problem)

    return {
        "id": hw_id,
        "title": title,
        "oj_url": set_url,
        "fetched_at": fetched_at,
        "deadline": meta["deadline"],
        "problems": problems,
    }


def now_iso() -> str:
    return _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="抓 OpenJudge 题集，生成作业解析 JSON")
    ap.add_argument("--set", dest="set_slug", help="题集 slug，例如 2026ci13hw1")
    ap.add_argument("--out", help="输出 JSON 路径，例如 hw1.json")
    ap.add_argument("--id", dest="hw_id", default=None, help="作业 id，默认由 --out 推断（hw1.json → hw1）")
    ap.add_argument("--title", default=None, help="作业标题，例如 作业一")
    ap.add_argument("--base", default=DEFAULT_BASE, help="OJ 站点根，默认 %s" % DEFAULT_BASE)
    ap.add_argument("--fetched-at", default=None, help="抓取时间戳（ISO8601）；不给则沿用旧文件里的值")
    ap.add_argument("--verify-url", default=DEFAULT_RUNNER,
                    help="跑 solution_code 用的本地运行器地址，默认 %s" % DEFAULT_RUNNER)
    ap.add_argument("--no-verify", action="store_true",
                    help="不实测参考代码（verified 会写成 null）")
    ap.add_argument("--list-sets", action="store_true", help="只列出首页上看到的题集")
    ap.add_argument("--with-archive", action="store_true",
                    help="配合 --list-sets：连 /contests/past 归档页一起列（最多 5 页）")
    args = ap.parse_args(argv)

    if args.list_sets:
        items = list_sets(fetch(args.base + "/"), args.base)
        if args.with_archive:
            items += fetch_archive_sets(args.base)
        for s in items:
            print("%-8s %-24s %s  %s" % (s["kind"], s["when"] or "-", s["url"], s["title"]))
        print("（共 %d 个题集）" % len(items))
        return 0

    if not args.set_slug or not args.out:
        ap.error("需要 --set 和 --out（或者用 --list-sets）")

    out_path = os.path.abspath(args.out)
    hw_id = args.hw_id or os.path.splitext(os.path.basename(out_path))[0]
    title = args.title or hw_id

    fetched_at = args.fetched_at
    if not fetched_at and os.path.exists(out_path):
        try:
            with open(out_path, encoding="utf-8") as fh:
                fetched_at = json.load(fh).get("fetched_at")
        except Exception:  # noqa: BLE001  旧文件坏了就重新取时间
            fetched_at = None
    fetched_at = fetched_at or now_iso()

    data = build(args.set_slug, hw_id, title, args.base, fetched_at,
                 runner=None if args.no_verify else args.verify_url)

    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    print("已写出 %s" % out_path)
    print("  作业 %s《%s》  deadline=%s  fetched_at=%s" % (data["id"], data["title"],
                                                          data["deadline"], data["fetched_at"]))
    print("  共 %d 题，extra_cases %d 条" % (len(data["problems"]),
                                             sum(len(p["extra_cases"]) for p in data["problems"])))
    for p in data["problems"]:
        v = p["verified"]
        vtxt = ("未实测" if v is None else
                "sample=%s extra=%d/%d" % (v["sample"], v["extra_passed"], v["extra_total"]))
        print("  %d. %-22s 题面 %5d 字  extra %d 条  解析 %4d 字  坑 %d 条  %s  points %s"
              % (p["no"], p["title"], len(p["statement_md"]), len(p["extra_cases"]),
                 len(p["analysis_md"]), len(p["pitfalls"]), vtxt,
                 ",".join(p["points"]) or "-"))
    bad = [p["no"] for p in data["problems"]
           if p["verified"] and (p["verified"]["sample"] != "pass"
                                 or p["verified"]["extra_passed"] != p["verified"]["extra_total"])]
    if bad:
        print("  !! 有参考代码没跑过：题 %s" % bad)
    print("  sha256(json) = %s" % digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
