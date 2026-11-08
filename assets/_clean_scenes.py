# -*- coding: utf-8 -*-
"""去掉背景图右下角的 AI 生成水印：用其上方干净的同类像素镜像覆盖，并羽化接缝。"""
import os
from PIL import Image, ImageFilter

BASE = os.path.dirname(os.path.abspath(__file__))
SCENES = os.path.join(BASE, "scenes")
OUT = os.path.join(SCENES, "web")

FILES = ["scene-sunny.png", "scene-rainy.png", "scene-night.png"]

# 水印区域的相对范围（右下角）
W_FRAC = 0.19   # 宽，占整图比例
H_FRAC = 0.11   # 高
FEATHER = 14


def clean(img: Image.Image) -> Image.Image:
    img = img.convert("RGB")
    w, h = img.size
    bw, bh = int(w * W_FRAC), int(h * H_FRAC)
    x0, y0 = w - bw, h - bh

    # 从水印区正上方取同尺寸的干净块，垂直翻转后覆盖
    src = img.crop((x0, y0 - bh, x0 + bw, y0)).transpose(Image.FLIP_TOP_BOTTOM)
    src = src.filter(ImageFilter.GaussianBlur(1.2))

    # 羽化遮罩：越靠右/下越实，靠内边界渐变
    mask = Image.new("L", (bw, bh), 255)
    mp = mask.load()
    for y in range(bh):
        for x in range(bw):
            # 左边界与上边界渐变，避免硬接缝
            a = 255
            if x < FEATHER:
                a = min(a, int(255 * x / FEATHER))
            if y < FEATHER:
                a = min(a, int(255 * y / FEATHER))
            mp[x, y] = a

    img.paste(src, (x0, y0), mask)
    return img


os.makedirs(OUT, exist_ok=True)
for fn in FILES:
    im = Image.open(os.path.join(SCENES, fn))
    out = clean(im)
    # 统一导出为较高效的尺寸，宽度 1600 足够铺满桌面
    if out.width > 1600:
        out = out.resize((1600, round(out.height * 1600 / out.width)), Image.LANCZOS)
    path = os.path.join(OUT, fn.replace(".png", ".jpg"))
    out.save(path, "JPEG", quality=86, optimize=True, progressive=True)
    print("ok", fn, im.size, "->", out.size,
          round(os.path.getsize(path) / 1024), "KB")
print("done ->", OUT)
