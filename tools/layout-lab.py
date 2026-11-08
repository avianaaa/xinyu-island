# -*- coding: utf-8 -*-
"""布局方案实验室 v2。

和 v1 的区别：每个元素可以单独给融合强度（tone）。
一刀切降饱和会把主体树调成灰疙瘩——近景要实、远景才该淡。

跑法：
    python tools/layout-lab.py
输出：
    _preview/lay-{H,I,J}.jpg   单套大图
    _preview/lay-compare.jpg   并排对比
"""
import os
import sys
import importlib.util
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
sys.path.insert(0, HERE)

spec = importlib.util.spec_from_file_location('lab', os.path.join(HERE, 'bg-lab.py'))
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)

W, H = 1440, 900
lab.W, lab.H = W, H
OUT = os.path.join(BASE, '_preview')
SCENE = os.path.join(OUT, 'scene-s2.jpg')

P = lambda s: os.path.join(BASE, s)
CAB = P('assets/items/sprites/item-cabin-t.webp')
TREE = P('assets/decor/tree-a-t.webp')
BUSH = P('assets/decor/bush-a-t.webp')
BOARD = P('assets/items/sprites/item-board-t.png')
MAIL = P('assets/items/sprites/item-mailbox-t.png')
RADIO = P('assets/items/sprites/item-radio-t.png')
PLANT = P('assets/items/sprites/item-plant-t.png')
FOX = P('assets/animals/watercolor/sprites/fox-idle-t.png')


def font(size=16):
    for f in ('msyh.ttc', 'simhei.ttf', 'arial.ttf'):
        try:
            return ImageFont.truetype('C:/Windows/Fonts/' + f, size)
        except Exception:
            continue
    return ImageFont.load_default()


# (kind, src, x, y脚底, 高度, flip, 融合强度 0=原色 1=完全融进背景)
PLANS = {
    'H': [
        ('tree', TREE, 24, 85, 74, 1, 0.30),
        ('tree', TREE, 87, 85, 38, -1, 0.85),
        ('cabin', CAB, 52, 77, 28, 1, 0.50),
        ('item', BOARD, 71, 81, 12, 1, 0.80),
        ('item', RADIO, 36, 89, 8.5, 1, 0.80),
        ('item', PLANT, 47, 95, 9.5, 1, 0.80),
        ('item', MAIL, 64, 93, 13, 1, 0.80),
        ('bush', BUSH, 56, 98, 13, 1, 0.60),
        ('bush', BUSH, 30, 96, 10, -1, 0.70),
        ('fox', FOX, 43, 85, 13, 1, 0.0),
    ],
    'I': [
        ('tree', TREE, 21, 84, 70, 1, 0.30),
        ('tree', TREE, 88, 86, 34, -1, 0.85),
        ('cabin', CAB, 50, 76, 31, 1, 0.50),
        ('item', BOARD, 70, 80, 12.5, 1, 0.80),
        ('item', RADIO, 33, 88, 9, 1, 0.80),
        ('item', PLANT, 45, 95, 10, 1, 0.80),
        ('item', MAIL, 62, 94, 13.5, 1, 0.80),
        ('bush', BUSH, 55, 99, 13, 1, 0.60),
        ('bush', BUSH, 27, 97, 10, -1, 0.70),
        ('fox', FOX, 41, 86, 13, 1, 0.0),
    ],
    'J': [
        ('tree', TREE, 30, 87, 78, 1, 0.28),
        ('tree', TREE, 90, 87, 32, -1, 0.88),
        ('cabin', CAB, 46, 79, 27, 1, 0.45),
        ('item', BOARD, 66, 83, 12, 1, 0.78),
        ('item', RADIO, 30, 92, 8.5, 1, 0.78),
        ('item', PLANT, 40, 97, 10, 1, 0.78),
        ('item', MAIL, 58, 95, 13, 1, 0.78),
        ('bush', BUSH, 51, 100, 14, 1, 0.55),
        ('bush', BUSH, 22, 99, 11, -1, 0.65),
        ('fox', FOX, 37, 88, 13, 1, 0.0),
    ],
}

NAMES = {
    'H': 'H 主树居左 · 房子中右',
    'I': 'I 房子放大 · 居中',
    'J': 'J 房子嵌在树根旁（贴参考图）',
}


def tone(im, k):
    """k=0 原色，k=1 完全按背景的明度区间走"""
    if k <= 0:
        return im
    a = im.split()[3]
    r = im.convert('RGB')
    r = ImageEnhance.Brightness(r).enhance(1 + 0.06 * k)
    r = ImageEnhance.Contrast(r).enhance(1 - 0.10 * k)
    r = ImageEnhance.Color(r).enhance(1 - 0.14 * k)
    o = r.convert('RGBA')
    o.putalpha(a)
    return o


def compose(bg, plan):
    c = bg.convert('RGBA')
    for kind, path, x, y, h, flip, k in sorted(plan, key=lambda t: t[3]):
        src = Image.open(path).convert('RGBA')
        if flip < 0:
            src = src.transpose(Image.FLIP_LEFT_RIGHT)
        th = max(1, round(H * h / 100.0))
        tw = max(1, round(src.width * th / src.height))
        im = tone(src.resize((tw, th), Image.LANCZOS), k)

        px, py = round(W * x / 100.0) - tw // 2, round(H * y / 100.0) - th
        sw, sh = int(tw * 0.55), max(8, int(th * 0.045))
        shm = Image.new('RGBA', (sw * 2 + 40, sh * 2 + 40), (0, 0, 0, 0))
        ImageDraw.Draw(shm).ellipse([20, 20, 20 + sw, 20 + sh], fill=(46, 60, 38, 92))
        shm = shm.filter(ImageFilter.GaussianBlur(5))
        c.alpha_composite(shm, (px + tw // 2 - sw // 2 - 20, round(H * y / 100.0) - sh // 2 - 20))
        c.alpha_composite(im, (px, py))
    return c.convert('RGB')


def main():
    bg = lab.cover(Image.open(SCENE).convert('RGB'), W, H, focus=0.42)
    outs = []
    for k, plan in PLANS.items():
        img = compose(bg, plan)
        img.save(os.path.join(OUT, 'lay-%s.jpg' % k), quality=93)
        outs.append((k, img))
        print('saved', k, flush=True)

    tw = 780
    th = round(tw * H / W)
    n = len(outs)
    sheet = Image.new('RGB', (tw * n + 20 * (n + 1), th + 56), (250, 248, 243))
    d = ImageDraw.Draw(sheet)
    for i, (k, im) in enumerate(outs):
        x = 20 + i * (tw + 20)
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, 42))
        d.text((x + 6, 14), NAMES[k], fill=(24, 24, 24), font=font(19))
    p = os.path.join(OUT, 'lay-compare.jpg')
    sheet.save(p, quality=90)
    print('saved', p, flush=True)


if __name__ == '__main__':
    main()
