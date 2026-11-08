# -*- coding: utf-8 -*-
"""把「改动前 / 改动后」两张合成图并排贴起来，方便一眼看出差异。"""
import os

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(BASE, '.shots')
OUT = os.path.join(BASE, '_preview', 'path-compare.jpg')

a = Image.open(os.path.join(SHOTS, '_before.png'))
b = Image.open(os.path.join(SHOTS, 'layout-desktop.png'))
W, H = a.size
f = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 26)

c = Image.new('RGB', (W * 2 + 24, H + 56), (251, 246, 236))
c.paste(a, (8, 48))
c.paste(b, (W + 16, 48))
d = ImageDraw.Draw(c)
d.text((10, 10), '之前：底图把石子路切掉了', font=f, fill=(94, 80, 64))
d.text((W + 18, 10), '现在：石子路回到左下角，狐狸活动区放大到整片空草', font=f, fill=(148, 84, 58))
c.save(OUT, quality=90)
print('saved', OUT)
