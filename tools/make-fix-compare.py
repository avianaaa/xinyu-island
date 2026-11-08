# -*- coding: utf-8 -*-
"""把"公告板翻转 + 狐狸尾巴补洞"的前后差异做成一张对比图。"""
import os
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = lambda *p: os.path.join(BASE, *p)
FONT = 'C:/Windows/Fonts/msyh.ttc'

BOX = (420, 255, 780, 560)      # 公告板 + 狐狸
SCALE = 1.55


def crop(path):
    im = Image.open(path).convert('RGB').crop(BOX)
    return im.resize((round(im.width * SCALE), round(im.height * SCALE)), Image.LANCZOS)


a = crop(S('.shots', 'real-sunny2.png'))
b = crop(S('.shots', 'final2-1360x680.png'))

W, H = a.size
top = 62
c = Image.new('RGB', (W * 2 + 36, H + top + 14), (251, 246, 236))
c.paste(a, (12, top))
c.paste(b, (W + 24, top))

d = ImageDraw.Draw(c)
f1 = ImageFont.truetype(FONT, 25)
f2 = ImageFont.truetype(FONT, 19)
d.text((14, 12), '改之前', font=f1, fill=(120, 104, 84))
d.text((14, 40), '公告板原朝向 · 尾巴尖被抠成透明', font=f2, fill=(140, 124, 104))
d.text((W + 26, 12), '现在', font=f1, fill=(148, 84, 58))
d.text((W + 26, 40), '公告板已翻转 · 尾巴白色尖补回来了', font=f2, fill=(148, 84, 58))

c.save(S('_preview', 'fix-board-tail.jpg'), quality=92)
print('saved', c.size)
