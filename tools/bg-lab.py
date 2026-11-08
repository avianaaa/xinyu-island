# -*- coding: utf-8 -*-
"""背景方案实验室：把几种"背景退后"的处理方式并排比出来，方便挑。

跑法：
    python tools/bg-lab.py
输出：
    _preview/bg-compare.jpg   四格对比
    _preview/bg-{key}.jpg     单独大图
"""
import os
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BG = os.path.join(BASE, 'assets/scenes/web/scene-sunny.jpg')
CABIN = os.path.join(BASE, 'assets/items/sprites/item-cabin-t.webp')
TREE = os.path.join(BASE, 'assets/decor/tree-a-t.webp')
BUSH = os.path.join(BASE, 'assets/decor/bush-a-t.webp')
FOX = os.path.join(BASE, 'assets/animals/watercolor/sprites/fox-idle-t.png')
OUT = os.path.join(BASE, '_preview')

W, H = 1440, 900

# 背景图上本来就画着的树（归一化 x0,y0,x1,y1），照着 1536x1024 量出来的
BG_TREES = [
    (0.00, 0.17, 0.145, 0.47),
    (0.00, 0.44, 0.125, 0.64),
    (0.86, 0.16, 1.00, 0.55),
    (0.90, 0.49, 1.00, 0.69),
]

# 当前 main.css 里的落点（x, y 脚底, 高）
LAYOUT = [
    ('tree', TREE, 0.13, 0.78, 0.36, 1),
    ('tree', TREE, 0.84, 0.87, 0.31, -1),
    ('cabin', CABIN, 0.30, 0.665, 0.335, 1),
    ('item', os.path.join(BASE, 'assets/items/sprites/item-board-t.png'), 0.68, 0.74, 0.13, 1),
    ('item', os.path.join(BASE, 'assets/items/sprites/item-radio-t.png'), 0.24, 0.88, 0.085, 1),
    ('item', os.path.join(BASE, 'assets/items/sprites/item-plant-t.png'), 0.50, 0.93, 0.09, 1),
    ('item', os.path.join(BASE, 'assets/items/sprites/item-mailbox-t.png'), 0.72, 0.92, 0.125, 1),
    ('bush', BUSH, 0.60, 0.97, 0.11, 1),
    ('bush', BUSH, 0.15, 0.965, 0.085, 1),
    ('fox', FOX, 0.44, 0.82, 0.13, 1),
]


def cover(im, w, h, focus=0.42):
    k = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    l = (im.width - w) // 2
    t = int((im.height - h) * focus)
    return im.crop((l, t, l + w, t + h))


def soft_region(im, box, blur=26, mix=0.85, dim=0.0, feather=40):
    """把一块区域揉成模糊色块：树就退成远景了，纸纹还在。"""
    x0, y0, x1, y1 = [round(v) for v in box]
    reg = im.crop((x0, y0, x1, y1))
    soft = reg.filter(ImageFilter.GaussianBlur(blur))
    if dim > 0:
        soft = Image.blend(soft, Image.new('RGB', soft.size, (214, 218, 210)), dim)
    # 羽化蒙版：区域中心最重，边缘渐隐，怕出硬边
    m = Image.new('L', (x1 - x0, y1 - y0), 0)
    d = ImageDraw.Draw(m)
    f = max(4, feather // 2)
    d.rounded_rectangle([f, f, x1 - x0 - f, y1 - y0 - f], radius=f, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(feather * 0.6))
    m = m.point(lambda v: round(v * mix))
    reg = Image.composite(soft, reg, m)
    im.paste(reg, (x0, y0))
    return im


def desat(im, k, bright=1.0, contrast=1.0):
    im = ImageEnhance.Color(im).enhance(k)
    im = ImageEnhance.Brightness(im).enhance(bright)
    im = ImageEnhance.Contrast(im).enhance(contrast)
    return im


def haze(im, color, a):
    return Image.blend(im, Image.new('RGB', im.size, color), a)


# ---------- 四种底色 ----------
def bg_v0(im):
    """现状：原图不动"""
    return im.copy()


def bg_v1(im):
    """雾化退景：背景整体变淡变柔，树只留影子"""
    o = im.copy()
    for r in BG_TREES:
        o = soft_region(o, (r[0] * W, r[1] * H, r[2] * W, r[3] * H), blur=22, mix=0.62, dim=0.30)
    o = desat(o, 0.80, bright=1.06, contrast=0.90)
    o = o.filter(ImageFilter.GaussianBlur(1.1))
    return haze(o, (238, 240, 234), 0.10)


def bg_v2(im):
    """抹掉背景树：画面里只留你叠上去的那几棵"""
    o = im.copy()
    for r in BG_TREES:
        o = soft_region(o, (r[0] * W, r[1] * H, r[2] * W, r[3] * H), blur=40, mix=0.97, dim=0.62, feather=54)
    o = desat(o, 0.88, bright=1.04, contrast=0.94)
    return o


def bg_v3(im):
    """空气透视：近处保留，远处（上三分之一）加雾，海天更亮"""
    o = im.copy()
    grad = Image.new('L', (1, H))
    for y in range(H):
        t = max(0.0, 1.0 - y / (H * 0.72))
        grad.putpixel((0, y), round(255 * (t ** 1.5)))
    grad = grad.resize((W, H))
    fog = Image.new('RGB', (W, H), (236, 240, 238))
    o = Image.composite(Image.blend(o, fog, 0.34), o, grad)
    for r in BG_TREES:
        o = soft_region(o, (r[0] * W, r[1] * H, r[2] * W, r[3] * H), blur=18, mix=0.55, dim=0.22)
    return desat(o, 0.86, bright=1.03, contrast=0.95)


def bg_v4(im):
    """只裁草地：把左右两条带树的边切掉，视野收到纯净草坡上"""
    # 原图按 cover 铺满后，左右各向内收 11%
    k = max(W / im.width, H / im.height) * 1.0
    big = im.resize((round(im.width * k * 1.24), round(im.height * k * 1.24)), Image.LANCZOS)
    ox = (big.width - W) // 2
    oy = int((big.height - H) * 0.40)
    o = big.crop((ox, max(0, oy), ox + W, max(0, oy) + H))
    return desat(o, 0.90, bright=1.02)


# ---------- 合成 ----------
def compose(bg, prep=None):
    """prep: 可选，对素材做明度对齐的函数；None 表示按原样贴"""
    c = bg.convert('RGBA')
    for kind, path, x, y, h, flip in LAYOUT:
        src = Image.open(path).convert('RGBA')
        if flip < 0:
            src = src.transpose(Image.FLIP_LEFT_RIGHT)
        th = max(1, round(H * h))
        tw = max(1, round(src.width * th / src.height))
        im = src.resize((tw, th), Image.LANCZOS)
        if prep and kind != 'fox':
            im = prep(im)
        px, py = round(W * x) - tw // 2, round(H * y) - th
        # 落地阴影
        sw, sh = int(tw * 0.55), max(8, int(th * 0.045))
        shm = Image.new('RGBA', (sw * 2 + 40, sh * 2 + 40), (0, 0, 0, 0))
        ImageDraw.Draw(shm).ellipse([20, 20, 20 + sw, 20 + sh], fill=(46, 60, 38, 92))
        shm = shm.filter(ImageFilter.GaussianBlur(5))
        c.alpha_composite(shm, (px + tw // 2 - sw // 2 - 20, round(H * y) - sh // 2 - 20))
        c.alpha_composite(im, (px, py))
    return c.convert('RGB')


def main():
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from tone import unify

    src = cover(Image.open(BG).convert('RGB'), W, H, focus=0.42)
    plans = [
        ('v0', bg_v0, None),
        ('v1', bg_v1, lambda i: unify(i, strength=0.75, fog=0.05)),
        ('v2', bg_v2, lambda i: unify(i, strength=0.95, fog=0.06)),
        ('v5', bg_v2, lambda i: unify(i, strength=1.15, fog=0.10)),
        ('v6', bg_v1, lambda i: unify(i, strength=1.30, fog=0.13, local=0.40)),
    ]
    outs = []
    for key, fn, prep in plans:
        img = compose(fn(src), prep)
        p = os.path.join(OUT, 'bg-%s.jpg' % key)
        img.save(p, quality=92)
        outs.append((key, img))
        print('saved', p)

    tw = 660
    th = round(tw * H / W)
    cols, rows = 3, 2
    sheet = Image.new('RGB', (tw * cols + 20 * (cols + 1), th * rows + 20 * (rows + 1)), (250, 248, 243))
    for i, (key, img) in enumerate(outs):
        r, c = divmod(i, cols)
        x = 20 + c * (tw + 20)
        y = 20 + r * (th + 20)
        sheet.paste(img.resize((tw, th), Image.LANCZOS), (x, y))
        ImageDraw.Draw(sheet).text((x + 8, y + 8), key.upper(), fill=(24, 24, 24))
    p = os.path.join(OUT, 'bg-compare.jpg')
    sheet.save(p, quality=90)
    print('saved', p)


if __name__ == '__main__':
    main()
