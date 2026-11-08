# -*- coding: utf-8 -*-
"""v2 物件（无地面版）抠图：纯色底泛洪即可，输出透明 PNG。

v2 相比原版去掉了脚下的草皮与投影，底色是均匀的奶油纸色，
所以抠图退化成最简单的情况：四角泛洪 + 去水印 + 收边。
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "v2")
OUT = os.path.join(BASE, "sprites")
os.makedirs(OUT, exist_ok=True)

# 生成时的长文件名 -> 规范名
MAP = {
    "Keep_the_EXACT_same_mailbox__s_2026-11-02T12-21-09.png": "item-mailbox.png",
    "Keep_the_EXACT_same_retro_radi_2026-11-02T12-19-16.png": "item-radio.png",
    "Keep_the_EXACT_same_still_life_2026-11-02T12-19-46.png": "item-plant.png",
    "Keep_the_EXACT_same_notice_boa_2026-11-02T12-20-26.png": "item-board.png",
    "Keep_the_EXACT_same_cozy_cabin_2026-11-02T12-20-47.png": "item-cabin.png",
}

FLOOD_T = 76   # 需要足够大才能吃掉纸底的白斑（与纸底差 73）；
              # 泛洪受主体描边阻挡，不会渗进信封等浅色部件
LONG = 512
PAD = 4


def key_bg(img: Image.Image) -> Image.Image:
    img = img.convert("RGB")
    w, h = img.size
    work = img.copy()
    SENT = (255, 0, 255)

    for seed in [(2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)]:
        try:
            ImageDraw.floodfill(work, seed, SENT, thresh=FLOOD_T)
        except Exception:
            pass

    rgba = img.convert("RGBA")
    px = rgba.load()
    wk = work.load()
    for y in range(h):
        for x in range(w):
            if wk[x, y] == SENT:
                px[x, y] = (0, 0, 0, 0)
            elif x > w * 0.855 and y > h * 0.855:   # 水印
                px[x, y] = (0, 0, 0, 0)

    a = rgba.getchannel("A")
    a = a.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    a = a.filter(ImageFilter.GaussianBlur(0.6))
    rgba.putalpha(a)
    return rgba


def drop_small_blobs(alpha: Image.Image, min_area=500) -> Image.Image:
    """清掉散落的纸底白斑。

    白斑与纸底差 73，靠泛洪容差清会误伤信封等浅色部件；
    改用连通域面积过滤：只保留足够大的块。收音机的细天线虽细，
    但面积与本体连通，不受影响。
    """
    b = alpha.point(lambda v: 255 if v > 8 else 0)
    while True:
        arr = np.array(b)
        ys, xs = np.where(arr == 255)
        if len(xs) == 0:
            break
        ImageDraw.floodfill(b, (int(xs[0]), int(ys[0])), 128, thresh=0)
        arr = np.array(b)
        area = int((arr == 128).sum())
        arr[arr == 128] = 200 if area >= min_area else 0
        b = Image.fromarray(arr)

    keep = np.array(b) == 200
    out = np.array(alpha).copy()
    out[~keep] = 0
    return Image.fromarray(out)


rows = []
for src_name, out_name in MAP.items():
    p = os.path.join(SRC, src_name)
    if not os.path.exists(p):
        print("MISSING", src_name)
        continue
    cut = key_bg(Image.open(p))
    bb = cut.getchannel("A").getbbox()
    l, t, r, b = bb
    l = max(0, l - PAD); t = max(0, t - PAD)
    r = min(cut.width, r + PAD); b = min(cut.height, b + PAD)
    piece = cut.crop((l, t, r, b))

    k = LONG / max(piece.width, piece.height)
    piece = piece.resize((max(1, round(piece.width * k)),
                          max(1, round(piece.height * k))), Image.LANCZOS)

    out = os.path.join(OUT, out_name.replace(".png", "-t.png"))
    piece.save(out)
    rows.append((out_name, piece.size[0], piece.size[1]))

print("%-16s %-10s ratio  (CSS 建议宽度 px, 舞台宽 1080)" % ("name", "size"))
for n, w_, h_ in rows:
    print("%-16s %-10s %.2f" % (n, "%dx%d" % (w_, h_), w_ / h_))
print("->", OUT)
