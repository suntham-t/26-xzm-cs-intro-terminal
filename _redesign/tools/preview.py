#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""preview.py -- 生成预览页，给分头写 CSS 的人自查用。

为什么需要：app 只服务 web/index.html 一个入口，多人同时往那里拼装会互相踩。
做法：按当前所有分片拼一份 HTML，写到 web/_pv<NN>.html（同一个服务、同源，
      /content 之类的绝对路径照常可用），再交给 headless Chrome 截图。

★ 预览页比正式产物多一行 <base href="/">：预览挂在 /web/ 下面，
  相对路径会被解析成 /web/content/... → 404；正式产物在站点根，不需要。

用法：
  python _redesign/tools/preview.py --part 30
  -> http://127.0.0.1:8800/web/_pv30.html
"""
import sys, argparse, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import apply as A

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="30")
    ap.add_argument("--port", default="8800")
    a = ap.parse_args()
    css, _used = A.build_css()
    html = A.build_html(css)
    html = html.replace("<head>", '<head>\n<base href="/">', 1)
    out = A.ROOT / "web" / ("_pv%s.html" % a.part)
    out.write_text(html, encoding="utf-8", newline="\n")
    print("预览页: http://127.0.0.1:%s/web/_pv%s.html" % (a.port, a.part))
    print("        (%.1f KB)  %s" % (len(html.encode()) / 1024, out))

if __name__ == "__main__":
    main()
