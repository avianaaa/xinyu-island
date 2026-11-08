# -*- coding: utf-8 -*-
"""把狐狸贴图底部烘死的那块草皮 / 泥地剥掉。

素材是"水彩 + 不透明底"生成的，草皮和狐狸烧在同一张图上，
狐狸一走动，草地就跟着滑 —— 看起来像踩着一块地毯在走。

做法：从图像底边和左右边做泛洪，只蔓延进"地面色"像素；
狐狸本体（橙棕 / 深棕描边 / 奶油白）不在泛洪集合里，天然是墙。
"""
import sys, glob, os
import numpy as np
from PIL import Image
from collections import deque

FOX = [62, 42, 30]      # 深棕描边
Y_MAX = 512             # 只在整张图下半部分动刀


def groundish(rgb):
    r = rgb[:, :, 0].astype(np.float32)
    g = rgb[:, :, 1].astype(np.float32)
    b = rgb[:, :, 2].astype(np.float32)
    v = np.maximum(np.maximum(r, g), b) / 255.0
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
    # 地面：偏黄（G-B 大）、不太艳、不太暗
    return ((g - b) >= 22) & (v >= 0.42) & (s <= 0.42) & ((r - g) <= 46)


def flood(mask, seeds):
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    dq = deque()
    for (y, x) in seeds:
        if mask[y, x] and not seen[y, x]:
            seen[y, x] = True
            dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    dq.append((ny, nx))
    return seen


def clean_small(mask, min_area=260):
    """清掉被爪子隔断的零星草枝：面积很小的连通块直接抹掉。"""
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    for y0 in range(h):
        for x0 in range(w):
            if mask[y0, x0] and not seen[y0, x0]:
                blob = []
                dq = deque([(y0, x0)])
                seen[y0, x0] = True
                while dq:
                    y, x = dq.popleft()
                    blob.append((y, x))
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                                seen[ny, nx] = True
                                dq.append((ny, nx))
                if len(blob) < min_area:
                    for (y, x) in blob:
                        mask[y, x] = False
    return mask


def run(path, out):
    im = Image.open(path).convert('RGBA')
    a = np.array(im)
    rgb = a[:, :, :3].astype(np.int16)
    alpha = a[:, :, 3]

    mask = groundish(rgb) & (alpha > 16)
    mask[:330, :] = False                    # 上半身绝不碰

    seeds = []
    h, w = mask.shape
    for x in range(w):
        for y in (h - 1, h - 2, h - 3, h - 12, h - 26):
            if 0 <= y < h:
                seeds.append((y, x))
    for y in range(330, h):
        for x in (0, 1, w - 1, w - 2):
            seeds.append((y, x))

    ground = flood(mask, seeds)
    ground = clean_small(ground)

    a[:, :, 3] = np.where(ground, 0, alpha)
    Image.fromarray(a, 'RGBA').save(out)
    return int(ground.sum())


if __name__ == '__main__':
    src = sys.argv[1]
    dst = sys.argv[2]
    os.makedirs(dst, exist_ok=True)
    for f in sorted(glob.glob(os.path.join(src, '*.png'))):
        n = run(f, os.path.join(dst, os.path.basename(f)))
        print('%-42s 去掉 %d 像素' % (os.path.basename(f), n))
