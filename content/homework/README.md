# 作业题解析内容层（`content/homework/`）

给「📝 作业」功能提供数据。**解析本身由终端运行时接 DeepSeek 现场生成**，所以这里的定位是：

- **题面 / 样例 / 统计 / 边界用例** —— AI 的**输入**和**验收标准**，必须准，一字不能歪；
- **`analysis_md` / `solution_code`** —— ① 离线兜底（没配 key、断网时直接显示）② few-shot 范例（塞进系统提示词）。

```
content/homework/
├── hw1.json        ← 作业一（6 题），UI 直接读这个
├── _fetch-oj.py    ← 抓取 + 实测脚本（可复跑的生产工具）
└── README.md       ← 本文
```

OJ：<http://xzmdsa.openjudge.cn/>（计概&数算B-谢正茂班），题面全是 UTF-8，**不需要登录**。

---

## 1. 数据契约（冻结，UI 按这个写）

`hw1.json` 顶层：`id` / `title` / `oj_url` / `fetched_at` / `deadline` / `problems[]`。

每题字段：

| 字段 | 说明 |
| --- | --- |
| `no` / `title` / `oj_url` | 题号、标题、题目页 URL |
| `global_id` | 页面右侧「全局题号」，字符串；拿不到是 `null` |
| `limits` | `{ "time": "1000ms", "memory": "65536kB" }` |
| `statement_md` | 题面 markdown（`## 描述` / `## 输入` / `## 输出` / `## 提示` / `## 来源`），**原文不改写** |
| `sample_in` / `sample_out` | 样例，**原样搬运**，只把 `\r\n`、`\r` 规范成 `\n` 并保证结尾有一个 `\n` |
| `extra_cases[]` | 手写的边界用例 `{in, out, why}`，`out` 是推导并实测过的 |
| `analysis_md` | 中文解析（离线兜底 + few-shot） |
| `pitfalls[]` | 3~5 条，每条都能落到一个具体输入上 |
| `solution_code` | 参考代码，**只用标准库**，实测过 sample + 全部 `extra_cases` |
| `points[]` | 相关知识点 id（`content/notes/_point-ids.txt` 里的 `chNN-sMM-pKK`） |
| `stats` | `{submitted, tried, passed}`，对应页面上的提交次数/尝试人数/通过人数；拿不到是 `null`，**不编** |
| `verified` | 实测结果 `{"sample": "pass"\|"fail", "extra_passed": N, "extra_total": N}`；没跑成是 `null` |

渲染器只支持 标题 / 列表 / 代码块 / 行内代码 / 粗体 / 链接 / 引用块，所以解析里**不用表格**。

### `statement_md` 的换行规则（AI 要读它，所以这里不能糊）

页面上 `</p>` / `</div>` 和连续两个 `<br>` 是**真的分段**，单个 `<br>` 只是**句内折行**，
要看上下文：上一段以句号/分号结尾、或下一段是 `1.` `2.` 这种编号才断开，否则用空格接回同一行。
第 5 题题面里的 `给定k（1<br/> < k < 100）` 就是被这条规则救回来的
（不然会被断成两段，AI 读到的就是残句）；第 3 题提示里 `1.…;<br />2.…` 仍是一行一条。

第 6 题描述里那张「字母 -> 数字」对照表在页面上是一行一个 `<div>`，会被包进 ``` 代码块，
否则 markdown 渲染器会把它们粘成一段。

### 一个必须知道的细节：第 3 题的样例输出是「制表符被展开后的样子」

第 3 题要求列之间用制表符 `\t`，但 OJ 页面上的样例输出存的是**空格**
（制表符被按 8 列宽度展开写死了）。所以：

- `sample_out` 里是空格 —— 因为契约要求「原文，一字不改」，我们不改写它；
- `extra_cases[].out` 和 `solution_code` 里是 `\t` —— 那才是真正要提交的格式。

对照关系（`我的输出.expandtabs(8) == 页面样例`，逐字符相等）：

```
页面样例: 'Table   Beef-Burrito    Ceviche Fried-Chicken   Water'
程序输出: 'Table\tBeef-Burrito\tCeviche\tFried-Chicken\tWater'
```

**UI 建议**：第 3 题的样例展示可以提示一句「网页样例里的对齐是制表符展开的结果，实际输出用 `\t`」，
或者把 `sample_out` 的连续空格按 8 列还原成 `\t` 再显示。其余 5 题没有这个问题。

第 6 题的样例输出末尾还有一个多余空格（`888-4567 3 `），也是原样保留的——判题时行尾空白无意义。

---

## 2. 加一份新作业

```powershell
cd D:\opencode\course-terminal\content\homework
# 1) 先看看有哪些题集（可选，加 --with-archive 连归档页一起列）
python _fetch-oj.py --list-sets

# 2) 抓新作业（题面会自动填好，解析部分脚本会在 stderr 提示缺哪几题）
python _fetch-oj.py --set 2026ci13hw2 --out hw2.json --id hw2 --title 作业二
```

然后给 `_fetch-oj.py` 里的 `AUTHORED` 补内容——它按**题号**索引，每题要给
`title`（只用来报警，题目被换掉时会提示）、`extra_cases`、`solution_code`、`points`，
以及 `analysis_md` / `pitfalls`（离线兜底 + few-shot，**够用就行，不用精雕**）。
改完再跑一次第 2 步就合并进 JSON 了。

> 手写内容为什么放在脚本里而不是单独的 json？为了让 `content/homework/` 只有约定的三个文件，
> 也为了让「抓题面」和「配解析」在一次运行里合并，重跑不会覆盖手写内容。

**新作业没有 `AUTHORED` 也能跑**：脚本会把 `analysis_md` 等留空、`verified` 记 `null`，
并在 stderr 提示缺哪几题——先让题面进 JSON，解析可以后补。
运行时生成的解析不依赖这里，所以新题当天就能用。

### `extra_cases` 怎么写（现在是「验 AI 代码」的测试集，最重要）

OJ 的样例普遍太弱（第 1 题只给 `2006 -> N`，第 2 题只给 `20 -> 5 10`），
踩坑全在样例没覆盖的分支上。**每题 4~6 条，总数 ≥ 25**，优先覆盖：

1. 最小 / 最大输入；
2. **样例没走到的分支**，尤其是「输出 `0 0`」「无解」「No duplicates.」这类；
3. 临界值（整百年、0、1、边界 ±1）；
4. 题目明确写了约束的极端情况（`k = 99`、桌号 `500`、`n` 的上下界）。

`why` 写给人看，一句话说清「这条在验什么」。`out` 必须自己推过、并且跑通过，**不确定就别写**。

### 参考代码实测（`verified`）

`_fetch-oj.py` 默认会把每份 `solution_code` 拿到**本地运行器**上真跑一遍
（sample + 全部 `extra_cases`），把结果写进 `verified`：

```powershell
# 先起服务，再抓；脚本会自己调 /run 实测
cd D:\opencode\course-terminal
python app\main.py --no-window --port 8896      # 另开一个窗口
cd content\homework
python _fetch-oj.py --set 2026ci13hw1 --out hw1.json --id hw1 --title 作业一
```

- 某个用例没过 → 脚本在 stderr 打印 `in / 期望 / 实际 / kind`，并且 `verified` 里就是真实数字（**不粉饰**）；
- 运行器没起来 → 打印提示，`verified` 写 `null`（抓题面不受影响）；
- `--verify-url` 换地址，`--no-verify` 完全跳过实测。

### 确定性

`fetched_at` 在输出文件已存在时**沿用旧值**（除非显式 `--fetched-at`），
所以题面没变的情况下反复抓，`hw1.json` 字节级一致，可以直接 diff：

```powershell
python _fetch-oj.py --set 2026ci13hw1 --out hw1.json --id hw1 --title 作业一
python _fetch-oj.py --set 2026ci13hw1 --out hw1.json --id hw1 --title 作业一
# 两次打印的 sha256(json) 相同
```

其它选项：`--base`（换站点）、`--fetched-at 2026-09-26T15:00:00+08:00`、`--list-sets --with-archive`。
抓取失败会自动重试 3 次（递增退避），全失败才抛错。

---

## 3. 独立复测：不信任脚本自己的结论

脚本会写 `verified`，但下面这段是**独立**再跑一遍的（对着 JSON 里的 `solution_code` 逐条断言）：

```python
import json, urllib.request

def run(code, stdin):
    q = urllib.request.Request("http://127.0.0.1:8896/run",
        data=json.dumps({"code": code, "stdin": stdin}).encode(),
        headers={"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(q, timeout=60).read())
    return d["kind"], d["stdout_final"]

def clean(s):
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in s.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)

hw = json.load(open(r"content\homework\hw1.json", encoding="utf-8"))
for p in hw["problems"]:
    for label, stdin, want in ([("sample", p["sample_in"], p["sample_out"])]
                               + [("extra%d" % i, c["in"], c["out"])
                                  for i, c in enumerate(p["extra_cases"], 1)]):
        kind, got = run(p["solution_code"], stdin)
        # 第 3 题的页面样例是制表符展开过的，比较前先 expandtabs(8)
        ok = clean(got).expandtabs(8) == clean(want).expandtabs(8)
        print(p["no"], label, kind, "OK" if ok else "FAIL")
        assert ok, (p["no"], label, repr(got), repr(want))
```

（运行器端口跟着 `--verify-url` 改。脚本默认就用 `http://127.0.0.1:8896`。）

比较规则：两边都做 `\r\n -> \n`、去掉行尾空格、去掉末尾空行；**行内空格保留**，
并且额外按 `expandtabs(8)` 对齐一次（就是为了第 3 题那个制表符）。

注意运行器是**逐行追踪**的教学引擎（`max_steps = 5000`），所以 `extra_cases` 的规模都刻意压小，
避免追到一半被 `aborted`。

---

## 4. 这个 OJ 上还有哪些题集

首页（`http://xzmdsa.openjudge.cn/`）只列「正在进行 + 计划中 + 最近 5 个已结束」，全部归档在
`/contests/past`（3 页，42 个）。当前能看到：

**正在进行**

- 2026计概13班-作业一（Python基础） — <http://xzmdsa.openjudge.cn/2026ci13hw1/> （本目录，6 题，截止 2026-10-10 13:00）

**已结束（计概 B 班，最近的）**

- 2026计概小测一补测（水平摸底） — <http://xzmdsa.openjudge.cn/2026citest11/>
- 2026计概小测一（水平摸底） — <http://xzmdsa.openjudge.cn/2026citest1/>
- 2025秋季计概B-13期末机考模拟 — <http://xzmdsa.openjudge.cn/2025ci13mock/>
- 2025秋季计概B-13小测5 / 4 / 3 — `/cintro2025test5/`、`/cintro2025test4/`、`/cintro2025test3/`
- 2025计概B13班期末机考 — <http://xzmdsa.openjudge.cn/jg2025qm/>
- 2025计概小测二 / 小测一（水平摸底） — `/2025citest2/`、`/2025citest1/`
- Python基础技能小测 — <http://xzmdsa.openjudge.cn/pythonbasic/>

**已结束（数算 B 班，同一位老师，2026 春季）**

- 作业六（图及算法） `/2026dsahw6/`、作业五（树及算法） `/2026dsahw5/`、作业四（排序与查找） `/2026dsahw4/`、
  作业三（递归与动规） `/2026dsahw3/`、作业二（线性表） `/2026dsahw2/`
- 2026年数算B-14期末机考 `/2026dsafinal/`
- 小测：树及算法 `/2026dsaquiz6tree/`、排序与查找 `/2026dsaquiz5sortfind/`、
  递归与动规 `/2026dsaquiz4rcdp/`、线性表 `/2026dsaquiz3liner/`、Python基础 `/2026dsaquiz2python/`、
  水平摸底 `/2026dsaquiz1/`（各有一个 `...review` 复习场）

以后要加哪一份，直接
`python _fetch-oj.py --set <slug> --out <hwN>.json --id hwN --title <标题>`。
