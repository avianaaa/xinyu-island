# -*- coding: utf-8 -*-
"""把原图左下角那条石子路贴回 16:9 背景上。

背景用的 scene-*-wide.jpg 是原图 crop(160,40,1360,715) 放大 1.28 倍的结果，
底边正好切在 y=715，而石子路在 y=720 以下 —— 整条被切掉了。
这里把原图的石子路连同周围草一起搬回来，贴在左下角，边缘羽化。

雨的雨丝、夜的暖蓝调是叠在 sunny 底图上的，所以贴之前先把补丁按
「sunny → 该天气」的整体线性映射调过去，不会一块亮一块暗。

跑法：
    python tools/add-path.py            # 只出预览 _preview/bg-path-{sunny,rainy,night}.jpg
    python tools/add-path.py --write    # 同时写 assets/scenes/web/scene-*-path.jpg
"""
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(BASE, 'assets/scenes/web')
OUT = os.path.join(BASE, '_preview')

# 原图里石子路所在的那块（上边带一点草，左边顶到画布边缘）
SRC_BOX = (0, 655, 470, 1024)
ZOOM = 1.28

WEATHER = ['sunny', 'rainy', 'night']


def patch_from_original():
    return Image.open(os.path.join(WEB, 'scene-sunny.jpg')).convert('RGB').crop(SRC_BOX)


def feather_mask(size, top=150, right=190):
    """只有上边和右边要淡出：左边和下边就是画布边界。"""
    w, h = size
    m = np.ones((h, w), dtype=np.float32)
    if top:
        m[:top, :] *= np.clip(np.linspace(0, 1, top), 0, 1)[:, None]
    if right:
        m[:, w - right:] *= np.clip(np.linspace(1, 0, right), 0, 1)[None, :]
    return Image.fromarray((m * 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(6))


def fit_map(src, dst):
    """逐通道最小二乘拟合 src→dst 的线性映射 (a, b)。"""
    a = np.asarray(src.resize((160, 100), Image.LANCZOS), dtype=np.float32).reshape(-1, 3)
    b = np.asarray(dst.resize((160, 100), Image.LANCZOS), dtype=np.float32).reshape(-1, 3)
    out = []
    for c in range(3):
        x, y = a[:, c], b[:, c]
        A = np.vstack([x, np.ones_like(x)]).T
        (ka, kb), *_ = np.linalg.lstsq(A, y, rcond=None)
        out.append((float(ka), float(kb)))
    return out


def apply_map(im, maps):
    a = np.asarray(im, dtype=np.float32)
    for c, (k, b) in enumerate(maps):
        a[:, :, c] = a[:, :, c] * k + b
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB')


def grass_pixels(im):
    a = np.asarray(im, dtype=np.float32).reshape(-1, 3)
    l = a.mean(axis=1)
    return a[(l > 60) & (l < 225)]


def match_grass(patch, region, maps=None, chroma=True):
    """把补丁的草压到目标区域上：先按天气调色，再对齐明度和彩度。"""
    if maps:
        patch = apply_map(patch, maps)
    a = np.asarray(patch, dtype=np.float32)
    sa, sr = grass_pixels(patch), grass_pixels(region)
    if len(sa) > 50 and len(sr) > 50:
        k = float(np.clip(sr.mean() / max(1e-3, sa.mean()), 0.55, 1.45))
        d = sr.mean(axis=0) - sa.mean(axis=0) * k
        a = a * k + d * 0.6
        print('  grass x%.3f' % k)

        if chroma:
            # 彩度（max-min）也一起对：夜里草地本来就发灰，补丁不压下去会"发绿"
            cs = float(np.clip((sr.max(axis=1) - sr.min(axis=1)).mean() /
                               max(1e-3, (sa.max(axis=1) - sa.min(axis=1)).mean()), 0.35, 1.3))
            lum = a.mean(axis=2, keepdims=True)
            a = lum + (a - lum) * cs
            print('  chroma x%.3f' % cs)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB')


def build(weather, sunny_ref):
    bg = Image.open(os.path.join(WEB, 'scene-%s-wide.jpg' % weather)).convert('RGB')
    W, H = bg.size
    p = patch_from_original()
    p = p.resize((round(p.width * ZOOM), round(p.height * ZOOM)), Image.LANCZOS)

    x, y = 0, H - p.height
    region = bg.crop((x, y, x + p.width, H))
    maps = None
    if weather != 'sunny':
        # 用同一块位置上的「晴 → 该天气」变换，比全图拟合准得多：
        # 雨丝、夜景的冷暖都只作用在这一带的草地上
        maps = fit_map(sunny_ref.crop((x, y, x + p.width, H)), region)
        print('  map', [tuple(round(v, 3) for v in m) for m in maps])
        p = apply_map(p, maps)
        p = match_grass(p, region, None, chroma=False)
    else:
        p = match_grass(p, region, None)

    bg.paste(Image.composite(p, region, feather_mask(p.size)), (x, y))
    return bg


def main():
    os.makedirs(OUT, exist_ok=True)
    writing = '--write' in sys.argv
    sunny_ref = Image.open(os.path.join(WEB, 'scene-sunny-wide.jpg')).convert('RGB')
    for w in WEATHER:
        print(w)
        img = build(w, sunny_ref)
        if writing:
            dst = os.path.join(WEB, 'scene-%s-path.jpg' % w)
            img.save(dst, quality=90, optimize=True)
            print('  saved', dst)
        else:
            p = os.path.join(OUT, 'bg-path-%s.jpg' % w)
            img.save(p, quality=92)
            print('  saved', p)


if __name__ == '__main__':
    main()
