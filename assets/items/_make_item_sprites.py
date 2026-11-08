# -*- coding: utf-8 -*-
"""物件抠图：泛洪去奶油纸底 + 去脚下草皮 + 去水印，输出透明 PNG。

输出不统一画布尺寸，而是各自按内容裁剪后把最长边缩到 512，
保留长宽比，前端据此摆放（物件大小差异本身就是信息：木屋比信箱大）。
"""
import os
import colorsys
from PIL import Image, ImageDraw, ImageFilter

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "sprites")
os.makedirs(OUT, exist_ok=True)

FILES = ["item-mailbox.png", "item-radio.png", "item-plant.png",
         "item-board.png", "item-cabin.png"]

FLOOD_T = 26      # 纸底容差（物件底色比狐狸那套更均匀，不需要放宽）
BOTTOM_T = 40     # 底部草地容差
LONG = 512        # 输出最长边
PAD = 4

# 每个物件脚下都踩着一小块草皮，水彩边缘与物件连在一起，按颜色清不干净。
# 这块草皮只在最底部一条，直接按比例切掉 —— 物件于是变成"插进地里"的形态，
# 放进场景时底部正好落地，柱子/屋基被草地边缘遮住，是自然的。
CUT_BOTTOM = {
    "item-mailbox.png": 0.115,
    "item-radio.png":   0.105,
    "item-plant.png":   0.105,
    "item-board.png":   0.115,
    "item-cabin.png":   0.100,
}


def key_bg(img: Image.Image) -> Image.Image:
    img = img.convert("RGB")
    w, h = img.size
    work = img.copy()
    SENT = (255, 0, 255)

    # 1) 四角泛洪去纸底
    for seed in [(2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)]:
        try:
            ImageDraw.floodfill(work, seed, SENT, thresh=FLOOD_T)
        except Exception:
            pass

    # 2) 底部整行种子，清掉物件脚下那块草皮
    for fy in (h - 2, h - 12, h - 24):
        for fx in range(2, w - 2, 12):
            seed = (fx, fy)
            if work.getpixel(seed) != SENT:
                try:
                    ImageDraw.floodfill(work, seed, SENT, thresh=BOTTOM_T)
                except Exception:
                    pass

    rgba = img.convert("RGBA")
    px = rgba.load()
    wk = work.load()

    # 3) 底部兜底：物件脚下那块草皮是橄榄黄 (191,180,131)，色相 ≈0.136，
    #    与木头的暖棕（色相 0.05-0.09）区分得开。只对最底部一条带生效，避免误伤屋顶与木墙
    for y in range(int(h * 0.82), h):
        for x in range(w):
            if wk[x, y] == SENT:
                continue
            r, g, b = px[x, y][:3]
            hh, ss, vv = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            if 0.125 <= hh <= 0.50 and ss >= 0.12 and vv >= 0.30:
                px[x, y] = (0, 0, 0, 0)

    # 4) 统一落地：水印区 + 边界
    for y in range(h):
        for x in range(w):
            if wk[x, y] == SENT:
                px[x, y] = (0, 0, 0, 0)
            elif x > w * 0.855 and y > h * 0.855:
                px[x, y] = (0, 0, 0, 0)

    # 5) 开运算清掉细碎草屑，再轻羽化
    a = rgba.getchannel("A")
    a = a.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    a = a.filter(ImageFilter.GaussianBlur(0.7))
    rgba.putalpha(a)
    return rgba


print("name                 bbox                out        ratio   cov%")
for fn in FILES:
    src = Image.open(os.path.join(BASE, fn))
    cut = key_bg(src)

    bb0 = cut.getchannel("A").getbbox()
    # 切掉底部那条草皮（按内容高度算，不是按画布高度）
    n = int((bb0[3] - bb0[1]) * CUT_BOTTOM.get(fn, 0.0))
    if n:
        a = cut.getchannel("A")
        ImageDraw.Draw(a).rectangle([0, bb0[3] - n, cut.width, cut.height], fill=0)
        cut.putalpha(a)

    bb = cut.getchannel("A").getbbox()
    l, t, r, b = bb
    l = max(0, l - PAD); t = max(0, t - PAD)
    r = min(cut.width, r + PAD); b = min(cut.height, b + PAD)
    piece = cut.crop((l, t, r, b))

    # 最长边缩到 512，保持长宽比
    k = LONG / max(piece.width, piece.height)
    piece = piece.resize((max(1, round(piece.width * k)),
                          max(1, round(piece.height * k))), Image.LANCZOS)

    out = os.path.join(OUT, fn.replace(".png", "-t.png"))
    piece.save(out)

    alpha = piece.getchannel("A")
    opaque = sum(alpha.histogram()[8:])
    print("%-20s %-18s %-10s %.2f   %.1f" % (
        fn, str(bb), "%dx%d" % piece.size,
        piece.width / piece.height,
        opaque * 100.0 / (piece.width * piece.height)))

print("->", OUT)
