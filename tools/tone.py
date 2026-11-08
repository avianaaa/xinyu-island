# -*- coding: utf-8 -*-
"""把新画的素材拉进背景的色彩区间里。

背景是极淡的水彩，明度集中在 200-235；新生成的小木屋/树/花丛暗部掉到 60-90，
直接贴上去就是贴纸感。这里做三件事：
  1. 抬暗部（曲线不是 gamma，中间调跟着走，亮部不动）
  2. 压局部对比（和自身模糊版混合，去掉枝叶上的黑噪点）
  3. 降饱和 + 掺一点空气雾色

用法：
    from tone import unify
    img = unify(img, strength=1.0)
"""
from PIL import Image, ImageFilter
import numpy as np

# 明度曲线控制点：(输入, 输出)，归一化
CURVE = [(0.00, 0.14), (0.18, 0.34), (0.38, 0.54), (0.60, 0.71), (0.80, 0.86), (1.00, 1.00)]
FOG = (238, 240, 233)


def _lut(strength=1.0):
    xs = np.array([p[0] for p in CURVE]) * 255
    ys = np.array([p[1] for p in CURVE]) * 255
    src = np.arange(256)
    out = np.interp(src, xs, ys)
    out = src + (out - src) * strength
    return [int(round(v)) for v in np.clip(out, 0, 255)]


def unify(im, strength=1.0, sat=0.80, local=0.30, fog=0.06, blur=1.5):
    """im: RGBA。返回 RGBA，alpha 保持不变。"""
    if im.mode != 'RGBA':
        im = im.convert('RGBA')
    alpha = im.split()[3]
    rgb = im.convert('RGB')

    lut = _lut(strength)
    rgb = rgb.point(lut * 3)

    if local > 0:
        soft = rgb.filter(ImageFilter.GaussianBlur(blur))
        rgb = Image.blend(rgb, soft, local)

    # 只对有色区域降饱和（白色高光不参与，否则会发灰）
    a = np.array(rgb).astype(np.float32)
    mx = a.max(axis=2, keepdims=True)
    mn = a.min(axis=2, keepdims=True)
    mean = (mx + mn) / 2
    gray = np.repeat(mean, 3, axis=2)
    # mean 越低的像素（暗部）降饱和越多
    w = np.clip((235 - mean[:, :, 0]) / 235, 0, 1)[:, :, None]
    a = a + (gray - a) * (1 - sat) * w
    rgb = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB')

    if fog > 0:
        rgb = Image.blend(rgb, Image.new('RGB', rgb.size, FOG), fog)

    out = rgb.convert('RGBA')
    out.putalpha(alpha)
    return out


if __name__ == '__main__':
    import sys, os
    for p in sys.argv[1:]:
        im = Image.open(p).convert('RGBA')
        out = unify(im)
        d = p.replace('.webp', '-u.webp').replace('.png', '-u.png')
        out.save(d, quality=90) if d.endswith('.webp') else out.save(d)
        a = np.array(out.convert('RGB')).astype(np.float32).mean(axis=2)
        m = np.array(out.split()[3]) > 40
        print(p, 'mean %.0f  p5 %.0f' % (a[m].mean(), np.percentile(a[m], 5)), '->', d)
