# -*- coding: utf-8 -*-
"""从美术稿生成应用图标（多尺寸 .ico + 各尺寸 PNG）。

    python app/make-icon.py --src <美术稿路径>        # 默认用下面 DEFAULT_SRC

产物（写进 app/assets/）：
    icon-16/24/32/48/64/128/256.png   各尺寸，给 favicon 或别处用
    icon-512.png                      母版（圆角与 alpha 在这一层定下）
    icon.ico                          七帧合一，build.ps1 用它

为什么这么绕（每条都是量出来的，不是猜的）：
  1. 美术稿是 **JPEG（24bpp，没有 alpha）**，蓝色圆角方块外面有一圈约 100px 白边
     —— 所以必须裁掉白边。
  2. 方块**自己的四个角是白的**：蓝色圆弧在边长 r≈0.224 处，而白色一直延伸到
     r≈0.266。所以圆角半径必须**大于 0.266**，否则会留下一个月牙形的白角。
     （实测：用 0.225 时 256px 那帧还剩 83 个近白像素。）
  3. 裁到刚好压边会带上源图约 5px 的**抗锯齿过渡**，边缘会发灰；所以裁切点内缩
     6px 落在纯蓝区域。
  4. 圆角**在 512px 母版上**算好，小尺寸再从母版降采样 —— 这样边界永远是
     "蓝 × alpha" 混合，不可能把白混进来。半透明环还刻意往画面自己的蓝上靠，
     保证外缘渐隐的是蓝色而不是白色。
环境限制：这台机器没有 Pillow，且 System.Drawing 的 LockBits 会让 pythonnet
**致命崩溃**（不可捕获），所以只用普通的 Graphics 调用 + 逐像素 GetPixel。
"""
import sys, os, struct, argparse
sys.stdout.reconfigure(encoding='utf-8')
import clr
clr.AddReference('System.Drawing')
from System.Drawing import Bitmap, Image, Rectangle, Graphics, Color, GraphicsUnit
from System.Drawing.Drawing2D import InterpolationMode, CompositingQuality, \
    SmoothingMode, PixelOffsetMode
from System.Drawing.Imaging import ImageFormat, PixelFormat

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, 'assets')

# 默认美术稿（用户提供的那张 1254×1254 JPEG）
DEFAULT_SRC = (r'C:\Users\LENOVO\.dsh\attachments\v1\objects\3d'
               r'\3df09c880dfa2169eb164f80c763daf8b75c044a143502a03f4b230c8808aab6')

# ---- 下面这些数字是在那张 1254×1254 的原图上量出来的 ------------------------
CROP_X, CROP_Y, CROP_S = 106, 105, 1042   # 蓝色方块，内缩 6px 避开抗锯齿过渡
MASTER = 512                              # 母版边长
CORNER_RATIO = 0.268                      # > 实测白环外缘 0.266
FEATHER = 0.018                           # alpha 斜坡宽度（占边长比例）
EDGE_BLUE = (30, 80, 185)                 # 半透明环的底色（画面自己的蓝）
SIZES = [16, 24, 32, 48, 64, 128, 256]


def build(src_path, quiet=False):
    os.makedirs(ASSETS, exist_ok=True)
    src = Image.FromFile(src_path)
    if not quiet:
        print('美术稿 : %dx%d %s' % (src.Width, src.Height, src.PixelFormat))
        print('裁切   : (%d,%d) %dx%d   母版 %d   圆角 %.3f   斜坡 %.3f'
              % (CROP_X, CROP_Y, CROP_S, CROP_S, MASTER, CORNER_RATIO, FEATHER))

    crop = Bitmap(CROP_S, CROP_S, PixelFormat.Format32bppArgb)
    g = Graphics.FromImage(crop)
    g.DrawImage(src, Rectangle(0, 0, CROP_S, CROP_S), CROP_X, CROP_Y, CROP_S, CROP_S,
                GraphicsUnit.Pixel)
    g.Dispose()

    R = MASTER * CORNER_RATIO
    RIN = R - MASTER * FEATHER
    HS = MASTER / 2.0
    sc = float(CROP_S) / MASTER
    master = Bitmap(MASTER, MASTER, PixelFormat.Format32bppArgb)
    for y in range(MASTER):
        fy = y + 0.5 - HS
        dy = max(0.0, abs(fy) - (HS - R))
        for x in range(MASTER):
            fx = x + 0.5 - HS
            dx = max(0.0, abs(fx) - (HS - R))
            dist = (dx * dx + dy * dy) ** 0.5
            if dist >= R:
                master.SetPixel(x, y, Color.FromArgb(0, EDGE_BLUE[0], EDGE_BLUE[1], EDGE_BLUE[2]))
                continue
            a = 1.0 if dist <= RIN else (R - dist) / (R - RIN)
            c = crop.GetPixel(int(x * sc), int(y * sc))
            if a >= 0.999:
                master.SetPixel(x, y, Color.FromArgb(255, c.R, c.G, c.B))
            else:
                r = int(c.R * a + EDGE_BLUE[0] * (1 - a))
                gg = int(c.G * a + EDGE_BLUE[1] * (1 - a))
                b = int(c.B * a + EDGE_BLUE[2] * (1 - a))
                master.SetPixel(x, y, Color.FromArgb(int(round(a * 255)), r, gg, b))
    mp = os.path.join(ASSETS, 'icon-512.png')
    master.Save(mp, ImageFormat.Png)
    if not quiet:
        print('母版   : %s' % os.path.basename(mp))

    frames = {}
    for size in SIZES:
        bmp = Bitmap(size, size, PixelFormat.Format32bppArgb)
        gg = Graphics.FromImage(bmp)
        gg.SmoothingMode = SmoothingMode.AntiAlias
        gg.InterpolationMode = InterpolationMode.HighQualityBicubic
        gg.PixelOffsetMode = PixelOffsetMode.HighQuality
        gg.CompositingQuality = CompositingQuality.HighQuality
        gg.Clear(Color.Transparent)
        gg.DrawImage(master, Rectangle(0, 0, size, size))
        gg.Dispose()
        out = os.path.join(ASSETS, 'icon-%d.png' % size)
        bmp.Save(out, ImageFormat.Png)
        frames[size] = out
        if not quiet:
            print('  %-13s %dx%d' % (os.path.basename(out), size, size))

    ico = os.path.join(ASSETS, 'icon.ico')
    blobs = [open(frames[s], 'rb').read() for s in SIZES]
    with open(ico, 'wb') as fh:
        fh.write(struct.pack('<HHH', 0, 1, len(SIZES)))     # reserved / type=icon / count
        off = 6 + 16 * len(SIZES)
        for size, data in zip(SIZES, blobs):
            wh = 0 if size == 256 else size                 # ICO 里 0 表示 256
            fh.write(struct.pack('<BBBBHHII', wh, wh, 0, 0, 1, 32, len(data), off))
            off += len(data)
        for data in blobs:
            fh.write(data)
    if not quiet:
        print()
        print('图标   : %s  %d 字节  %d 帧' % (ico, os.path.getsize(ico), len(SIZES)))
    return ico


def main():
    ap = argparse.ArgumentParser(description='从美术稿生成应用图标')
    ap.add_argument('--src', default=DEFAULT_SRC, help='美术稿路径（默认用内置的那张）')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    if not os.path.isfile(a.src):
        print('找不到美术稿：%s' % a.src, file=sys.stderr)
        return 2
    build(a.src, a.quiet)
    return 0


if __name__ == '__main__':
    sys.exit(main())
