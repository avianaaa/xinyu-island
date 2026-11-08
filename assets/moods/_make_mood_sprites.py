"""五档心情表情抠图：泛洪去纸底，保持 512 全画布（五档位置天然对齐）。"""
import os
from PIL import Image, ImageDraw, ImageFilter

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "sprites")
os.makedirs(OUT, exist_ok=True)

FLOOD_T = 72   # 纸底有渐变纹理；泛洪受铅笔描边阻挡，不会渗进奶油色的第 3 档身体
SIDE = 512
SENT = (255, 0, 255)

for i in range(1, 6):
    src = Image.open(os.path.join(BASE, f"mood-{i}.png")).convert("RGB")
    w, h = src.size
    work = src.copy()

    # 四角 + 四边中点撒种子，覆盖纸底渐变
    seeds = [(3, 3), (w - 4, 3), (3, h - 4), (w - 4, h - 4),
             (w // 2, 3), (w // 2, h - 4), (3, h // 2), (w - 4, h // 2)]
    for s in seeds:
        if work.getpixel(s) != SENT:
            try:
                ImageDraw.floodfill(work, s, SENT, thresh=FLOOD_T)
            except Exception:
                pass

    rgba = src.convert("RGBA")
    px = rgba.load()
    wk = work.load()
    for y in range(h):
        for x in range(w):
            if wk[x, y] == SENT:
                px[x, y] = (0, 0, 0, 0)

    # 边缘轻微羽化，去掉水彩硬锯齿
    rgba.putalpha(rgba.getchannel("A").filter(ImageFilter.GaussianBlur(0.8)))

    rgba = rgba.resize((SIDE, SIDE), Image.LANCZOS)
    out = os.path.join(OUT, f"mood-{i}-t.png")
    rgba.save(out)
    op = sum(rgba.getchannel("A").histogram()[8:])
    print(f"ok mood-{i}", rgba.size, "覆盖%", round(op * 100.0 / (SIDE * SIDE), 1))

print("done ->", OUT)
