# -*- coding: utf-8 -*-
"""生成三套背景的三联对比图，标注海面占比。"""
import os
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(BASE, "scenes", "web")

CREAM = (251, 246, 236)
INK = (90, 76, 62)
SUB = (140, 124, 106)

FILES = [
    ("scene-sunny.jpg", "晴天 · sunny", "海 ≈ 上方 1/3"),
    ("scene-rainy.jpg", "雨天 · rainy", "海面有细波纹"),
    ("scene-night.jpg", "夜晚 · night", "月光带 + 萤火"),
]

TW = 640          # 每张缩略宽
GAP = 26
PAD = 40


def font(size, bold=False):
    cands = [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]
    for c in cands:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


im0 = Image.open(os.path.join(WEB, FILES[0][0]))
ratio = TW / im0.width
TH = round(im0.height * ratio)

W = PAD * 2 + TW * 3 + GAP * 2
H = PAD + 58 + TH + 46 + 26

sheet = Image.new("RGB", (W, H), CREAM)
d = ImageDraw.Draw(sheet)
f_title = font(26, True)
f_sub = font(17)
f_small = font(15)

d.text((PAD, PAD - 6), "心屿 · 三套背景（海面比例已加大）", fill=INK, font=f_title)

top = PAD + 58
for i, (fn, name, note) in enumerate(FILES):
    im = Image.open(os.path.join(WEB, fn)).convert("RGB").resize((TW, TH), Image.LANCZOS)
    x = PAD + i * (TW + GAP)
    sheet.paste(im, (x, top))
    d.rectangle([x, top, x + TW - 1, top + TH - 1], outline=(214, 202, 184))
    d.text((x + 2, top + TH + 12), name, fill=INK, font=f_sub)
    d.text((x + 2, top + TH + 32), note, fill=SUB, font=f_small)

sheet.save(os.path.join(BASE, "scenes-preview.png"))
print("ok", sheet.size)
