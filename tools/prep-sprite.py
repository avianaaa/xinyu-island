# -*- coding: utf-8 -*-
"""把生成图处理成可直接用的贴图。

生图工具只能输出不透明底，右下角还压着"AI生成"角标，所以这里做三件事：
  1. 抹掉右下角水印（用纸底色硬填，并检查有没有压到主体）
  2. 从四周泛洪抠出纸底
  3. 裁到主体外框，留一点呼吸边

用法：
  python tools/prep-sprite.py _gen/xxx.png assets/...
  python tools/prep-sprite.py --dir _gen assets/out
  python tools/prep-sprite.py in.png out.png --tol 22 --wm 0.78,0.905

  --tol  泛洪容差。水彩纸有渐变要放宽（46），底子干净的大图可以收紧（22），
         收紧了主体上浅色的高光才不会被当成纸底吃掉。
  --wm   水印区左上角在画面里的相对位置（x,y）。默认 0.76,0.86。
"""
import os
import sys
import glob
from collections import deque

import numpy as np
from PIL import Image, ImageFilter

TOL = 46           # 泛洪容差：水彩纸底是渐变的，太小会剩一圈纸色
FEATHER = 30       # 边缘羽化带宽（像素）


def bg_color(a):
    """四角取中位数当作纸底色。"""
    h, w = a.shape[:2]
    k = max(8, min(h, w) // 24)
    patches = [
        a[0:k, 0:k], a[0:k, w - k:w],
        a[h - k:h, 0:k], a[h - k:h, w - k:w],
    ]
    vals = np.concatenate([p[..., :3].reshape(-1, 3) for p in patches], axis=0)
    return np.median(vals, axis=0)


def kill_watermark(a, bg, fx=0.76, fy=0.86):
    """右下角角标。默认位置是实测值，个别图可以用 --wm 挪。"""
    h, w = a.shape[:2]
    x0, y0 = int(w * fx), int(h * fy)
    box = a[y0:h, x0:w, :3].astype(np.float32)
    d = np.linalg.norm(box - bg, axis=2)
    hit = int((d > 34).sum())
    a[y0:h, x0:w, :3] = bg.astype(np.uint8)
    return hit, (x0, y0)


def flood_bg(dist, tol):
    h, w = dist.shape
    bgm = np.zeros((h, w), dtype=bool)
    cand = dist < tol
    dq = deque()
    # 最外圈无条件当背景：主体永远是居中的，边缘必然是纸底。
    # 纸底本身有渐变，靠容差判断会在某些角上判不出来，所以直接种死。
    ring = 2
    for x in range(w):
        for y in list(range(ring)) + list(range(h - ring, h)):
            bgm[y, x] = True
            dq.append((y, x))
    for y in range(h):
        for x in list(range(ring)) + list(range(w - ring, w)):
            if not bgm[y, x]:
                bgm[y, x] = True
                dq.append((y, x))
    cand |= bgm
    while dq:
        y, x = dq.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and cand[ny, nx] and not bgm[ny, nx]:
                bgm[ny, nx] = True
                dq.append((ny, nx))
    return bgm


def drop_small(mask, min_area):
    """水彩纸有麻点纹理：泛洪绕过去的每个小点都会留下一个"透明洞"。
    这里把面积过小的连通块并回背景。"""
    h, w = mask.shape
    seen = np.zeros((h, w), dtype=bool)
    ys, xs = np.nonzero(mask)
    killed = 0
    for y0, x0 in zip(ys, xs):
        if seen[y0, x0]:
            continue
        blob = [(y0, x0)]
        seen[y0, x0] = True
        dq = deque([(y0, x0)])
        while dq:
            y, x = dq.popleft()
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    dq.append((ny, nx))
                    blob.append((ny, nx))
        if len(blob) < min_area:
            for (y, x) in blob:
                mask[y, x] = False
            killed += len(blob)
    return killed


def process(src, dst, max_side=1024, tol=TOL, wm=(0.76, 0.86)):
    im = Image.open(src).convert('RGB')
    a = np.dstack([np.array(im), np.full((im.height, im.width), 255, np.uint8)])
    bg = bg_color(a)

    hit, box = kill_watermark(a, bg, wm[0], wm[1])
    dist = np.linalg.norm(a[:, :, :3].astype(np.float32) - bg, axis=2)
    bgm = flood_bg(dist, tol)

    alpha = np.where(bgm, 0.0, 255.0)

    # 纸色残留的浅边：只在紧贴背景的一圈里按色差降低不透明度，避免一圈脏边
    band = np.array(Image.fromarray(bgm.astype(np.uint8) * 255)
                    .filter(ImageFilter.MaxFilter(FEATHER | 1))) > 0
    band &= ~bgm
    t = np.clip((dist - tol * 0.55) / (tol * 0.9), 0, 1)
    alpha = np.where(band, np.minimum(alpha, 255 * t), alpha)

    # 纸纹麻点：面积很小又孤立的碎块，一律按背景处理
    keep = alpha > 10
    min_area = max(80, int(im.width * im.height / 3200))
    killed = drop_small(keep, min_area)
    alpha = np.where(keep, alpha, 0)

    a[:, :, 3] = alpha.astype(np.uint8)
    out = Image.fromarray(a, 'RGBA')
    # 用较高的阈值算外框，免得一圈羽化把画布撑满
    solid = np.array(out.split()[3].point(lambda v: 255 if v > 40 else 0))
    bbox = Image.fromarray(solid).getbbox()
    if bbox:
        pad = 5
        l, t2, r, b = bbox
        out = out.crop((max(0, l - pad), max(0, t2 - pad),
                        min(out.width, r + pad), min(out.height, b + pad)))

    if max(out.size) > max_side:
        k = max_side / max(out.size)
        out = out.resize((max(1, round(out.width * k)), max(1, round(out.height * k))), Image.LANCZOS)

    os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
    out.save(dst)
    return out.size, hit


def take_opt(args, name, default):
    """从参数里摘掉 `--name value`，返回值（没给就用默认）。"""
    if name in args:
        i = args.index(name)
        v = args[i + 1]
        del args[i:i + 2]
        return v
    return default


if __name__ == '__main__':
    args = sys.argv[1:]
    tol = float(take_opt(args, '--tol', TOL))
    wm = tuple(float(x) for x in take_opt(args, '--wm', '0.76,0.86').split(','))
    if args and args[0] == '--dir':
        src_dir, dst_dir = args[1], args[2]
        os.makedirs(dst_dir, exist_ok=True)
        for f in sorted(glob.glob(os.path.join(src_dir, '*.png'))):
            name = os.path.basename(f)
            size, hit = process(f, os.path.join(dst_dir, name), tol=tol, wm=wm)
            print('%-52s -> %-12s 水印区抹掉 %d 像素' % (name, '%dx%d' % size, hit))
    else:
        src, dst = args[0], args[1]
        size, hit = process(src, dst, tol=tol, wm=wm)
        print('%s -> %s  %dx%d  水印区 %d' % (src, dst, size[0], size[1], hit))
