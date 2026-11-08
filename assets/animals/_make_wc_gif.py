# -*- coding: utf-8 -*-
"""生成行走循环预览 GIF（水彩版狐狸，两帧交替 + 轻微上下起伏）。"""
import os
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.join(BASE, "watercolor", "sprites")
OUT = os.path.join(BASE, "fox-walk-wc.gif")

a = Image.open(os.path.join(SP, "fox-walk-a-t.png")).convert("RGBA")
b = Image.open(os.path.join(SP, "fox-walk-b-t.png")).convert("RGBA")

S = 300
A = a.resize((S, S), Image.LANCZOS)
B = b.resize((S, S), Image.LANCZOS)

BG = (168, 186, 150)
frames = []
for img, dy in [(A, -3), (B, 0)]:
    canvas = Image.new("RGB", (S, S), BG)
    canvas.paste(img, (0, dy), img)
    frames.append(canvas)

frames[0].save(OUT, save_all=True, append_images=frames[1:],
               duration=220, loop=0, optimize=True)
print("ok", OUT, os.path.getsize(OUT) // 1024, "KB")
