# -*- coding: utf-8 -*-
"""水彩版狐狸姿态图 -> 透明精灵图：泛洪去纸底、按色相去草地、去水印、补内部空洞、开运算清边、共用裁剪框。"""
import os
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "watercolor")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(SRC, "sprites")
os.makedirs(OUT, exist_ok=True)

FILES = ["fox-idle.png", "fox-blink.png", "fox-happy.png", "fox-sit.png",
         "fox-sleep.png", "fox-walk-a.png", "fox-walk-b.png"]

FLOOD_T = 62      # 纸底容差（水彩纸纹让底色不绝对均匀，需要宽松些）
SIDE = 512        # 输出画布
PAD = 6           # 裁剪留白
HOLE_R = 7        # 补洞用的闭运算半径：轮廓线上的缺口约 10px，取 7 刚好封住又不吃掉正常凹陷


def fill_holes(solid, radius=HOLE_R):
    """泛洪是从四角往里走的，轮廓线上一旦有缺口就会顺着缺口漏进去。

    狐狸尾巴尖是奶白色，和纸底几乎同色，泛洪从尾巴顶那道断掉的铅笔线上漏了进去，
    整块尾尖就被抠成了透明 —— 只剩一圈线。这里把"被轮廓围住、但和画布边缘不连通"
    的空洞找出来补回去：先闭运算把线缺口封住，再从边框泛洪，走不到的自由像素即为空洞。
    """
    side = radius * 2 + 1
    m = Image.fromarray((solid * 255).astype(np.uint8))
    closed = np.asarray(m.filter(ImageFilter.MaxFilter(side))
                         .filter(ImageFilter.MinFilter(side))) > 127
    free = ~closed

    h, w = free.shape
    seen = np.zeros((h, w), bool)
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            if free[y, x] and not seen[y, x]:
                seen[y, x] = True
                dq.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if free[y, x] and not seen[y, x]:
                seen[y, x] = True
                dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and free[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                dq.append((ny, nx))

    holes = (~solid) & (~seen)
    return holes


def key_bg(img: Image.Image) -> Image.Image:
    img = img.convert("RGB")
    w, h = img.size
    work = img.copy()
    SENT = (255, 0, 255)

    # 1) 四角泛洪吃掉奶油纸底
    for seed in [(2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)]:
        try:
            ImageDraw.floodfill(work, seed, SENT, thresh=FLOOD_T)
        except Exception:
            pass

    # 2) 底部整行撒种子，把被身体分开的草地残块全部吃掉
    #    这块土黄色与纸底三通道差值之和约 67，需要放宽容差；
    #    狐狸腿有深棕描边（与土黄差 >200），泛洪进不去
    for fy in (h - 2, h - 14, h - 26):
        for fx in range(2, w - 2, 10):
            seed = (fx, fy)
            if work.getpixel(seed) != SENT:
                try:
                    ImageDraw.floodfill(work, seed, SENT, thresh=95)
                except Exception:
                    pass

    rgba = img.convert("RGBA")
    px = rgba.load()
    wk = work.load()

    # 3) 脚下那块草皮是浅橄榄绿 + 米黄土色，与纸底不连通、泛洪到不了，
    #    按颜色直接在下部区域清除。狐狸腿/爪是深棕，胸口奶油白在 y<0.75 之外，均不受影响
    import colorsys
    for y in range(int(h * 0.70), h):
        for x in range(w):
            if wk[x, y] == SENT:
                continue
            r, g, b = px[x, y][:3]
            hh, ss, vv = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            greenish = 0.13 <= hh <= 0.45 and ss >= 0.055 and vv >= 0.33 and g >= r - 6
            sandy = abs(r - 243) < 15 and abs(g - 222) < 17 and abs(b - 194) < 19
            if greenish or sandy:
                px[x, y] = (0, 0, 0, 0)

    for y in range(h):
        for x in range(w):
            if wk[x, y] == SENT:
                px[x, y] = (0, 0, 0, 0)
                continue
            # 4) 右下角水印区
            if x > w * 0.855 and y > h * 0.855:
                px[x, y] = (0, 0, 0, 0)

    # 4) 补内部空洞：泛洪从轮廓线的缺口漏进了尾巴的白色尖，这里按原图补回来
    orig = np.asarray(img)
    solid = np.asarray(rgba.getchannel("A")) > 127
    holes = fill_holes(solid)
    if holes.any():
        arr = np.asarray(rgba).copy()
        arr[holes, :3] = orig[holes]
        arr[holes, 3] = 255
        rgba = Image.fromarray(arr, "RGBA")
        print("  补洞 %d px" % int(holes.sum()))

    # 5) 形态学开运算：抹掉残留的草屑与纸纹细边
    alpha = rgba.getchannel("A")
    alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))

    # 5) 轻微羽化边缘，避免硬锯齿
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.7))
    rgba.putalpha(alpha)
    return rgba


# 先全部抠出来，再用同一个包围盒统一切割，保证各姿态体型与脚底基准一致
cut = [key_bg(Image.open(os.path.join(SRC, f))) for f in FILES]

unions = None
for im in cut:
    bb = im.getchannel("A").getbbox()
    unions = bb if unions is None else (
        min(unions[0], bb[0]), min(unions[1], bb[1]),
        max(unions[2], bb[2]), max(unions[3], bb[3]),
    )

l, t, r, b = unions
l = max(0, l - PAD); t = max(0, t - PAD)
r = min(cut[0].width, r + PAD); b = min(cut[0].height, b + PAD)
side = max(r - l, b - t)

for fn, im in zip(FILES, cut):
    piece = im.crop((l, t, r, b))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    # 水平居中、底部对齐（脚底基准一致，切换姿态不会上下跳）
    canvas.alpha_composite(piece, ((side - piece.width) // 2, side - piece.height))
    canvas = canvas.resize((SIDE, SIDE), Image.LANCZOS)
    out = os.path.join(OUT, fn.replace(".png", "-t.png"))
    canvas.save(out)
    a = canvas.getchannel("A")
    hist = a.histogram()
    opaque = sum(hist[8:])
    print("ok", os.path.basename(out), "bbox", a.getbbox(), "覆盖%", round(opaque * 100.0 / (SIDE * SIDE), 1))

print("crop box used:", (l, t, r, b), "side", side)
