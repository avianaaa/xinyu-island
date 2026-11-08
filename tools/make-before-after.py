# -*- coding: utf-8 -*-
"""把用户的旧截图和现在的真实截图并排，方便对比「网页 vs 预览」。"""
import os

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OLD = r'C:\Users\Mayyy\.workbuddy\clipboard-images\clipboard-2026-11-02T15-11-34-104Z-009175fa.jpg'
NEW = os.path.join(BASE, '.shots', 'real-sunny2.png')
OUT = os.path.join(BASE, '_preview', 'before-after.jpg')

W = 760
f = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 24)


def fit(p):
    im = Image.open(p).convert('RGB')
    return im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)


a, b = fit(OLD), fit(NEW)
H = max(a.height, b.height)
c = Image.new('RGB', (W * 2 + 30, H + 52), (251, 246, 236))
c.paste(a, (8, 46))
c.paste(b, (W + 22, 46))
d = ImageDraw.Draw(c)
d.text((10, 10), '改之前：背景按 cover 缩放、狐狸按窗口宽算 → 比例和预览对不上', font=f, fill=(120, 96, 74))
d.text((W + 24, 10), '现在：1.6 固定舞台，和预览同一套比例', font=f, fill=(148, 84, 58))
c.save(OUT, quality=90)
print('saved', OUT)
