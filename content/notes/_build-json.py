# -*- coding: utf-8 -*-
r"""Content pipeline generator for the course terminal.

Reads content/notes/chNN.md, mechanically splits it into sections (##) and
knowledge points (###, plus #### promoted out of oversized parents), derives
slide-page numbers from the <!-- SLIDE --> markers, and writes content/chNN.json.

Contract: SPEC.md section 3.1 / 4.  Field names are frozen.

环境变量（便携/打包运行用，全部不设时行为与本文件历史版本逐字节一致）:
    CT_ROOT       项目根目录，默认 D:\opencode\course-terminal
    CT_TOOLS      存放 node 工具链的目录（render-pdf.mjs + node_modules/
                  pdfjs-dist）；这个名字在 .mjs 里已经是既有约定
    CT_EXTRACTOR  auto(默认) | pdfium | node —— 选 PDF 引擎；pdfium/node 是
                  给自测用的强制开关，见“PDF 引擎”一节
    CT_TMP        临时目录（PDF 缓存 + 每页文本 dump），语义未改动

子命令：
    （裸跑）             按 registry 顺序重建全部章节的 chNN.json
    --rebuild-one chNN   单章端到端重建：detect -> 渲染 PNG -> 本地化图片 ->
                         只更新这一章的 registry 条目 -> 写 chNN.json。
                         输入必须已放好（content/notes/chNN.md + CT_TMP/chNN.pdf），
                         全程不联网；只写这一章的产物，不写 _point-ids.txt 漂移基线。
    --selftest-detect    只读自测；--detect 只读分析；--check 只读远端比对
    --add chNN           会联网抓取并刷新 _point-ids.txt 的完整流程
    --only chNN          把裸跑限定到某一章（不做 detect/渲染/registry 更新）

机器可读结论行，供桌面端解析——桌面端是用
importlib.util.spec_from_file_location 装载本模块后直接调 main() 的：
    REBUILD-OK <chapter> slides=<n> points=<n>
    REBUILD-FAIL <chapter> <reason>
--rebuild-one 会把它作为整轮 stdout 的最后一行；裸跑则按章节顺序在末尾各来一行。
有任一章失败则退出码 1。
"""
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import time
import unicodedata
import zlib

sys.stdout.reconfigure(encoding='utf-8')
# stdout 早已是 UTF-8，但 stderr 仍是本地代码页（本机 cp936），于是同一条管道里
# 两种编码混在一起，桌面端按 UTF-8 解析 stderr 会炸。这里把它对齐，顺手把
# pythonw 下 stderr 为 None 的情况挡掉（不改动上面那行的既有行为）。
if sys.stderr is not None:
    sys.stderr.reconfigure(encoding='utf-8')

# ---------------------------------------------------------------------------
# 路径。全部可被环境变量重定向，这样打包成便携版之后同一份脚本仍能跑起来；
# 一个都不设时，取值与写死的常量完全相同。
# ---------------------------------------------------------------------------
ROOT = os.environ.get('CT_ROOT') or r'D:\opencode\course-terminal'
CONTENT = os.path.join(ROOT, 'content')
NOTES = os.path.join(CONTENT, 'notes')
IMAGES = os.path.join(CONTENT, 'images')
SLIDES = os.path.join(CONTENT, 'slides')
REGISTRY_FILE = os.path.join(NOTES, '_chapters.json')
ID_LIST_FILE = os.path.join(NOTES, '_point-ids.txt')
EXTRACTOR = os.path.join(NOTES, '_extract-pdf-text.mjs')
TOOLS_DIR = os.environ.get('CT_TOOLS') or r'D:\opencode\course\_tools'
RENDERER = os.path.join(TOOLS_DIR, 'render-pdf.mjs')

BASE_URL = os.environ.get('CT_BASE_URL', 'https://csintro2026.zhengmao.ltd')
DEFAULT_FETCHED_AT = '2026-09-26T11:53:43+08:00'

# ---------------------------------------------------------------------------
# Chapter registry.  `--add chNN` GENERATES the entry (sha256 / page count /
# non_content_pages are computed, never hand-copied), so a weekly update is one
# command instead of an archaeology session.
# ---------------------------------------------------------------------------
CHAPTER_ORDER = []
CHAPTERS = {}


def load_registry():
    global CHAPTER_ORDER, CHAPTERS
    with open(REGISTRY_FILE, encoding='utf-8') as f:
        reg = json.load(f)
    CHAPTER_ORDER = list(reg['order'])
    CHAPTERS = reg['chapters']
    return reg


def save_registry(order, chapters):
    global CHAPTER_ORDER, CHAPTERS
    with open(REGISTRY_FILE, encoding='utf-8') as f:
        reg = json.load(f)
    reg['order'] = list(order)
    reg['chapters'] = chapters
    tmp = REGISTRY_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(reg, f, ensure_ascii=False, indent=1)
        f.write('\n')
    os.replace(tmp, REGISTRY_FILE)
    CHAPTER_ORDER, CHAPTERS = list(order), chapters


load_registry()

FETCHED_AT = DEFAULT_FETCHED_AT      # kept for the seed / fallback only

# ---------------------------------------------------------------------------
# refs: link each knowledge point to the localised Python-100-Days files.
#
# Source data is content/100days/index.json (produced by the 100Days agent):
#   topic_index : { "<topic>": [day, ...] }   (287 topics)
#   days        : [ {day, title, file, bytes, topics} ]
#
# Shape follows SPEC.md 3.1: {kind, label, url}.  web/index.html refsHtml()
# builds a chip from kind/label/url, and openDaysRef() recovers the Day number
# by running /Day\s*0*(\d+)/i over url+label.  So:
#   kind  = "100days"                  -> selects the 📖 chip branch
#   label = "Day11 字符串"              -> the chip text
#   url   = "100days/Day11-字符串.md"   -> resolveContentPath -> content/100days/...
#   day   = 11                         -> NOT read by the UI today; included
#                                         because it is free, exact metadata.
#
# MATCHING CALIBER -- no substring / no fuzzy matching, ever.  Every rule
# requires a whole string to EQUAL a topic key.
#   exact    : canonical whole-title equality only (+ 例题：-style prefix strip)
#   generous : + trailing-parenthetical / whole-segment-split (each segment must
#              EQUAL a key) / 例题N:==例题: / Head+LatinTail
# SHIPPED DEFAULT IS generous + title + cap 5 (option C) -- see below.
# `--refs-report` prints both calibers and enforces the <5 / >60 floor.
# ---------------------------------------------------------------------------
IDX_100DAYS = os.path.join(CONTENT, '100days', 'index.json')
# DEFAULTS ARE THE SHIPPING CHOICE (option C), so a bare `_build-json.py` run
# reproduces it; the env vars only exist to override for experiments.
#   generous : mechanical normalisation only -- every rule still requires a
#              WHOLE string to equal a topic key (never substring / fuzzy)
#   title    : topic_index tags a topic to every day that MENTIONS it, which is
#              why 函数 used to pull in Day05 分支结构.  Keep only days whose own
#              title contains a matched key; if that empties the list, keep the
#              full list rather than losing the ref.
#   max=5    : chip cap.  DISPLAY ONLY -- it can never create a match, only drop
#              the highest-numbered surplus days.
REFS_CALIBER = os.environ.get('CT_REFS_CALIBER', 'generous')   # generous | exact
REFS_DAYS = os.environ.get('CT_REFS_DAYS', 'title')            # title | all
REFS_MAX = int(os.environ.get('CT_REFS_MAX', '5'))             # 0 = no cap

REFS_PREFIX_RE = re.compile(
    r'^(例题|例|练习|习题|思考|作业|扩展|拓展|案例)\s*[:：]\s*')
_REF_CACHE = {}


def _ref_key(s):
    """Canonical comparison form: NFKC + drop 例题：-style prefix + collapse
    whitespace + unify full/half-width punctuation."""
    s = unicodedata.normalize('NFKC', s)
    s = REFS_PREFIX_RE.sub('', s).strip()
    s = re.sub(r'\s+', '', s)
    return s.replace('：', ':').replace('（', '(').replace('）', ')')


def load_100days_index():
    if _REF_CACHE:
        return _REF_CACHE
    topic_days, days = {}, {}
    try:
        with open(IDX_100DAYS, encoding='utf-8') as f:
            idx = json.load(f)
    except Exception as e:
        print(f'   (refs: 100days/index.json unavailable: {e})')
        _REF_CACHE.update({'topic_days': {}, 'days': {}, 'keys': []})
        return _REF_CACHE
    days = {int(d['day']): d for d in (idx.get('days') or [])}
    for k, v in (idx.get('topic_index') or {}).items():
        ck = _ref_key(k)
        if ck:
            topic_days.setdefault(ck, set()).update(int(x) for x in v)
    _REF_CACHE.update({'topic_days': topic_days, 'days': days,
                       'keys': sorted(topic_days)})
    return _REF_CACHE


def _ref_entry(day):
    d = load_100days_index()['days'].get(int(day))
    if not d:
        return None
    short = re.sub(r'\.md$', '', re.sub(r'^Day\d+[-_]?', '', d.get('file', '')))
    return {
        'kind': '100days',
        'day': int(day),
        'label': 'Day%02d %s' % (int(day), short or d.get('title', '')),
        'url': '100days/' + d['file'],
    }


def _ref_keys_exact(title):
    k = _ref_key(title)
    return [k] if k and k in load_100days_index()['topic_days'] else []


def _ref_keys_generous(title):
    """exact, then a chain of EXACT-equality canonicalisations (never substring)."""
    idx = load_100days_index()
    keys = _ref_keys_exact(title)
    if keys:
        return keys
    k = _ref_key(title)
    if not k:
        return []
    # (a) drop one trailing parenthetical: 集成开发环境（IDE） -> 集成开发环境
    k2 = re.sub(r'\([^)]*\)$', '', k)
    if k2 != k and k2 in idx['topic_days']:
        return [k2]
    # (b) the heading names several topics: 数值类型：整数和浮点数 -> 整数, 浮点数
    segs = [x for x in re.split(r'[、,，/·:;；]|和|与|及', k) if len(x) >= 2]
    good = [x for x in segs if x in idx['topic_days']]
    if good:
        return good
    # (c) 例题N： and 例题： mean the same thing
    k3 = re.sub(r'^(例题|例子)\d*', '例题', k)
    same = [x for x in idx['keys']
            if re.sub(r'^(例题|例子)\d*', '例题', x) == k3]
    if same:
        return same
    # (d) "Head LatinTail": 字符串 str -> 字符串 (+ str)
    m = re.match(r'^(.+?)([A-Za-z][A-Za-z0-9_]*)$', k)
    if m and m.group(1) in idx['topic_days']:
        out = [m.group(1)]
        if m.group(2) in idx['topic_days']:
            out.append(m.group(2))
        return out
    return []


def _ref_days(title):
    """Sorted day numbers matched by a point title (BEFORE the chip cap)."""
    keys = (_ref_keys_generous(title) if REFS_CALIBER == 'generous'
            else _ref_keys_exact(title))
    if not keys:
        return [], []
    idx = load_100days_index()
    days = set()
    for k in keys:
        days.update(idx['topic_days'].get(k, ()))
    if REFS_DAYS == 'title' and days:
        titled = {d for d in days
                  if any(k and k in idx['days'][d].get('title', '') for k in keys)}
        if titled:
            days = titled
    return sorted(days), keys


def build_refs(title):
    """100days refs for one point title; empty list when nothing matches.

    The cap is applied AFTER matching, so it only ever shortens the visible chip
    row -- it cannot manufacture a match or change which keys matched.
    """
    days, _keys = _ref_days(title)
    if REFS_MAX > 0:
        days = days[:REFS_MAX]
    out = []
    for d in days:
        e = _ref_entry(d)
        if e:
            out.append(e)
    return out


def refs_report(sample=8):
    """--refs-report: measure the matching calibers, print samples, and apply
    the caller's floor check (hits < 5 or > 60 means the caliber is wrong)."""
    idx = load_100days_index()
    print('100days index: %d topic keys, %d days, caliber=%s'
          % (len(idx['topic_days']), len(idx['days']), REFS_CALIBER))
    rows = []
    for ch in CHAPTER_ORDER:
        doc, _ = build(ch)
        for s in doc['sections']:
            for p in s['points']:
                t = p['title']
                ex = _ref_keys_exact(t)
                ge = ex if ex else _ref_keys_generous(t)
                rows.append((ch, p['id'], t, ex, ge))
    n_ex = sum(1 for r in rows if r[3])
    n_ge = sum(1 for r in rows if r[4])
    e_ex = sum(len(set(sum((sorted(idx['topic_days'][k]) for k in r[3]), [])))
               for r in rows if r[3])
    e_ge = sum(len(set(sum((sorted(idx['topic_days'][k]) for k in r[4]), [])))
               for r in rows if r[4])
    print()
    print('  points total            : %d' % len(rows))
    print('  exact caliber           : %d points get refs, %d ref entries' % (n_ex, e_ex))
    print('  generous caliber        : %d points get refs, %d ref entries' % (n_ge, e_ge))
    print()
    print('=== EXACT caliber hits (title -> matched topic key -> days) ===')
    for ch, pid, t, ex, ge in rows:
        if not ex:
            continue
        ds = sorted(set(sum((sorted(idx['topic_days'][k]) for k in ex), [])))
        print('  %-14s %-28s -> %-16s -> %s' % (
            pid, t, ','.join(ex), ['Day%02d %s' % (d, idx['days'][d]['title'])
                                   for d in ds]))
    print()
    print('=== GENEROUS-only extras (the shipped caliber also takes these) ===')
    for ch, pid, t, ex, ge in rows:
        if ex or not ge:
            continue
        ds = sorted(set(sum((sorted(idx['topic_days'][k]) for k in ge), [])))
        print('  %-14s %-28s -> %-16s -> %s' % (
            pid, t, ','.join(ge), ['Day%02d %s' % (d, idx['days'][d]['title'])
                                   for d in ds]))
    print()
    applied = n_ge if REFS_CALIBER == 'generous' else n_ex
    a_pts = sum(1 for r in rows if build_refs(r[2]))
    a_ent = sum(len(build_refs(r[2])) for r in rows)
    # uncapped, to prove the cap only shortens the visible row
    u_ent = sum(len(_ref_days(r[2])[0]) for r in rows)
    u_max = max((len(_ref_days(r[2])[0]) for r in rows), default=0)
    a_max = max((len(build_refs(r[2])) for r in rows), default=0)
    print('  APPLIED caliber=%s days=%s cap=%s : %d points, %d ref entries'
          % (REFS_CALIBER, REFS_DAYS, REFS_MAX or 'off', a_pts, a_ent))
    print('  cap effect: uncapped %d entries (max %d/card) -> applied %d '
          'entries (max %d/card), %d dropped by the cap'
          % (u_ent, u_max, a_ent, a_max, u_ent - a_ent))
    if applied < 5:
        print('  *** FLOOR CHECK FAILED: %d < 5 ***' % applied)
        print('  The authorized caliber (exact whole-title equality) cannot reach')
        print('  the expected range.  See the GENEROUS extras above and decide.')
        return 2
    if applied > 60:
        print('  *** CEILING CHECK FAILED: %d > 60 ***' % applied)
        print('  The caliber is too loose -- it is matching unrelated topics.')
        return 2
    print('  floor check OK (5 <= %d <= 60)' % applied)
    return 0



MAX_BODY_LINES = 120          # SPEC rule 4.4

MARKER_RE = re.compile(r'^\s*<!--\s*SLIDE\s*-->\s*$')
H_RE = re.compile(r'^(#{1,6})\s+(.*?)\s*#*\s*$')
# A fence delimiter must be a clean run of one fence character; an info string
# may not itself contain fence characters.  This matters: ch03 line 521 is a
# Traceback caret line "    ~~~~~~~~~^~~~~" which a naive regex reads as a
# fence, leaving the fence stuck open for the rest of the file.
FENCE_OPEN_RE = re.compile(r'^(\s*)(`{3,}|~{3,})\s*([^`~]*)$')
FENCE_CLOSE_RE = re.compile(r'^(\s*)(`{3,}|~{3,})\s*$')

# Pitfall rule v2 (parent directive): the notes never use '>' blockquotes for
# pitfalls -- they live in LIST ITEMS.  A list item is a pitfall if it carries
# a warning keyword, or if it opens with bold reminder text.  Headings and
# ordinary prose are excluded; a bare category label with no substance is
# dropped (better null than noise).
PITFALL_WORDS = ('注意', '常见错误', '万人坑', '坑', '易错', '警告', '陷阱',
                 '误区', '错误')

# A warning keyword must sit in a WARNING POSITION, not merely occur somewhere.
# "含 错误 即可" would flag neutral exposition such as
#   "- 代码补全、语法高亮、错误提示，写程序更快"
#   "- 最后一行：错误的类型和原因，先看这一行"
#   "- 程序运行中可能出现各种错误"
# so an item qualifies only when the keyword leads its label, leads bold text,
# or states a consequence ("…导致答案错误").
# A bare 错误 is deliberately NOT a leading keyword: "错误的类型和原因" would match.
PITFALL_START_RE = re.compile(
    r'^\s*(?:[-*+]|\d+[.)])?\s*(?:\*\*)?\s*'
    r'(注意|提醒|警告|误区|陷阱|坑|易错|常见错误|万人坑)')
PITFALL_CONSQ_RE = re.compile(r'(导致|造成|引起).{0,4}错误')
BOLD_LEAD_RE = re.compile(r'^\s*\*\*([^*]+)\*\*\s*[：:]')
BOLD_REMIND_RE = re.compile(r'^(注意|提醒|警告|误区|陷阱|坑|易错|常见错误|万人坑)')
LIST_ITEM_RE = re.compile(r'^(\s*)(?:[-*+]|\d+[.)])\s+(.*)$')

PITFALL_MIN_CHARS = 6

# The only remaining exception.  A review question can read like a warning
# ("下面哪种写法最可能导致'答案错误'？") but it is a quiz, not a pitfall.
PITFALL_BLOCKLIST = [
    (re.compile(r'[?？]\s*$'), 'quiz question, not a trap'),
]

# ---------------------------------------------------------------------------
# run: hand-picked, only where a 1-3 line snippet genuinely shows the point.
# Keyed by (chapter, normalised point title) so it survives renumbering.
# ---------------------------------------------------------------------------
RUN = {
    ('ch02', '作为计算器的Python Shell'): "print(2 ** 100)\nprint(12 * 34.5 + 23.4)",
    ('ch02', '进制转换：Python内建方法'): "print(bin(37), oct(37), hex(37))\nprint(int('100101', 2), int('0o45', 8), int('0x25', 16))",
    ('ch02', '算术运算'): "print(7 / 2, 7 // 2, -7 // 2, -7 % 3)",
    ('ch02', '二进制逻辑运算'): "print(0b1100 & 0b1010, 0b1100 | 0b1010, 0b1100 ^ 0b1010)",
    ('ch02', '二进制的移位运算'): "print(1 << 4, 255 >> 2)\nprint(bin(1 << 4))",

    ('ch03', '变量：数据对象的标签'): "height = 8848\neverest = height\nprint(height, everest, height is everest)",
    ('ch03', '动态类型'): "x = 0\nprint(type(x))\nx = True\nprint(type(x))\nx = 'hello'\nprint(type(x))",
    ('ch03', '赋值语句的小技巧'): "a, b = 1, 2\na, b = b, a\nprint(a, b)",
    ('ch03', '数值类型：整数和浮点数'): "print(7 / 2, 7 // 2, -7 // 2, -7 % 3)\nprint(0.1 + 0.2)",
    ('ch03', '复数和逻辑值'): "print((1 + 2j) * (3 - 1j), abs(3 + 4j))\nprint(bool(0), bool(''), bool([]))",
    ('ch03', '比较与逻辑运算'): "print(3 != 4, 3 >= 4, 'abc' < 'abd')\nprint(0 < 5 < 10, 0 or 'x', 1 and 2)",
    ('ch03', '字符串 str'): "s = 'Hello Tom'\nprint(s[0], s[-1], len(s))\nprint(s[1:4], s[::2], s[::-1])",
    ('ch03', '字符串的常用方法'): "print('a,b,,c'.split(','))\nprint('-'.join(['2026', '09', '22']))\nprint('Hello Tom'.upper(), 'Hello Tom'.swapcase())",
    ('ch03', 'input 和 print'): "print('a', 'b', sep='-', end='!\\n')\nprint(f'{3.14159:.2f}')",
    ('ch03', '读入一行中的多个数'): "nums = list(map(int, '3 5 7'.split()))\nprint(nums, sum(nums))",
    ('ch03', '输入输出的细节'): "print(repr('  hello  '.strip()))\nx = 3.0\nprint(f'{x:.2f}', round(x, 2))",
    ('ch03', '列表和元组'): "atup = (1, True, 0.234)\nprint(atup[0], len(atup))",
    ('ch03', '列表和元组的共同操作'): "alist = [1, True, 0.234]\nalist[0] = 2\nprint(alist, alist[::-1])",
    ('ch03', '列表的其他方法'): "lst = [3, 1, 2]\nlst.append(5)\nlst.sort()\nprint(lst, lst.count(3), lst.index(5))",
    ('ch03', '为什么需要元组？'): "def minmax(a, b):\n    return (a, b) if a < b else (b, a)\nprint(minmax(7, 3))",
    ('ch03', '可变对象的引用'): "alist = [1, 2, 3]\nblist = alist\nblist[0] = 'abc'\nprint(alist, alist is blist)",
    ('ch03', '可变对象：副本与陷阱'): "alist = [1, 2, 3]\nclist = alist[:]\nclist[0] = 99\nprint(alist, clist)",
    ('ch03', 'range：连续整数序列'): "print(list(range(5)), list(range(2, 6)))\nprint(list(range(10, 0, -2)))",
    ('ch03', '集合 set'): "x, y = {1, 2, 3, 4}, {3, 4, 5}\nprint(x | y, x & y, x - y, x ^ y)",
    ('ch03', '字典 dict'): "age = {'Tom': 25}\nage['Ann'] = 20\nprint(age, 'Tom' in age)",
    ('ch03', '表达式、调用与赋值'): "print(len('python'), max(3, 7))\nf = len\nprint(f('abc'))",
    ('ch03', '条件分支：if 语句'): "x = 7\nif x % 2 == 0:\n    print('even')\nelse:\n    print('odd')",
    ('ch03', '条件循环：while 语句'): "n, total = 1, 0\nwhile n <= 100:\n    total += n\n    n += 1\nprint(total)",
    ('ch03', '迭代循环：for 语句'): "total = 0\nfor x in [2, 3, 15, 17]:\n    total = total + x\nprint(total)",
    ('ch03', 'break 和 continue'): "for i in range(10):\n    if i % 3 == 0:\n        continue\n    if i == 8:\n        break\n    print(i, end=' ')",
    ('ch03', '推导式'): "print([i * i for i in range(6) if i % 2 == 0])\nprint({k: len(k) for k in ['a', 'bb']})",
    ('ch03', '括号的用法'): "print(type(()), type((1)), type((1,)))\nprint([1, 2, 'sina'], {'Tom': 25}, {'Tom', 'Bob'})",
    ('ch03', '异常处理'): "try:\n    x = int('abc')\nexcept ValueError as e:\n    print('ValueError:', e)",
    ('ch03', '函数'): "def add(a, b=1):\n    return a + b\nprint(add(3), add(3, 5))",
    ('ch03', '注意括号！'): "def f():\n    print('called')\nprint(f)\nprint(f())",
    ('ch03', '参数的定义与传递'): "def func(a, b=2, *args):\n    return a, b, args\nprint(func(1), func(1, 3, 4, 5))",
    ('ch03', '类：定义与使用'): "class Point:\n    def __init__(self, x):\n        self.x = x\n\nprint(Point(3).x)",
    ('ch03', '例：力的合成'): "class Force:\n    def __init__(self, fx, fy):\n        self.fx, self.fy = fx, fy\n\n    def show(self):\n        return f'({self.fx}, {self.fy})'\n\nprint(Force(3, 4).show())",
}


def norm_title(t):
    """Strip numbering / decoration from a heading so `title` is the bare name."""
    t = t.strip()
    t = re.sub(r'\*\*([^*]*)\*\*', r'\1', t)
    t = re.sub(r'`([^`]*)`', r'\1', t)
    t = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', t)
    t = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', t)
    t = re.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'^第\s*[0-9一二三四五六七八九十百]+\s*[章节讲部分]\s*[\.、:：]?\s*', '', t)
    t = re.sub(r'^\d+(\.\d+)*\s*[\.、:：)）]\s*', '', t)
    t = re.sub(r'^\d+(\.\d+)+\s+', '', t)
    t = re.sub(r'^[\(（]\d+[\)）]\s*', '', t)
    t = re.sub(r'^[一二三四五六七八九十]+\s*[、\.]\s*', '', t)
    t = re.sub(r'^\s*Ch\s*\d+\s*[\.、:：]\s*', '', t, flags=re.I)
    return t.strip()


def scan(lines):
    """Classify every line: fences, headings (level, title), SLIDE markers."""
    info = []
    fence_char = None
    fence_len = 0
    for i, l in enumerate(lines):
        if fence_char is None:
            m = FENCE_OPEN_RE.match(l)
            if m:
                fence_char = m.group(2)[0]
                fence_len = len(m.group(2))
                info.append({'i': i, 'kind': 'fence_open'})
                continue
        else:
            m = FENCE_CLOSE_RE.match(l)
            if m and m.group(2)[0] == fence_char and len(m.group(2)) >= fence_len:
                fence_char = None
                fence_len = 0
                info.append({'i': i, 'kind': 'fence_close'})
                continue
            info.append({'i': i, 'kind': 'code'})
            continue
        if MARKER_RE.match(l):
            info.append({'i': i, 'kind': 'marker'})
            continue
        h = H_RE.match(l)
        if h:
            info.append({'i': i, 'kind': 'h', 'level': len(h.group(1)),
                         'title': h.group(2).strip()})
            continue
        info.append({'i': i, 'kind': 'text'})
    if fence_char is not None:
        raise RuntimeError('unbalanced code fence')
    return info


# ---------------------------------------------------------------------------
# Unsupported-tag removal.  The UI markdown renderer whitelists only
# img / details / summary / mark / figure / figcaption, so a raw <iframe> or
# <svg> would be escaped and show up as visible tag soup.  Replace them with a
# short Chinese note.  NEVER touches code fences (ch03 line 469 contains a real
# "#include <stdio.h>", and ch02's only <svg> is an SVG *source sample* inside a
# ```xml fence -- that is teaching material, not a tag to strip).
# ---------------------------------------------------------------------------
IFRAME_RE = re.compile(r'<iframe\b.*?</iframe\s*>|<iframe\b[^>]*/?>', re.S | re.I)
SVG_RE = re.compile(r'<svg\b.*?</svg\s*>', re.S | re.I)
IFRAME_NOTE = '（原讲义此处嵌入了一个 YouTube 视频，国内无法访问）'
SVG_NOTE = '（原讲义此处有一张 SVG 示意图，当前渲染器不支持）'
NOTE_RE = re.compile(re.escape(IFRAME_NOTE) + '|' + re.escape(SVG_NOTE))


def _segments(text):
    """Split text into (chunk, is_code) pieces.  Multi-line <iframe> tags span
    5 lines in ch01, so the regex must run on whole outside-fence segments --
    a per-line pass silently misses 3 of the 4 iframes."""
    segs, buf, fence = [], [], None
    for line in text.split('\n'):
        if fence is None:
            m = FENCE_OPEN_RE.match(line)
            if m:
                if buf:
                    segs.append(('\n'.join(buf), False))
                    buf = []
                fence = m.group(2)[0]
                segs.append((line, True))
                continue
        else:
            segs.append((line, True))
            m = FENCE_CLOSE_RE.match(line)
            if m and m.group(2)[0] == fence:
                fence = None
            continue
        buf.append(line)
    if buf:
        segs.append(('\n'.join(buf), False))
    return segs


def strip_unsupported_tags(text, stats=None):
    """Replace <iframe>/<svg> OUTSIDE code fences with a short Chinese note."""
    out = []
    for chunk, is_code in _segments(text):
        if is_code:
            out.append(chunk)
            continue
        n_i = len(IFRAME_RE.findall(chunk))
        n_s = len(SVG_RE.findall(chunk))
        if n_i or n_s:
            if stats is not None:
                stats['iframe'] = stats.get('iframe', 0) + n_i
                stats['svg'] = stats.get('svg', 0) + n_s
            chunk = IFRAME_RE.sub(IFRAME_NOTE, chunk)
            chunk = SVG_RE.sub(SVG_NOTE, chunk)
        out.append(chunk)
    return '\n'.join(out)


def neighbour_note(text):
    """Inverse view: drop the notes we inserted, so the rest can be compared."""
    return NOTE_RE.sub('', text)


def count_tags_outside_fences(text):
    """Residual <iframe>/<svg> counts, ignoring code fences."""
    res = {'iframe': 0, 'svg': 0}
    for chunk, is_code in _segments(text):
        if is_code:
            continue
        res['iframe'] += len(IFRAME_RE.findall(chunk))
        res['svg'] += len(SVG_RE.findall(chunk))
    return res


def md_to_plain(s):
    """Strip markdown decoration, keeping the words."""
    s = re.sub(r'\*\*([^*]*)\*\*', r'\1', s)
    s = re.sub(r'`([^`]*)`', r'\1', s)
    s = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', s)
    s = re.sub(r'<mark>(.*?)</mark>', r'\1', s, flags=re.S | re.I)
    s = re.sub(r'\$([^$]*)\$', r'\1', s)
    s = re.sub(r'^\s*>\s?', '', s)
    return s.strip()


def find_pitfall(lines, a, b):
    """Pitfall rule v2: warning keywords / bold reminders inside LIST ITEMS.

    Returns (text, [source line numbers]) or (None, []).

    Two things matter here, both learned the hard way:
      * qualification uses the item's OWN label -- a child that merely mentions
        错误 must not promote its parent (that wrongly flagged "- 什么是 IDE").
      * the subtree must survive blank lines and indented code fences, because
        "- 常见错误" continues through two code samples before its remaining
        children (IndentationError / NameError / TypeError / ValueError).
    """
    stats = {}
    suppressed = set()
    i = a - 1
    while i < b:
        m = LIST_ITEM_RE.match(lines[i])
        if not m:
            i += 1
            continue
        indent = len(m.group(1).expandtabs(4))
        body = m.group(2)

        # ---- walk the item's markdown subtree --------------------------------
        j = i + 1
        desc, code, last = [], [], i + 1
        while j < b:
            line = lines[j]
            fm = FENCE_OPEN_RE.match(line)
            if fm:
                fc, fl = fm.group(2)[0], len(fm.group(2))
                k = j + 1
                block = []
                while k < b:
                    cm = FENCE_CLOSE_RE.match(lines[k])
                    if cm and cm.group(2)[0] == fc and len(cm.group(2)) >= fl:
                        break
                    block.append(lines[k].rstrip())
                    k += 1
                code.extend(x for x in block if x.strip())
                j = min(k + 1, b)
                last = j
                continue
            nxt = LIST_ITEM_RE.match(line)
            if nxt:
                nind = len(nxt.group(1).expandtabs(4))
                if nind <= indent:
                    break
                desc.append(line)
                j += 1
                last = j
                continue
            s = line.strip()
            if s == '' or s.startswith('<!-- SLIDE'):
                j += 1
                continue
            if re.match(r'^#{1,6}\s', s):
                break
            if len(line) - len(line.lstrip()) > indent:
                desc.append(line)
                j += 1
                last = j
                continue
            break        # unindented non-list block ends the subtree

        # ---- qualify on the item's OWN label --------------------------------
        plain = md_to_plain(body)
        bm = BOLD_LEAD_RE.match(body)
        kw = bool(PITFALL_START_RE.match(body)) or bool(PITFALL_CONSQ_RE.search(plain))
        bold = bool(bm and BOLD_REMIND_RE.match(bm.group(1).strip()))
        blocked = next((why for rx, why in PITFALL_BLOCKLIST
                        if rx.search(plain)), None)
        if blocked:
            # a non-pitfall parent means its subtree is context too
            suppressed.update(range(i + 2, last + 1))
            i += 1
            continue
        if not (kw or bold):
            i += 1               # do NOT skip the subtree: children may qualify
            continue
        if any(x in suppressed for x in range(i + 1, last + 1)):
            i += 1
            continue
        suppressed.update(range(i + 2, last + 1))

        # ---- build the plain-text pitfall ------------------------------------
        texts = []
        label = md_to_plain(body)
        if label:
            texts.append(label)
        for d in desc:
            dm = LIST_ITEM_RE.match(d)
            if dm:
                t = md_to_plain(dm.group(2))
                if t:
                    texts.append('  - ' + t)
            else:
                t = md_to_plain(d)
                if t:
                    texts.append(t)
        # a code sample is the item's content only when it has no child items
        if not desc and code:
            texts.extend(code)
        text = '\n'.join(texts).strip()
        substantive = any(
            len(re.sub(r'[\s：:、。，,\.\-—]+', '', t)) >= PITFALL_MIN_CHARS
            for t in texts)
        if text and substantive:
            stats[i + 1] = text
        i += 1
    if not stats:
        return None, []
    order = sorted(stats)
    return '\n'.join(stats[k] for k in order), order


# ---------------------------------------------------------------------------
# Image path rewrite: the notes reference images as ../images/x (relative to
# the /notes/ directory), which cannot resolve inside the app.  body_md is
# rendered from the app root, so rewrite to content/images/x.  ONLY the value
# of a `src` attribute changes -- alt/width/height/text stay byte-identical,
# and the rewrite is reversible (unrewrite_img_src) so the self-test can prove
# that nothing else was touched.
# ---------------------------------------------------------------------------
IMG_SRC_RE = re.compile(r'(src\s*=\s*")((?:\.\./)+images/[^"]*)(")')
IMG_SRC_BACK_RE = re.compile(r'(src\s*=\s*")(content/images/[^"]*)(")')


def rewrite_img_src(text):
    return IMG_SRC_RE.sub(
        lambda m: m.group(1) + 'content/images/' + m.group(2).split('/')[-1] + m.group(3),
        text)


def unrewrite_img_src(text):
    """Inverse of rewrite_img_src, used to prove nothing else was touched."""
    return IMG_SRC_BACK_RE.sub(
        lambda m: m.group(1) + '../images/' + m.group(2).split('/')[-1] + m.group(3),
        text)


# ===========================================================================
# Automatic derivation of `non_content_pages`  (cover + agenda/TOC pages)
#
# Why this is code and not a hand-written list: get it wrong by ONE page and
# every knowledge point in the chapter points at the wrong slide, silently.
# The three checks below all have to agree before a value is accepted:
#   (1) agenda pages        -- pages whose text repeats the chapter agenda
#   (2) |content pages| == M or M+1, where M = number of <!-- SLIDE --> markers
#   (3) marker/page anchor  -- for every content page C[k], its best verbatim
#                              match in the notes must sit AFTER marker #k and
#                              the previous page's match must sit BEFORE it.
#       This is what catches an off-by-one page shift.
# ===========================================================================
AGENDA_MARK = '本章内容'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')


# ---------------------------------------------------------------------------
# PDF 引擎。优先用 pypdfium2（进程内、不需要 node、不需要 node_modules），
# 项目自带的 node 抽取器保留为兜底。CT_EXTRACTOR 决定选谁：
#   auto（默认）—— 先试 pypdfium2，import 失败或抽取报错则退回 node
#   pdfium      —— 强制 pypdfium2，拿不到就大声失败（自测开关）
#   node        —— 强制走 node 子进程（自测开关 / 旧行为）
# pypdfium2 是惰性 import 的：模块导入期的副作用仍然只有 load_registry()。
# ---------------------------------------------------------------------------
_PDFIUM_UNSET = object()
_PDFIUM_CACHE = _PDFIUM_UNSET
CT_EXTRACTOR = (os.environ.get('CT_EXTRACTOR') or 'auto').strip().lower()


def pdfium_module():
    """返回 pypdfium2 模块；进程内引擎不可用时返回 None。"""
    global _PDFIUM_CACHE
    if _PDFIUM_CACHE is _PDFIUM_UNSET:
        mod = None
        if CT_EXTRACTOR != 'node':
            try:
                import pypdfium2 as mod  # noqa: F401
            except Exception as e:
                # ImportError 是常态（没装），但 DLL 缺失等也会在这里炸；
                # 两种情况在 auto 下都应当安静地退回 node。
                if CT_EXTRACTOR == 'pdfium':
                    raise RuntimeError(
                        'CT_EXTRACTOR=pdfium 但 pypdfium2 无法 import: %s' % e)
                mod = None
                print('   pypdfium2 不可用 (%s)，改用 node 抽取器' % e)
        _PDFIUM_CACHE = mod
    return _PDFIUM_CACHE


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    with open(p, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def fetch_url(url, tries=3, timeout=180):
    """Fetch with retries.  Returns (status, content_type, bytes)."""
    import urllib.request
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA,
                                                       'Accept': '*/*'})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.headers.get('Content-Type', ''), r.read()
        except Exception as e:
            last = e
            print(f'      retry {i + 1}/{tries}: {e}', flush=True)
            time.sleep(2 * (i + 1))
    raise RuntimeError(f'FAILED after {tries} tries: {url}: {last}')


def pdf_norm(s):
    """Normalise text so that PDF-extracted text can be compared with notes.

    ★ NFKC IS NOT OPTIONAL HERE.  The deck PDFs map CJK glyphs onto the KANGXI
      RADICAL block: the PDF says U+2F64 '⽤' where the notes say U+7528 '用',
      and U+2F00 '⼀' for U+4E00 '一'.  Without NFKC every verbatim match
      silently fails, the anchor check finds nothing, and the detector appears
      to "work" while proving nothing.  This was the original trap.
    """
    s = unicodedata.normalize('NFKC', s)
    s = re.sub(r'<!--.*?-->', '', s, flags=re.S)
    s = re.sub(r'`([^`]*)`', r'\1', s)
    s = re.sub(r'\*\*([^*]*)\*\*', r'\1', s)
    s = re.sub(r'^\s{0,3}#{1,6}\s*', '', s, flags=re.M)
    s = re.sub(r'!\[[^\]]*\]\([^)]*\)', ' ', s)
    s = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', s)
    s = re.sub(r'[#*_>|`\-—–\.\,\;\:\(\)\[\]\{\}\!\?\"\'\/\\+=<>~@\$%\^&\s]', '', s)
    return s


def extract_node(pdf_path, out_json):
    """走 node 子进程：项目的 _extract-pdf-text.mjs（兜底路径，行为未变）。"""
    proc = subprocess.run(['node', EXTRACTOR, pdf_path, out_json, TOOLS_DIR],
                          capture_output=True, text=True, encoding='utf-8',
                          errors='replace')
    if proc.returncode != 0:
        raise RuntimeError('PDF text extraction failed:\n' + (proc.stderr or '')[-1200:])
    with open(out_json, encoding='utf-8') as f:
        return json.load(f)


def extract_pdfium(pdfium, pdf_path, out_json):
    """pypdfium2 版的 _extract-pdf-text.mjs，返回结构完全相同。

    node 工具遍历 pdf.js 的 text item，凡 hasEOL 就补一个 ' | '，最后把连续的
    空白压成一个空格。pdfium 交回来的就是同一份信息、而且已经是断好行的
    （FPDFText_GetText 给每一行末尾加了 '\\r\\n'），所以等价做法是：按换行切开、
    再用 ' | ' 拼回去、然后套用同一个 re.sub(r'\\s+', ' ', t).strip()。

    两个诚实的差异，都不会传到检测器：
      * 断行位置是 pdfium 自己定的，它甚至可能把一页判成"一行一个字"
        （ch02 P02 的议程页就是这样）。下游无所谓——所有消费者都会先过
        pdf_norm()，而 pdf_norm() 本来就会删掉 '|' 和全部空白。
      * chars 是 len(text)：Python 数码点，JS 数 UTF-16 码元，只有当页面出现
        BMP 外字符（emoji 之类）时两者才会不同。
    """
    doc = pdfium.PdfDocument(pdf_path)
    pages = []
    try:
        n = len(doc)
        for i in range(n):
            page = doc[i]
            tp = page.get_textpage()
            try:
                t = tp.get_text_range()
            finally:
                tp.close()
                page.close()
            t = t.replace('\r\n', '\n').replace('\r', '\n')
            t = ' | '.join(t.split('\n'))
            t = re.sub(r'\s+', ' ', t).strip()
            pages.append({'page': i + 1, 'chars': len(t), 'text': t})
    finally:
        doc.close()
    # 与 node 版一致：pdf 写绝对路径、缩进 1、ensure_ascii=False
    dump = {'pdf': os.path.abspath(pdf_path), 'numPages': n, 'pages': pages}
    with open(out_json, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(dump, f, ensure_ascii=False, indent=1)
    return dump


def run_extractor(pdf_path, out_json):
    """输出某一章 PDF 的逐页文本：{pdf, numPages, pages:[{page,chars,text}]}。

    这个 dict 的形状是冻结的（detect_chapter 直接按 key 取值），所以不管最后是
    哪个引擎应答，调用方看到的 key 都与 node 工具当年写下的完全一致。
    """
    pdfium = pdfium_module()
    if pdfium is not None:
        try:
            return extract_pdfium(pdfium, pdf_path, out_json)
        except Exception as e:
            if CT_EXTRACTOR == 'pdfium':
                raise
            print('   pypdfium2 抽取失败 (%s)，退回 node' % e)
    return extract_node(pdf_path, out_json)


def build_probe_index(raw):
    """Normalised notes text for anchoring + a code-fence-masked twin.

    The masked twin exists because of a real false anchor: in ch02 the ASCII
    addition table in slide P33 ('0000 0101 | 5 0000 0101 …') also appears in a
    notes *code block* belonging to P34, so a raw search anchors P33 far too
    late.  Masking code regions inside fences removes that class of collision.
    """
    lines = raw.split('\n')
    info = scan(lines)
    start = 0
    if lines and lines[0].strip() == '---':
        for i, l in enumerate(lines):
            if i > 0 and l.strip() == '---':
                start = i + 1
                break
    for i, l in enumerate(lines):
        if '</style>' in l:
            start = max(start, i + 1)
            break
    allb, nocb, loc = [], [], []
    for i in range(start, len(lines)):
        frag = pdf_norm(lines[i])
        if i > start:
            allb.append('\n')
            nocb.append('\n')
            loc.append(i)
        is_code = info[i]['kind'] in ('code', 'fence_open', 'fence_close')
        for c in frag:
            allb.append(c)
            nocb.append('\x00' if is_code else c)
            loc.append(i)
    code_lines = {i + 1 for i, d in enumerate(info)
                  if d['kind'] in ('code', 'fence_open', 'fence_close')}
    return ''.join(allb), ''.join(nocb), loc, lines, info, start, code_lines


def _best_in(page_norm, notes, loc, lo, hi):
    """Longest verbatim run of the page inside notes[lo:hi].  Returns (len, line)."""
    seg = notes[lo:hi]
    n = len(page_norm)
    if n == 0 or not seg:
        return 0, None
    for L in (48, 40, 34, 28, 22, 16, 12):
        if n < L:
            continue
        hit = None
        for st in range(0, n - L + 1):
            idx = seg.find(page_norm[st:st + L])
            if idx >= 0 and (hit is None or idx > hit):
                hit = idx
        if hit is not None:
            return L, loc[lo + hit] + 1
    return 0, None


def _scan_best(page_norm, notes, loc, lo):
    """Longest verbatim run of the page found in `notes` at offset >= lo.

    Returns (length, char_index, notes_line).
    """
    n = len(page_norm)
    if n == 0:
        return 0, None, None
    for L in (48, 40, 34, 28, 22, 16, 12):
        if n < L:
            continue
        hit = None
        for st in range(0, n - L + 1):
            idx = notes.find(page_norm[st:st + L], lo)
            if idx >= 0 and (hit is None or idx > hit):
                hit = idx
        if hit is not None:
            return L, hit, loc[hit] + 1
    return 0, None, None


def find_anchor(page_norm, notes_all, notes_nocode, loc, lo, code_lines):
    """Anchor a slide page to a notes line, tolerating code-block collisions.

    `lo` is a MONOTONIC lower bound on the search offset.  Without it a page
    happily matches a short coincidental run far earlier/later in the notes and
    the check produces noise instead of signal (the first version of this
    detector did exactly that: 9 bogus "violations" on ch03).

    Returns (length, char_index, notes_line, resolved_via_code_free_retry).
    """
    L, idx, ln = _scan_best(page_norm, notes_all, loc, lo)
    if ln is None:
        return 0, None, None, False
    if ln in code_lines:
        L2, idx2, ln2 = _scan_best(page_norm, notes_nocode, loc, lo)
        if ln2 is not None and L2 >= 8 and ln2 not in code_lines:
            return L2, idx2, ln2, True
    return L, idx, ln, False


def detect_chapter(chapter, notes_path, pdf_path, tmpdir, quiet=False, raw=None):
    """Derive non_content_pages + all derived metadata for one chapter.

    `raw` lets a caller analyse notes it holds in memory, so `--add` can run all
    cross-checks BEFORE it writes anything into the project.
    """
    if raw is None:
        with open(notes_path, encoding='utf-8') as f:
            raw = f.read()
    notes_sha = sha256_bytes(raw.encode('utf-8'))
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    slides_sha = sha256_bytes(pdf_bytes)

    text_json = os.path.join(tmpdir, f'{chapter}-text.json')
    dump = run_extractor(pdf_path, text_json)
    npages = dump['numPages']
    ptext = {p['page']: p['text'] for p in dump['pages']}
    assert len(ptext) == npages, 'page dump incomplete'

    notes_all, notes_nocode, loc, lines, info, start, code_lines = \
        build_probe_index(raw)
    markers = [d['i'] + 1 for d in info if d['kind'] == 'marker']
    M = len(markers)

    # ---- check 1: agenda pages -------------------------------------------
    # ★ 这是全脚本最后一处（也是唯一一处）直接拿"原始文本"做子串匹配的地方，
    #   而它正是一个陷阱。pdfium 的 FPDFText_GetText 会把某些课件的议程页报成
    #   "一行一个字"（ch02 第 2 页回来的是 '本 | 章 | 内 | 容'），于是
    #   `AGENDA_MARK in text` 不再命中；第 2 页随之从 non_content_pages 里消失，
    #   content 变成既不是 M 也不是 M+1，后面每个锚点窗口整体错位一页，检测器
    #   当场崩掉（checked 67→3、violations 0→1）。
    #   解法：两边都过 pdf_norm()。pdf_norm() 会删掉空白和 ' | ' 这个行连接符，
    #   所以 '本 | 章 | 内 | 容' 归一化回 '本章内容'，匹配恢复；而对 node 抽取器
    #   而言这一步是恒等变换，因为 pdf_norm('本章内容') == '本章内容'。
    agenda_mark = pdf_norm(AGENDA_MARK)
    agenda = [p for p in range(1, npages + 1)
              if agenda_mark in pdf_norm(ptext.get(p) or '')]
    cover = [1]
    non_content = sorted(set(cover) | set(agenda))
    content = [p for p in range(1, npages + 1) if p not in set(non_content)]

    problems, warnings = [], []

    char_of_line = {}
    for ci, ln0 in enumerate(loc):
        if ln0 + 1 not in char_of_line:
            char_of_line[ln0 + 1] = ci

    def W(n):
        """Char offset where content page C[n]'s notes text begins."""
        if n <= 0:
            return char_of_line.get(start + 1, 0)
        if n - 1 < len(markers):
            return char_of_line.get(markers[n - 1], 0)
        return len(notes_all)

    def window_check(content_list):
        """check 3: content_list[k] 必须匹配自己的窗口。返回统计与明细。

        ★ 抽成函数，是为了「对齐自愈」能复用**同一套**判据 —— 自愈后的结果
          必须再过一遍这个检查，绝不能自己给自己放宽标准。
        """
        _anchors, _checked, _weak = {}, 0, 0
        _violations, _suspects, _warns = [], [], []
        for k in range(1, min(len(content_list) - 1, M) + 1):
            pg = content_list[k]
            pn = pdf_norm(ptext[pg])
            own = _best_in(pn, notes_all, loc, W(k), W(k + 1))
            prv = _best_in(pn, notes_all, loc, W(k - 1), W(k))
            nxt = _best_in(pn, notes_all, loc, W(k + 1), W(k + 2))
            _anchors[pg] = {'own': own, 'prev': prv, 'next': nxt}
            if own[0] < 12:
                _weak += 1
                continue
            _checked += 1
            if own[0] < prv[0] or own[0] < nxt[0]:
                rec = {'marker': k, 'marker_line': markers[k - 1], 'page': pg,
                       'own_len': own[0], 'own_line': own[1],
                       'prev_len': prv[0], 'prev_line': prv[1],
                       'next_len': nxt[0], 'next_line': nxt[1]}
                if own[1] in code_lines:
                    # The match that beat it is code-like; historically this shape
                    # is a coincidence rather than a page shift.
                    _suspects.append(rec)
                    _warns.append(
                        f'marker #{k} -> P{pg}: best in-window match is in a notes '
                        f'code block (len {own[0]}), and a neighbouring window '
                        f'scores higher (prev {prv[0]}, next {nxt[0]}) '
                        f'-- false-anchor pattern, needs a human look')
                else:
                    _violations.append(rec)
        return {'anchors': _anchors, 'checked': _checked, 'weak': _weak,
                'violations': _violations, 'suspects': _suspects, 'warnings': _warns}

    # ---- 对齐自愈：课件比 marker 多出 1~3 页时，找出"课件有、讲义没写"的那几页 ----
    # ★ 为什么需要：原判据把关系写死成 M 或 M+1。实测 ch04 是 **M+2**：
    #     · p3  —— 「本章学习的目的」引言页，在第一个 marker 之前
    #     · p32 —— 「复习：存储层次（二）」，而讲义把"复习一 + 复习二"并进了**同一个**
    #              marker（marker #27 那一节同时写了 16MB 那道题和断电那道题）
    #   101 = 99 + 2 → relation=MISMATCH → 检测器拒绝落盘 → 站上第四周永远装不进来。
    # ★ 做法：先用探针看每页落在哪个窗口；**同一个窗口里出现第二页**，后面那页就是多余的。
    #   排除后必须重新过同一套 check 3（0 违规 + 覆盖率 ≥60%），否则原样退回 MISMATCH。
    auto_skipped = []
    _need = len(content) - (M + 1)
    if 0 < _need <= 3 and M >= 10:

        def _probe_assign(content_list):
            """每页最匹配哪个窗口（探针投票）。None = 探针全落空。"""
            bounds = [W(k) for k in range(1, M + 2)]

            def window_of(pos):
                if pos < bounds[0]:
                    return 0
                for _i in range(len(bounds) - 1, -1, -1):
                    if pos >= bounds[_i]:
                        return _i + 1
                return 0

            out = []
            for _pg in content_list:
                _pn = pdf_norm(ptext[_pg])
                votes = []
                _step = max(12, len(_pn) // 6)
                for _st in range(0, max(1, len(_pn) - 12), _step):
                    _pr = _pn[_st:_st + 12]
                    if len(_pr) < 12:
                        break
                    _pos = notes_all.find(_pr)
                    if _pos >= 0:
                        votes.append(window_of(_pos))
                out.append(max(set(votes), key=votes.count) if votes else None)
            return out

        for _round in range(_need):
            _assign = _probe_assign(content)
            # 断裂点 = 第一个"落到的窗口和自己的下标对不上"的位置
            _break = None
            for _i, _w in enumerate(_assign):
                if _w and _w != _i:
                    _break = _i
                    break
            _cands = []
            if _break is not None:
                _lo = 0
                for _i in range(_break - 1, -1, -1):
                    if _assign[_i] == _i:
                        _lo = _i + 1
                        break
                _cands = list(range(_lo, _break + 1))
            # 同一窗口里的第二页也纳入候选
            _seen, _dup = set(), []
            for _i, _w in enumerate(_assign):
                if not _w or _w <= 0:
                    continue
                if _w in _seen:
                    _dup.append(_i)
                else:
                    _seen.add(_w)
            _cands = sorted(set(_cands) | set(_dup))

            _best = None
            for _drop in _cands:
                _trial = [p for _i, p in enumerate(content) if _i != _drop]
                if len(_trial) != len(content) - 1:
                    continue
                _ev = window_check(_trial)
                if _ev['violations']:
                    continue
                _own0 = sum(1 for _a in _ev['anchors'].values() if _a['own'][0] == 0)
                _score = (_ev['checked'], -_own0)
                if _best is None or _score > _best[0]:
                    _best = (_score, _drop, _ev['checked'])
            if _best is None:
                break
            _drop = _best[1]
            _dropped = content[_drop]
            auto_skipped.append(_dropped)
            content = [p for _i, p in enumerate(content) if _i != _drop]
            non_content = sorted(set(non_content) | {_dropped})

        if auto_skipped:
            _ev_final = window_check(content)
            warnings.append(
                '对齐自愈：把 %s 当作"课件有、讲义无"的页排除'
                '（否则 content=%d 对不上 markers=%d，检测器会拒绝落盘）；'
                '排除后 marker↔页对齐通过**同一套** check 3'
                '（checked=%d，违规 %d）。这几页是课件上单独成页、讲义里没有单独一节的内容。'
                % (sorted(auto_skipped), len(content) + len(auto_skipped), M,
                   _ev_final['checked'], len(_ev_final['violations'])))
            if _ev_final['violations'] or _ev_final['checked'] < 0.6 * len(content):
                # 自愈结果过不了同一套检查 → 整体作废，宁可继续报 MISMATCH
                warnings.append('（自愈结果没通过 check 3，已作废，仍按 MISMATCH 处理）')
                content = [p for p in range(1, npages + 1)
                           if p not in set(non_content) - set(auto_skipped)]
                non_content = sorted(set(non_content) - set(auto_skipped))
                auto_skipped = []

    if len(content) == M:
        relation = 'M'
    elif len(content) == M + 1:
        relation = 'M+1'
    else:
        relation = 'MISMATCH'
        problems.append(
            f'content pages {len(content)} != markers {M} and != {M + 1}')

    # ---- check 3: marker/page WINDOW validation ---------------------------
    # The hypothesis says: the notes text in window [W(k), W(k+1)) is rendered
    # on content page C[k].  So C[k] must match its OWN window, and must match
    # that window at least as well as the neighbouring windows -- which is
    # what catches the dangerous failure: one page missing from
    # non_content_pages shifts every later page and silently mis-points every
    # knowledge point in the chapter.
    #
    # Why windows instead of a global best-match: a plain "best match anywhere"
    # search produced pure noise (9 bogus violations on ch03, plus ch02's
    # P33/P34 ASCII-table collision).  Matching inside the window also makes the
    # code-block collision harmless, because the colliding code block belongs to
    # a DIFFERENT window.
    _ev = window_check(content)
    anchors, checked, weak = _ev['anchors'], _ev['checked'], _ev['weak']
    violations, suspects = _ev['violations'], _ev['suspects']
    warnings.extend(_ev['warnings'])

    # ---- cover sanity: P01 must not anchor into the notes -----------------
    L1, _i1, ln1, _ = find_anchor(pdf_norm(ptext.get(1, '')), notes_all,
                                  notes_nocode, loc, 0, code_lines)
    if L1 >= 20:
        warnings.append(f'P01 looks like content (anchor len {L1} at line {ln1}); '
                        f'is it really the cover?')

    if problems or violations:
        ok = False
    else:
        ok = True

    title = ''
    for d in info:
        if d['kind'] == 'h' and d['level'] == 1:
            title = norm_title(d['title'])
            break

    return {
        'chapter': chapter,
        'title': title,
        'notes_sha256': notes_sha,
        'slides_sha256': slides_sha,
        'slides_pages': npages,
        'non_content_pages': non_content,
        'detection': {
            'agenda_pages': agenda,
            'cover_pages': cover,
            'agenda_mark': AGENDA_MARK,
            'slide_markers': M,
            'content_pages': len(content),
            'relation': relation,
            'anchor_checked': checked,
            'anchor_weak': weak,
            'anchor_violations': len(violations),
            'anchor_suspect': suspects,
            'anchor_warnings': warnings,
            'auto_skipped_pages': auto_skipped,
            'content_page_list': content,
        },
        'ok': ok,
        'problems': problems,
        'warnings': warnings,
        'violations': violations,
    }


def print_detection(d):
    ch = d['chapter']
    det = d['detection']
    print(f'────────────────────────────────────────────────────────────────────')
    print(f'{ch}  "{d["title"]}"')
    print(f'  notes  sha256 {d["notes_sha256"][:16]}…   slides sha256 '
          f'{d["slides_sha256"][:16]}…')
    print(f'  deck pages           : {d["slides_pages"]}')
    print(f'  check 1  agenda pages: {det["agenda_pages"]}  '
          f'(pages containing "{det["agenda_mark"]}")')
    print(f'           cover page  : {det["cover_pages"]}')
    print(f'  ──> non_content_pages = {d["non_content_pages"]}')
    print(f'  check 2  slide markers M = {det["slide_markers"]}, '
          f'content pages = {det["content_pages"]}  ->  relation {det["relation"]}'
          + ('   OK' if det['relation'] in ('M', 'M+1') else '   *** MISMATCH ***'))
    print(f'  check 3  pages with a usable window match = {det["anchor_checked"]}, '
          f'no evidence = {det["anchor_weak"]}, '
          f'violations = {det["anchor_violations"]}, '
          f'suspect = {len(det["anchor_suspect"])}')
    for s in det['anchor_suspect']:
        print(f'           SUSPECT marker #{s["marker"]} (line {s["marker_line"]}) '
              f'-> P{s["page"]}: own window len {s["own_len"]} @line {s["own_line"]}'
              f', prev {s["prev_len"]} @{s["prev_line"]}, '
              f'next {s["next_len"]} @{s["next_line"]}')
    for v in d['violations']:
        print(f'           VIOLATION marker #{v["marker"]} (line {v["marker_line"]}) '
              f'-> P{v["page"]}: own window len {v["own_len"]} @line '
              f'{v["own_line"]}, but prev window scores {v["prev_len"]} and '
              f'next scores {v["next_len"]} -- page may be misplaced')
    for w in det['anchor_warnings']:
        print(f'           warning: {w}')
    for p in d['problems']:
        print(f'           PROBLEM: {p}')
    print(f'  RESULT: {"OK" if d["ok"] else "FAILED"}')


# ---------------------------------------------------------------------------
# image localisation (shared by --add)
# ---------------------------------------------------------------------------
def sync_images(raw, chapter, quiet=False):
    """Download every ../images/x cited by this chapter into content/images/."""
    os.makedirs(IMAGES, exist_ok=True)
    names = []
    for m in IMG_SRC_RE.finditer(raw):
        fn = m.group(2).split('/')[-1]
        if fn not in names:
            names.append(fn)
    man_path = os.path.join(IMAGES, '_manifest.json')
    man = {}
    if os.path.exists(man_path):
        with open(man_path, encoding='utf-8') as f:
            man = json.load(f)
    got = skipped = failed = 0
    for fn in sorted(names):
        p = os.path.join(IMAGES, fn)
        if os.path.exists(p) and os.path.getsize(p) > 0:
            skipped += 1
            continue
        try:
            url = BASE_URL + '/images/' + fn
            st, ct, data = fetch_url(url)
            if not ct.startswith('image/'):
                raise RuntimeError(f'not an image: Content-Type {ct}')
            with open(p, 'wb') as f:
                f.write(data)
            man[fn] = {'bytes': len(data), 'sha256': sha256_bytes(data),
                       'content_type': ct, 'url': url}
            got += 1
            if not quiet:
                print(f'      + {fn} ({len(data):,} B, {ct})')
        except Exception as e:
            failed += 1
            print(f'      ! FAILED {fn}: {e}')
    # 只在字节真的会变时才落盘。无变化的重建不该去动 content/images/_manifest.json
    # 的 mtime——桌面端有"内容文件被动过就整轮失败"的守卫。
    want = json.dumps(man, ensure_ascii=False, indent=1, sort_keys=True)
    cur = None
    if os.path.exists(man_path):
        with open(man_path, encoding='utf-8') as f:
            cur = f.read()
    if cur != want:
        with open(man_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(want)
    print(f'   images: {len(names)} cited, {got} downloaded, {skipped} already '
          f'present, {failed} FAILED')
    return {'cited': len(names), 'downloaded': got, 'present': skipped,
            'failed': failed}


def _png_bytes(bitmap):
    """把 pypdfium2 的 PdfBitmap 编码成 8 位真彩 PNG，只用标准库。

    本机既没有 Pillow 也没有 numpy（bitmap.to_pil() 会 ModuleNotFoundError，
    to_numpy() 同样），如果为此去装一个第三方包，就等于给一条本来零第三方依赖
    的流水线凭空加一个依赖。PNG 的基线格式用 zlib + struct 就够写出来。
    注意：字节与 node 渲染器产出的 PNG 不同（编码器不同），app 依赖的是尺寸、
    色彩模型和 page-NN.png 这个命名。
    """
    w, h, stride, n = bitmap.width, bitmap.height, bitmap.stride, bitmap.n_channels
    if n < 3:
        raise RuntimeError('unsupported pdfium bitmap format %r (%d channels)'
                           % (bitmap.format, n))
    mv = bytes(bitmap.buffer)
    row_bytes = w * 3
    parts = []
    for y in range(h):
        src = mv[y * stride:y * stride + row_bytes]        # 每行是 BGR(A)
        row = bytearray(row_bytes)
        row[0::3] = src[2::n]                              # R
        row[1::3] = src[1::n]                              # G
        row[2::3] = src[0::n]                              # B
        parts.append(bytes(row))
    raw = b'\x00' + b'\x00'.join(parts)                    # 每条扫描线前缀 filter 0

    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data
                + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))

    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw, 6))
            + chunk(b'IEND', b''))


def render_pdfium(pdfium, pdf_path, outdir):
    """pypdfium2 版的 render-pdf.mjs：scale 1.4 -> 1344x756，page-NN.png。"""
    doc = pdfium.PdfDocument(pdf_path)
    try:
        for i in range(len(doc)):
            page = doc[i]
            try:
                bitmap = page.render(scale=1.4)
                try:
                    data = _png_bytes(bitmap)
                finally:
                    bitmap.close()
            finally:
                page.close()
            # %02d 与 JS String(i).padStart(2, '0') 一致：01..90，第 100 页才是 100
            with open(os.path.join(outdir, 'page-%02d.png' % (i + 1)), 'wb') as f:
                f.write(data)
    finally:
        doc.close()


def render_node(pdf_path, outdir):
    """兜底：node 渲染器（行为未变）。"""
    proc = subprocess.run(['node', RENDERER, pdf_path, outdir, '1.4'],
                          capture_output=True, text=True, encoding='utf-8',
                          errors='replace')
    if proc.returncode != 0:
        raise RuntimeError('render failed:\n' + (proc.stderr or '')[-1200:])


def render_pages(pdf_path, chapter, npages, quiet=False):
    """Render the deck to content/slides/chNN/page-NN.png (1344x756 at 1.4)."""
    outdir = os.path.join(SLIDES, chapter)
    have = 0
    if os.path.isdir(outdir):
        have = len([f for f in os.listdir(outdir)
                    if re.fullmatch(r'page-\d+\.png', f)])
    if have == npages:
        print(f'   slides: {have}/{npages} PNGs already present, skipping render')
        return have
    os.makedirs(outdir, exist_ok=True)
    print(f'   slides: rendering {npages} pages -> {outdir}')
    pdfium = pdfium_module()
    if pdfium is not None:
        try:
            render_pdfium(pdfium, pdf_path, outdir)
        except Exception as e:
            if CT_EXTRACTOR == 'pdfium':
                raise
            print('   pypdfium2 渲染失败 (%s)，退回 node' % e)
            render_node(pdf_path, outdir)
    else:
        render_node(pdf_path, outdir)
    have = len([f for f in os.listdir(outdir)
                if re.fullmatch(r'page-\d+\.png', f)])
    print(f'   slides: {have} PNGs written')
    return have


def build(chapter):
    cfg = CHAPTERS[chapter]
    path = os.path.join(NOTES, chapter + '.md')
    raw = open(path, encoding='utf-8').read()
    sha = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    assert sha == cfg['notes_sha256'], (chapter, sha)
    lines = raw.split('\n')
    info = scan(lines)

    # ---- content window: skip front-matter and <style> ---------------------
    content_start = 0
    if lines and lines[0].strip() == '---':
        for i, l in enumerate(lines):
            if i > 0 and l.strip() == '---':
                content_start = i + 1
                break
    for i, l in enumerate(lines):
        if '</style>' in l:
            content_start = max(content_start, i + 1)
            break

    # ---- slide page table -------------------------------------------------
    n_pages = cfg['slides_pages']
    non_content = set(cfg['non_content_pages'])
    C = [p for p in range(1, n_pages + 1) if p not in non_content]
    markers = [d['i'] + 1 for d in info if d['kind'] == 'marker']   # 1-based lines

    # marker #n (1-based) starts content page C[n]; content before marker 1 is C[0]
    starts = [(content_start + 1, C[0])]                            # (line, page)
    for n in range(1, min(len(C) - 1, len(markers)) + 1):
        starts.append((markers[n - 1] + 1, C[n]))

    def page_at(line):
        pg = starts[0][1]
        for st, p in starts:
            if st <= line:
                pg = p
            else:
                break
        return pg

    def pages_for(a, b):
        """pages covered by notes lines [a, b] (1-based, closed)."""
        # last substantive line (ignore blanks and SLIDE markers)
        ce = a
        for i in range(a - 1, b):
            s = lines[i].strip()
            if s and not MARKER_RE.match(lines[i]):
                ce = i + 1
        pages = {page_at(a)}
        for n in range(1, min(len(C) - 1, len(markers)) + 1):
            m = markers[n - 1]
            if a < m <= ce:
                pages.add(C[n])
        return sorted(pages)

    # ---- sections / points ------------------------------------------------
    h2s = [(d['i'] + 1, d['title']) for d in info
           if d['kind'] == 'h' and d['level'] == 2]
    sections = []
    diagnostics = {'oversized': [], 'skipped_empty_sections': [],
                   'points_total': 0, 'h3_count': 0, 'h4_count': 0,
                   'empty_body': 0, 'pitfalls': 0, 'runs': 0, 'sections': 0,
                   'img_refs': 0, 'iframe_stripped': 0, 'svg_stripped': 0,
                   'ref_points': 0, 'ref_entries': 0,
                   'pitfall_detail': []}

    # ---- top-level intro / summary (normally-empty ## sections) ------------
    special = {}
    for ln, title in h2s:
        end = next((x for x, _ in h2s if x > ln), len(lines) + 1) - 1
        t = norm_title(title)
        if t in ('本章学习的目的', '本章总结', '更正记录'):
            block = '\n'.join(lines[ln - 1:end])
            special[t] = {'md': strip_unsupported_tags(rewrite_img_src(block)),
                          'lines': [ln, end]}
    diagnostics['special_sections'] = special

    # Caliber (parent, authoritative): only ## sections that contain at least one
    # ### participate in numbering; they are numbered 1..N consecutively, and the
    # empty ## sections (本章学习的目的 / 本章总结 / 更正记录) are skipped entirely.
    for ln, title in h2s:
        end = next((x for x, _ in h2s if x > ln), len(lines) + 1) - 1
        h3s = [(d['i'] + 1, d['title']) for d in info
               if d['kind'] == 'h' and d['level'] == 3 and ln < d['i'] + 1 <= end]
        h4s = [(d['i'] + 1, d['title']) for d in info
               if d['kind'] == 'h' and d['level'] == 4 and ln < d['i'] + 1 <= end]
        diagnostics['h3_count'] += len(h3s)
        diagnostics['h4_count'] += len(h4s)
        if not h3s:
            diagnostics['skipped_empty_sections'].append(
                {'chapter': chapter, 'line': ln, 'title': norm_title(title),
                 'span_lines': end - ln + 1})
            continue
        si = len(sections) + 1          # 1..N over non-empty sections only

        points = []
        for pi, (p_ln, p_title) in enumerate(h3s, 1):
            nxt = [x for x, _ in h3s[pi:]]
            p_end = (nxt[0] - 1) if nxt else end
            span = p_end - p_ln + 1
            if span > MAX_BODY_LINES:
                diagnostics['oversized'].append({
                    'chapter': chapter, 'section': si, 'point': p_title,
                    'span_lines': span, 'level': 3,
                })
            a, b, level = p_ln, p_end, 3      # #### are NOT split out (caliber 2)
            raw_body = '\n'.join(lines[a - 1:b])
            pid = '%s-s%02d-p%02d' % (chapter, si, len(points) + 1)
            # only src values may differ; ../images/ must live only inside src
            assert raw_body.count('../images/') == len(IMG_SRC_RE.findall(raw_body)), \
                'stray ../images/ outside a src attribute: %s' % pid
            diagnostics['img_refs'] += len(IMG_SRC_RE.findall(raw_body))
            tstats = {}
            body = strip_unsupported_tags(rewrite_img_src(raw_body), tstats)
            diagnostics['iframe_stripped'] += tstats.get('iframe', 0)
            diagnostics['svg_stripped'] += tstats.get('svg', 0)
            ntitle = norm_title(p_title)
            pit, pit_lines = find_pitfall(lines, a, b)
            run = RUN.get((chapter, ntitle))
            if not body.strip():
                diagnostics['empty_body'] += 1
            if pit:
                diagnostics['pitfalls'] += 1
                diagnostics['pitfall_detail'].append({
                    'point': pid, 'title': ntitle, 'lines': pit_lines,
                    'text': pit,
                    'original': '\n'.join(lines[x - 1] for x in pit_lines)})
            if run:
                diagnostics['runs'] += 1
            refs = build_refs(ntitle)
            if refs:
                diagnostics['ref_points'] += 1
                diagnostics['ref_entries'] += len(refs)
            points.append({
                'id': pid,
                'no': len(points) + 1,
                'title': ntitle,
                'level': level,
                'body_md': body,
                'notes_lines': [a, b],
                'slides': pages_for(a, b),
                'pitfall': pit,
                'video': None,
                'refs': refs,
                'run': run,
            })
        allp = [p for pt in points for p in pt['slides']]
        diagnostics['sections'] += 1
        diagnostics['points_total'] += len(points)
        sections.append({
            'id': '%s-s%02d' % (chapter, si),
            'no': si,
            'title': norm_title(title),
            'slide_range': [min(allp), max(allp)],
            'points': points,
        })

    # Intro / summary come from the normally-empty ## sections, which are NOT
    # numbered (caliber: empty sections take no id) -- so they live in top-level
    # fields instead of synthetic points, keeping the 104 point ids untouched.
    # errata_md is deliberately NOT emitted: '## 更正记录' is an internal
    # contribution/bonus ledger ("感谢以下同学…+0.5 贡献加分"), not errata.
    doc = {
        'chapter': chapter,
        'title': cfg['title'],
        'intro_md': special.get('本章学习的目的', {}).get('md'),
        'summary_md': special.get('本章总结', {}).get('md'),
        'source': {
            'notes_url': f'{BASE_URL}/notes/{chapter}.md',
            'notes_sha256': cfg['notes_sha256'],
            'slides_url': f'{BASE_URL}/slides/{chapter}.pdf',
            'slides_sha256': cfg['slides_sha256'],
            'slides_pages': cfg['slides_pages'],
            'fetched_at': cfg.get('fetched_at') or FETCHED_AT,
        },
        'sections': sections,
    }
    return doc, diagnostics


def baseline_ids():
    """Ordered id list from _point-ids.txt (the drift baseline)."""
    if not os.path.exists(ID_LIST_FILE):
        return []
    txt = open(ID_LIST_FILE, encoding='utf-8').read()
    seen, out = set(), []
    for m in re.finditer(r'ch\d{2}-s\d{2}-p\d{2}', txt):
        if m.group(0) not in seen:
            seen.add(m.group(0))
            out.append(m.group(0))
    return out


def current_ids(chapter, doc=None):
    d = doc if doc is not None else build(chapter)[0]
    return [p['id'] for s in d['sections'] for p in s['points']]


def id_drift(chapter, current):
    """Compare a chapter's freshly built ids against the _point-ids.txt baseline.

    chNN-sMM-pKK is POSITIONAL: inserting or deleting one ### shifts every later
    id in that chapter, so saved progress and videos.json keys silently point at
    the wrong knowledge point.  This is the alarm for exactly that.
    """
    base = [i for i in baseline_ids() if i.startswith(chapter)]
    if not base:
        return 'new', f'ids (no baseline) -> {len(current)}, 首次加入', False
    if base == current:
        return 'same', f'ids {len(base)} -> {len(current)}, 集合相同', False
    bs, cs = set(base), set(current)
    added = [i for i in current if i not in bs]
    removed = [i for i in base if i not in cs]
    k = next((n for n in range(min(len(base), len(current)))
              if base[n] != current[n]), min(len(base), len(current)))
    where = current[k] if k < len(current) else (base[k] if k < len(base) else '?')
    sec = re.match(r'(ch\d{2}-s\d{2})', where)
    detail = (f'ids {len(base)} -> {len(current)}, 新增 {len(added)} 个, '
              f'移除 {len(removed)} 个; 首次分歧 idx {k} ({where})'
              + (f' -> {sec.group(1)} 之后整体平移' if sec else ''))
    if added:
        detail += f'; 新增例 {added[:3]}'
    if removed:
        detail += f'; 移除例 {removed[:3]}'
    return 'DRIFT', detail, True


def refresh_point_ids(order=None):
    """Regenerate _point-ids.txt from the current chNN.json files."""
    order = order or [c for c in CHAPTER_ORDER
                      if os.path.exists(os.path.join(CONTENT, c + '.json'))]
    docs = [(ch, json.load(open(os.path.join(CONTENT, ch + '.json'),
                                encoding='utf-8'))) for ch in order]
    grand = 0
    for _, d in docs:
        grand += sum(len(s['points']) for s in d['sections'])
    out = ['# content/chNN.json -> point ids (%d total)' % grand,
           '# id | section | level | notes_lines | slides | title', '']
    for ch, d in docs:
        pts = [p for s in d['sections'] for p in s['points']]
        out.append('# ===== %s  %s  |  %d sections, %d points  |  slides %d pages  '
                   '|  notes sha256 %s' % (ch, d['title'], len(d['sections']),
                                           len(pts), d['source']['slides_pages'],
                                           d['source']['notes_sha256']))
        for s in d['sections']:
            out.append('#   %s  no=%d  %s   slide_range=%s  (%d points)' % (
                s['id'], s['no'], s['title'], s['slide_range'], len(s['points'])))
            for p in s['points']:
                out.append('%-16s %-16s s%02d level=%d lines=%-11s slides=%-14s %s'
                           % (p['id'], s['id'], s['no'], p['level'],
                              '[%d,%d]' % tuple(p['notes_lines']),
                              str(p['slides']), p['title']))
        out.append('')
    out.append('# TOTAL %d points' % grand)
    with open(ID_LIST_FILE, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    print(f'   ids list refreshed: {ID_LIST_FILE} ({grand} points)')
    return grand


def report_drift(chapters):
    print('--- id drift vs _point-ids.txt baseline ---')
    bad = []
    for ch in chapters:
        try:
            status, detail, is_bad = id_drift(ch, current_ids(ch))
        except Exception as e:
            print(f'{ch}: cannot build ({e})')
            continue
        mark = {'same': '  ok  ', 'new': ' new  ', 'DRIFT': '!!!!!!'}[status]
        print(f'{mark} {ch}: {detail}')
        if is_bad:
            bad.append(ch)
    if bad:
        print()
        print('  *** ID DRIFT DETECTED in ' + ', '.join(bad) + ' ***')
        print('  Positional ids shifted, so saved progress and the videos.json')
        print('  mapping for these chapters are stale and need remapping.')
    return bad


def check_remote(chapters):
    """--check: remote sha256 vs the registry + id drift.  Writes nothing."""
    print('=== remote content check ===')
    print('%-6s %-9s %-9s %s' % ('ch', 'artifact', 'state', 'sha256'))
    changed = []
    for ch in chapters:
        if ch not in CHAPTERS:
            print('%-6s %-9s %-9s %s' % (ch, '-', 'UNKNOWN', 'not in registry'))
            continue
        for kind, url, key in (
                ('notes', f'{BASE_URL}/notes/{ch}.md', 'notes_sha256'),
                ('slides', f'{BASE_URL}/slides/{ch}.pdf', 'slides_sha256')):
            local = CHAPTERS[ch][key]
            try:
                _, _, data = fetch_url(url, tries=3)
                remote = sha256_bytes(data)
            except Exception as e:
                print('%-6s %-9s %-9s %s' % (ch, kind, 'ERROR', e))
                changed.append(ch)
                continue
            same = remote == local
            if not same:
                changed.append(ch)
            print('%-6s %-9s %-9s %s' % (ch, kind, 'same' if same else 'CHANGED',
                                         remote[:16] + '…'))
            if not same:
                print('%-6s %-9s %-9s %s   (registry)'
                      % ('', '', '', local[:16] + '…'))
    print()
    if changed:
        print('CHANGED upstream:', sorted(set(changed)))
        print('  -> review, then: python content/notes/_build-json.py --only chNN')
    else:
        print('All chapters up to date.')
    print()
    bad = report_drift([c for c in chapters if c in CHAPTERS])
    return sorted(set(changed)), bad


def detect_cmd(chapters, tmpdir):
    """--detect: analysis only.  Writes nothing."""
    results = {}
    for ch in chapters:
        print('=' * 76)
        print(f'--detect {ch}')
        try:
            notes_path = os.path.join(NOTES, ch + '.md')
            if not os.path.exists(notes_path):
                print(f'  notes not local, fetching {BASE_URL}/notes/{ch}.md')
                _, _, nb = fetch_url(f'{BASE_URL}/notes/{ch}.md')
                notes_path = os.path.join(tmpdir, ch + '.md')
                with open(notes_path, 'wb') as f:
                    f.write(nb)
            pdf_path = ensure_pdf(ch, tmpdir)
            d = detect_chapter(ch, notes_path, pdf_path, tmpdir)
            print_detection(d)
            results[ch] = d
        except Exception as e:
            print(f'  ERROR: {e}')
            results[ch] = None
    print('=' * 76)
    print('summary (nothing was written):')
    for ch, d in results.items():
        if d is None:
            print(f'  {ch}: FAILED (see above)')
        else:
            print(f'  {ch}: non_content_pages = {d["non_content_pages"]}   '
                  f'(pages={d["slides_pages"]}, markers='
                  f'{d["detection"]["slide_markers"]}, content='
                  f'{d["detection"]["content_pages"]}, '
                  f'relation={d["detection"]["relation"]})  '
                  f'{"OK" if d["ok"] else "FAILED"}')
    return results


# Independently established ground truth for the three existing chapters (from
# the original manual analysis).  The detector must reproduce these EXACTLY -- a
# one-page error here mis-points every knowledge point in the chapter.
KNOWN_NON_CONTENT = {
    'ch01': [1, 2],
    'ch02': [1, 2, 9, 23, 36, 44, 89],
    'ch03': [1, 2, 5, 13, 23, 31, 41, 52, 64, 80, 89],
}


def selftest_detect(tmpdir):
    """--selftest-detect: prove the detector reproduces the three known decks.

    ch04 does not exist yet, so reproducing three independently-known answers is
    the only honest way to show the logic is right.  READ-ONLY.
    """
    print('=' * 88)
    print('DETECTOR SELF-TEST: auto-derived non_content_pages vs known-correct values')
    print('=' * 88)
    rows, failures = [], []
    for ch in sorted(KNOWN_NON_CONTENT):
        notes_path = os.path.join(NOTES, ch + '.md')
        pdf_path = ensure_pdf(ch, tmpdir)
        d = detect_chapter(ch, notes_path, pdf_path, tmpdir, quiet=True)
        got = d['non_content_pages']
        want = KNOWN_NON_CONTENT[ch]
        reg = (CHAPTERS.get(ch) or {}).get('non_content_pages')
        ok = got == want
        ok_reg = reg is None or reg == want
        print()
        print(f'{ch}: deck {d["slides_pages"]}p, markers '
              f'{d["detection"]["slide_markers"]}, content '
              f'{d["detection"]["content_pages"]} '
              f'(relation {d["detection"]["relation"]}), '
              f'anchors checked {d["detection"]["anchor_checked"]}, '
              f'violations {d["detection"]["anchor_violations"]}, '
              f'suspect {len(d["detection"]["anchor_suspect"])}')
        print(f'  agenda pages detected : {d["detection"]["agenda_pages"]}')
        print(f'  derived   : {got}')
        print(f'  expected  : {want}')
        print(f'  registry  : {reg}')
        print(f'  VERDICT   : {"MATCH" if ok else "*** MISMATCH ***"}'
              f'{"" if ok_reg else "   (registry disagrees!)"}')
        rows.append((ch, d, got, want, ok))
        if not ok:
            failures.append(ch)
        if not ok_reg:
            failures.append(ch + '(registry)')
        if d['violations']:
            failures.append(ch + '(anchor violations)')
        for w in d['warnings']:
            print(f'  warning   : {w}')
    print()
    print('=' * 88)
    print('%-6s %-8s %-8s %-8s %-9s %s' % ('ch', 'pages', 'markers', 'content',
                                           'relation', 'non_content_pages'))
    for ch, d, got, want, ok in rows:
        det = d['detection']
        print('%-6s %-8d %-8d %-8d %-9s %s  %s' % (
            ch, d['slides_pages'], det['slide_markers'], det['content_pages'],
            det['relation'], got, 'MATCH' if ok else 'MISMATCH'))
    print()
    if failures:
        print('SELF-TEST FAILED:', failures)
        return 1
    print('SELF-TEST PASSED: all %d chapters reproduced exactly.' % len(rows))
    return 0


def ensure_pdf(chapter, tmpdir):
    """Return a local path to the chapter's deck PDF, downloading if needed.

    ★★ 缓存必须校验大小再复用。原来只判"文件存在且非空"，于是：
       %TEMP%\\ct_pipeline\\ch04.pdf 里如果躺着的是 **ch02 的 PDF**（23,737,618 B，
       实测过），--detect ch04 会拿 ch02 的课件去分析 ch04，
       报出一堆"agenda pages 和 ch02 一模一样 / markers 99 != content 101"的
       误导性结果 —— 而且**只报 FAILED，不告诉你分析错了对象**。
       排查成本极高（我先怀疑站点的文件、又怀疑检测器，最后才发现是缓存放错了）。
       修法：用远端 Content-Length 比一下本地大小，不一致就重下。
       HEAD 拿不到长度时**保守重下**（宁可多下一次，也不要拿错文件出结果）。
    """
    pdf_path = os.path.join(tmpdir, chapter + '.pdf')
    url = f'{BASE_URL}/slides/{chapter}.pdf'
    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
        local = os.path.getsize(pdf_path)
        remote = None
        # ★ import 必须在函数内：这个文件顶层**没有** import urllib（fetch_url 也是函数内导入）。
        #   第一版我在这里直接用 urllib.request，于是 NameError 被下面的 except 吞掉、
        #   remote 永远是 None，结果**每次 --detect 都重下 19.5MB**。
        #   教训：过宽的 except 会把"代码写错"伪装成"网络不给"。
        try:
            import urllib.request
            req = urllib.request.Request(url, method='HEAD',
                                         headers={'User-Agent': UA, 'Accept': '*/*'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                cl = resp.headers.get('Content-Length')
                remote = int(cl) if cl else None
        except Exception as e:                                   # noqa: BLE001
            print(f'  HEAD failed for {chapter} ({e!r}) -> 保守重下')
            remote = None
        if remote is not None and remote == local:
            return pdf_path
        print(f'  cache mismatch for {chapter}: local {local:,} B vs remote '
              f'{remote if remote is not None else "?"} B -> re-downloading')
    print(f'  fetching {url}')
    _, _, pb = fetch_url(url)
    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) == len(pb):
        return pdf_path
    with open(pdf_path, 'wb') as f:
        f.write(pb)
    print(f'  cached -> {pdf_path} ({len(pb):,} B)')
    return pdf_path


def add_chapter(chapter, tmpdir):
    """--add chNN: fetch + detect + render + images + registry + rebuild."""
    print('=' * 76)
    print(f'--add {chapter}')
    print('[1/7] fetch notes + slides')
    # Fetch BOTH before writing anything: if the chapter does not exist we abort
    # with a clean message instead of leaving a half-added chapter on disk.
    notes_url = f'{BASE_URL}/notes/{chapter}.md'
    slides_url = f'{BASE_URL}/slides/{chapter}.pdf'
    try:
        _, _, nb = fetch_url(notes_url)
        _, _, pb = fetch_url(slides_url)
    except Exception as e:
        print(f'  ERROR: {e}')
        print(f'  Could not fetch {notes_url} / {slides_url}.')
        print('  Nothing was written.  Does the chapter exist on the course site?')
        return 1
    notes_path = os.path.join(NOTES, chapter + '.md')
    print(f'   notes  {len(nb):,} B (not written yet)')
    pdf_path = os.path.join(tmpdir, chapter + '.pdf')
    with open(pdf_path, 'wb') as f:
        f.write(pb)
    print(f'   slides {len(pb):,} B')
    raw = nb.decode('utf-8')

    print('[2/7] derive non_content_pages')
    # analyse from memory: nothing enters the project until every check passes
    d = detect_chapter(chapter, notes_path, pdf_path, tmpdir, raw=raw)
    print_detection(d)
    if not d['ok']:
        print()
        print('  *** REFUSING TO WRITE: cross-checks did not pass. ***')
        print('  The content-page count and the <!-- SLIDE --> markers disagree,')
        print('  so non_content_pages cannot be trusted.  NOTHING was written')
        print('  (not the notes, not the registry, not images, not slides).')
        print('  Fix the deck/notes mismatch, or run --detect and inspect manually.')
        return 1
    if d['warnings']:
        print('  (warnings above are non-fatal but worth a human look)')

    with open(notes_path, 'wb') as f:
        f.write(nb)
    print(f'   notes written -> {notes_path}')

    print('[3/7] render deck -> PNG')
    render_pages(pdf_path, chapter, d['slides_pages'])

    print('[4/7] localise note images')
    sync_images(raw, chapter)

    print('[5/7] update registry (generated; sha256 is never hand-copied)')
    prev = CHAPTERS.get(chapter)
    unchanged = bool(prev
                     and prev['notes_sha256'] == d['notes_sha256']
                     and prev['slides_sha256'] == d['slides_sha256'])
    fetched_at = (prev.get('fetched_at') if unchanged and prev.get('fetched_at')
                  else time.strftime('%Y-%m-%dT%H:%M:%S+08:00'))
    entry = {
        'title': d['title'],
        'notes_sha256': d['notes_sha256'],
        'slides_sha256': d['slides_sha256'],
        'slides_pages': d['slides_pages'],
        'non_content_pages': d['non_content_pages'],
        'fetched_at': fetched_at,
        'detection': d['detection'],
    }
    order = list(CHAPTER_ORDER)
    if chapter not in order:
        order.append(chapter)
        order.sort()
    chapters = dict(CHAPTERS)
    chapters[chapter] = entry
    print('   %s (fetched_at=%s)' % (
        'unchanged upstream -> kept fetched_at' if unchanged
        else 'new/changed content -> fetched_at = now', fetched_at))
    save_registry(order, chapters)

    print('[6/7] rebuild chNN.json')
    status, detail, drift = id_drift(chapter, current_ids(chapter))
    print(f'   drift check [{status}]: {detail}')
    doc, diag = build(chapter)
    out = os.path.join(CONTENT, chapter + '.json')
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(f'   {chapter}: sections={diag["sections"]} points={diag["points_total"]} '
          f'pitfalls={diag["pitfalls"]} runs={diag["runs"]} '
          f'img_refs={diag["img_refs"]}')

    print('[7/7] refresh _point-ids.txt')
    refresh_point_ids()
    if drift:
        print()
        print('  *** STRUCTURE CHANGED for ' + chapter + ' ***')
        print('  ' + detail)
        print('  Re-confirm the videos.json mapping and any saved user progress,')
        print('  or the card flow will show the wrong video for shifted ids.')
    print()
    print(f'--add {chapter}: done.')
    return 0


def _rebuild_one_inner(chapter, tmpdir):
    """--rebuild-one chNN 的实现体，按 --add 的后半段顺序执行。"""
    print('=' * 76)
    print(f'--rebuild-one {chapter}')
    notes_path = os.path.join(NOTES, chapter + '.md')
    pdf_path = os.path.join(tmpdir, chapter + '.pdf')
    # 这两个输入由调用方（桌面端）事先放好。缺了就明确报错，绝不在重建路径上
    # 偷偷联网——离线包里没有网络可联。
    if not os.path.exists(notes_path):
        raise RuntimeError('notes not staged at %s' % notes_path)
    if not (os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0):
        raise RuntimeError('deck PDF not staged at %s' % pdf_path)
    with open(notes_path, encoding='utf-8') as f:
        raw = f.read()
    print(f'   notes  {len(raw.encode("utf-8")):,} B  {notes_path}')
    print(f'   slides {os.path.getsize(pdf_path):,} B  {pdf_path}')

    # 顺序与 --add 严格一致：先更新 registry，后 build()——因为 build() 会断言
    # notes 的 sha256 等于 cfg['notes_sha256']，而这两个 hash 正是这里刚读进来的
    # 那份字节算出来的，所以断言在后续每次运行都成立。
    print('[1/5] derive non_content_pages')
    d = detect_chapter(chapter, notes_path, pdf_path, tmpdir, raw=raw)
    print_detection(d)
    if not d['ok']:
        raise RuntimeError('detector cross-checks failed: '
                           + '; '.join(d['problems'] or ['see --detect']))

    print('[2/5] render deck -> PNG')
    render_pages(pdf_path, chapter, d['slides_pages'])

    print('[3/5] localise note images')
    sync_images(raw, chapter)

    print('[4/5] update registry (this chapter only)')
    prev = CHAPTERS.get(chapter)
    unchanged = bool(prev
                     and prev['notes_sha256'] == d['notes_sha256']
                     and prev['slides_sha256'] == d['slides_sha256'])
    fetched_at = (prev.get('fetched_at') if unchanged and prev.get('fetched_at')
                  else time.strftime('%Y-%m-%dT%H:%M:%S+08:00'))
    chapters = dict(CHAPTERS)
    chapters[chapter] = {
        'title': d['title'],
        'notes_sha256': d['notes_sha256'],
        'slides_sha256': d['slides_sha256'],
        'slides_pages': d['slides_pages'],
        'non_content_pages': d['non_content_pages'],
        'fetched_at': fetched_at,
        'detection': d['detection'],
    }
    order = list(CHAPTER_ORDER)
    if chapter not in order:
        order.append(chapter)
        order.sort()
    save_registry(order, chapters)
    print('   %s (fetched_at=%s)' % (
        'unchanged upstream -> kept fetched_at' if unchanged
        else 'new/changed content -> fetched_at = now', fetched_at))

    print('[5/5] rebuild chNN.json')
    status, detail, drift = id_drift(chapter, current_ids(chapter))
    print(f'   drift check [{status}]: {detail}')
    if drift:
        print('   WARNING: id drift detected.  --rebuild-one does NOT rewrite '
              '_point-ids.txt (that baseline belongs to --add).')
    doc, diag = build(chapter)
    out = os.path.join(CONTENT, chapter + '.json')
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(f'   wrote {out}')
    print()
    print('REBUILD-OK %s slides=%d points=%d' % (
        chapter, doc['source']['slides_pages'], diag['points_total']))
    return 0


def rebuild_one(chapter, tmpdir):
    """--rebuild-one chNN: 单章端到端重建，只碰这一章，全程不联网。

    这是桌面端要的入口。调用方把输入放好之后：
        <CT_ROOT>/content/notes/chNN.md    （讲稿）
        <CT_TMP>/chNN.pdf                  （课件，CT_TMP 默认 = <CT_ROOT>/tmp）
    本函数依次做：detect -> 渲染 PNG -> 本地化图片 -> 只更新这一章的 registry
    条目 -> 写 <CT_ROOT>/content/chNN.json，最后打印
        REBUILD-OK <chapter> slides=<n> points=<n>
    任一步失败则打印 REBUILD-FAIL <chapter> <reason> 并返回 1。

    ★ 故意不调用 refresh_point_ids()：_point-ids.txt 是漂移基线，按约定只有
      --add 能写它。这里只做只读的漂移检查，发现漂移就大声报警。
    ★ 与 --add 的差别仅此两点：不下载 notes/PDF，不写漂移基线。
    """
    try:
        return _rebuild_one_inner(chapter, tmpdir)
    except Exception as e:
        reason = ' '.join(str(e).split()) or e.__class__.__name__
        print(f'REBUILD-FAIL {chapter} {reason}')
        return 1


def main():
    argv = sys.argv[1:]
    tmpdir = os.environ.get('CT_TMP') or os.path.join(
        os.environ.get('TEMP', '.'), 'ct_pipeline')
    os.makedirs(tmpdir, exist_ok=True)

    def opt(name):
        return (argv[argv.index(name) + 1]
                if name in argv and argv.index(name) + 1 < len(argv) else None)

    if '--selftest-detect' in argv:
        return selftest_detect(tmpdir)

    if '--refs-report' in argv:
        return refs_report()

    if '--detect' in argv:
        ch = opt('--detect')
        targets = [ch] if ch else list(CHAPTER_ORDER)
        res = detect_cmd(targets, tmpdir)
        return 0 if all(d is not None for d in res.values()) else 1

    if '--add' in argv:
        ch = opt('--add')
        if not ch:
            print('--add needs a chapter name, e.g. --add ch04', file=sys.stderr)
            return 2
        if not re.fullmatch(r'ch\d{2}', ch):
            print(f'bad chapter name {ch!r}; expected chNN', file=sys.stderr)
            return 2
        return add_chapter(ch, tmpdir)

    if '--rebuild-one' in argv:
        ch = opt('--rebuild-one')
        if not ch:
            print('--rebuild-one needs a chapter name, e.g. --rebuild-one ch03',
                  file=sys.stderr)
            return 2
        if not re.fullmatch(r'ch\d{2}', ch):
            print(f'bad chapter name {ch!r}; expected chNN', file=sys.stderr)
            return 2
        return rebuild_one(ch, tmpdir)

    only = opt('--only')
    if only and only not in CHAPTERS:
        print(f'--only needs one of {sorted(CHAPTERS)}', file=sys.stderr)
        return 2
    chapters = [only] if only else list(CHAPTER_ORDER)

    if '--check' in argv:
        changed, bad = check_remote(chapters)
        # exit code is the probe: 0 = nothing changed and no drift
        return 1 if (changed or bad) else 0

    all_diag = {}
    drift_seen = []
    outcomes = []
    failed = False
    for chapter in chapters:
        try:
            doc, diag = build(chapter)
            status, detail, is_bad = id_drift(chapter, current_ids(chapter, doc))
            out = os.path.join(CONTENT, chapter + '.json')
            with open(out, 'w', encoding='utf-8', newline='\n') as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
                f.write('\n')
        except Exception as e:
            # 桌面端是 import 本模块后直接调 main() 的，所以某一章炸掉时必须留下
            # 一行能解析的 REBUILD-FAIL，而不是它读不懂的 traceback。
            failed = True
            reason = ' '.join(str(e).split()) or e.__class__.__name__
            outcomes.append('REBUILD-FAIL %s %s' % (chapter, reason))
            print(f'{chapter}: FAILED -- {reason}')
            continue
        all_diag[chapter] = diag
        outcomes.append('REBUILD-OK %s slides=%d points=%d' % (
            chapter, doc['source']['slides_pages'], diag['points_total']))
        if is_bad:
            drift_seen.append((chapter, detail))
        print(f'{chapter}: sections={diag["sections"]} points={diag["points_total"]} '
              f'h3={diag["h3_count"]} h4={diag["h4_count"]} '
              f'oversized={len(diag["oversized"])} pitfalls={diag["pitfalls"]} '
              f'runs={diag["runs"]} empty_body={diag["empty_body"]} '
              f'img_refs_rewritten={diag["img_refs"]} '
              f'iframe_stripped={diag["iframe_stripped"]} '
              f'svg_stripped={diag["svg_stripped"]}')
        ss = diag['special_sections']
        print('          intro_md=%s summary_md=%s' % (
            f'{ss["本章学习目的"]["lines"][0]}..{ss["本章学习目的"]["lines"][1]}'
            if '本章学习目的' in ss else 'null',
            f'{ss["本章总结"]["lines"][0]}..{ss["本章总结"]["lines"][1]}'
            if '本章总结' in ss else 'null'))
        print('          id drift: [%s] %s' % (status, detail))
    with open(os.path.join(tmpdir, 'ct_diag.json'), 'w', encoding='utf-8') as f:
        json.dump(all_diag, f, ensure_ascii=False, indent=1)
    print()
    print('--- oversized ### kept intact (NOT split) ---')
    for ch, d in all_diag.items():
        for u in d['oversized']:
            print(f'{ch} s{u["section"]:02d} "{u["point"]}" {u["span_lines"]} lines '
                  f'-> level {u["level"]}')
    print()
    print('--- skipped empty ## sections ---')
    for ch, d in all_diag.items():
        for u in d['skipped_empty_sections']:
            print(f'{ch} line {u["line"]:5d} "{u["title"]}" ({u["span_lines"]} lines)')
    print()
    print('--- pitfalls extracted (rule v2: list items) ---')
    for ch, d in all_diag.items():
        for p in d['pitfall_detail']:
            print(f'{ch} {p["point"]} "{p["title"]}" lines {p["lines"]}')
    if drift_seen:
        print()
        print('*** ID DRIFT ***')
        for ch, detail in drift_seen:
            print(f'  {ch}: {detail}')
    # 机器可读结论行——整轮输出的最后一行（多章时按章节顺序各一行），
    # 桌面端据此判断重建结果，不必去解析上面那一堆人类可读的诊断。
    print()
    for line in outcomes:
        print(line)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
