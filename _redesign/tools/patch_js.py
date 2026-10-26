#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""patch_js.py -- 从"未改动的原始 JS"出发，按顺序套用 patches/*.json，产出 src/app.js。

为什么这么做：直接在 src/app.js 上手改，任何一处改动都会让后续补丁的锚点漂移，
而且改错了没法回滚。这里每次都从 ref/old-app.js（git HEAD 的干净底本）重新生成：
补丁是幂等的、可逐条 review 的、失败就整体不写。

补丁文件两种形态：
  1) {"id","note","old":"必须出现恰好一次的原文","new":"替换成什么"}
  2) {"id","note","anchor":"锚点","insert_file":"相对 _redesign 的文件"}  # 引入大块内容（图标库）

用法：
  python _redesign/tools/patch_js.py            # 生成 src/app.js
  python _redesign/tools/patch_js.py --list     # 只列补丁，不写文件
"""
import json, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
RD   = ROOT / "_redesign"
SRC  = RD / "ref" / "old-app.js"
OUT  = RD / "src" / "app.js"
PDIR = RD / "patches"

def main():
    listing = "--list" in sys.argv
    text = SRC.read_text(encoding="utf-8")
    files = sorted(PDIR.glob("*.json")) if PDIR.exists() else []
    if not files:
        print("没有补丁，直接拷贝底本")
        if not listing:
            OUT.write_text(text, encoding="utf-8")
        return 0
    ok, applied = True, 0
    for f in files:
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print("  [BAD] %s 不是合法 JSON: %s" % (f.name, e)); ok = False; break
        pid = p.get("id") or f.stem
        anchor = p.get("anchor", "")
        if p.get("insert_file"):
            ipath = pathlib.Path(p["insert_file"])
            if not ipath.is_absolute():
                ipath = RD / ipath
            if not anchor:
                print("  [BAD] %s: 缺 anchor" % pid); ok = False; break
            if text.count(anchor) != 1:
                print("  [BAD] %s: anchor 出现 %d 次（必须恰好 1 次）" % (pid, text.count(anchor))); ok = False; break
            if not ipath.exists():
                print("  [BAD] %s: insert_file 不存在 %s" % (pid, ipath)); ok = False; break
            ins = ipath.read_text(encoding="utf-8").strip("\n")
            text = text.replace(anchor, anchor + "\n\n" + ins + "\n", 1)
            applied += 1
            if listing:
                print("  [ok ] %-34s %s" % (f.name, p.get("note", "")))
            continue
        old, new = p.get("old", ""), p.get("new", "")
        if not old:
            print("  [BAD] %s: 缺 old" % pid); ok = False; break
        n = text.count(old)
        if n == 0:
            print("  [BAD] %s: 锚点找不到（顺序错了？被前一个补丁改掉了？）" % pid); ok = False; break
        if n > 1:
            print("  [BAD] %s: 锚点出现 %d 次（必须恰好 1 次）" % (pid, n)); ok = False; break
        text = text.replace(old, new, 1)
        applied += 1
        if listing:
            print("  [ok ] %-34s %s" % (f.name, p.get("note", "")))
    if not ok:
        print("\n★ 补丁链断了：src/app.js 未写入")
        return 1
    if listing:
        print("\n共 %d 个补丁，产物 %d 字节" % (applied, len(text)))
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print("已生成 %s（%d 个补丁，%d 行）" % (OUT, applied, text.count(chr(10)) + 1))
    return 0

if __name__ == "__main__":
    sys.exit(main())
