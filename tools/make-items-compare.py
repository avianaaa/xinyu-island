# -*- coding: utf-8 -*-
"""物件换新素材的前后对比：旧的四件扁平面 vs 新的统一水彩。"""
import os
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = lambda *p: os.path.join(BASE, *p)
FONT = 'C:/Windows/Fonts/msyh.ttc'

PAIRS = [
    (S('.shots', 'final2-1360x680.png'), '改之前：公告板 / 信箱 / 盆栽是早期的扁平面，观测台还是一台收音机'),
    (S('.shots', 'items-new-2.png'), '现在：四件统一成同一套水彩，观测台换成黄铜望远镜'),
]

W = 1000
top = 34
rows = []
for path, label in PAIRS:
    im = Image.open(path).convert('RGB')
    h = round(im.height * W / im.width)
    rows.append((im.resize((W, h), Image.LANCZOS), label))

H = sum(r[0].height for r in rows) + top * 2 + 10
c = Image.new('RGB', (W, H), (251, 246, 236))
d = ImageDraw.Draw(c)
f1 = ImageFont.truetype(FONT, 17)

y = 0
for im, label in rows:
    d.text((10, y + 9), label, font=f1, fill=(120, 100, 80))
    y += top
    c.paste(im, (0, y))
    y += im.height + 10

c.save(S('_preview', 'items-before-after.jpg'), quality=90)
print('saved', c.size)
