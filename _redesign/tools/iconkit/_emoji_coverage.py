# -*- coding: utf-8 -*-
"""emoji 覆盖率自查：哪些符号还没有处置决定、哪些其实只出现在注释里。

跑法：python _redesign/tools/iconkit/_emoji_coverage.py
它回答两个问题：
1. 映射表里有没有漏登记（漏了就会在明细里显示"待判"）？
2. 每个符号"真正需要动界面"的次数是多少（注释里出现的不算工作量）？
"""
import io, sys, os, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _build_icons_docs as B
import _icons_meta as M

src = io.open(B.SRC, encoding="utf-8").read()
hits, span = B.scan(src)

by_em = collections.defaultdict(lambda: collections.Counter())
for h in hits:
    by_em[h["emoji"]][h["zone"]] += 1

print("JS 段 %d-%d 行；命中 %d 处 / %d 种" % (span[0], span[1], len(hits), len(by_em)))
print("")
print("%-4s %6s %6s %6s %6s   %s" % ("符号", "总计", "注释", "字符串", "标记", "决定"))
print("-" * 78)
unknown = 0
for em, zc in sorted(by_em.items(), key=lambda kv: -sum(kv[1].values())):
    dec = M.EMOJI_DECISION.get(em)
    if dec is None:
        unknown += 1
    print("%-4s %6d %6d %6d %6d   %s" % (
        em, sum(zc.values()), zc.get("comment", 0), zc.get("string", 0), zc.get("markup", 0),
        ("%s %s" % (dec[0], dec[1] or "")) if dec else "!! 未登记"))
print("-" * 78)
print("未登记: %d 种" % unknown)
