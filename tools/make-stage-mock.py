# -*- coding: utf-8 -*-
"""模拟「真实浏览器窗口里长什么样」，检查舞台两侧的补边效果。

正式站的舞台宽高比固定 1.6（= 背景图 1536×960），窗口比例不一样时舞台居中、
剩下的部分用同一张背景的模糊放大版垫底。这个脚本就是把那个效果先算出来。

跑法：
    python tools/make-stage-mock.py 1920x1080 1366x768 1088x543
输出：
    _preview/mock-<WWWWxHHHH>.jpg
"""
import os
import re
import sys

from PIL import Image, ImageFilter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(BASE, '.shots')
OUT = os.path.join(BASE, '_preview')
STAGE = os.path.join(SHOTS, 'layout-desktop.png')     # 舞台的 1:1 渲染（1440×900）
CSS = open(os.path.join(BASE, 'styles/main.css'), encoding='utf-8').read()

ASPECT = 1.6
m = re.search(r'--scene-img:\s*url\("\.\./([^"]+)"\)', CSS)
BG = os.path.join(BASE, m.group(1) if m else 'assets/scenes/web/scene-sunny-path.jpg')


def backdrop(W, H):
    """cover + 模糊，模拟 .scene::before"""
    im = Image.open(BG).convert('RGB')
    k = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    left = (im.width - W) // 2
    top = int((im.height - H) * 0.42)
    im = im.crop((left, top, left + W, top + H))
    return im.filter(ImageFilter.GaussianBlur(max(8, W // 40)))


def edge_fade(stage, px=34, cream=(251, 246, 236), strength=0.5):
    """模拟 .island 的 inset 内阴影：四周往奶油色淡出去，接住两侧的模糊底。"""
    import numpy as np
    w, h = stage.size
    m = np.ones((h, w), dtype=np.float32)
    ramp = np.clip(np.linspace(0, 1, px), 0, 1)
    m[:px, :] *= ramp[:, None]
    m[-px:, :] *= ramp[::-1][:, None]
    m[:, :px] *= ramp[None, :]
    m[:, -px:] *= ramp[::-1][None, :]
    a = (1 - m)[:, :, None] * strength
    base = np.asarray(stage, dtype=np.float32)
    out = base * (1 - a) + np.array(cream, dtype=np.float32) * a
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGB')


def mock(W, H):
    c = backdrop(W, H)
    stage = Image.open(STAGE).convert('RGB')
    # contain：舞台按比例塞进窗口
    sw = min(W, round(H * ASPECT))
    sh = round(sw / ASPECT)
    stage = edge_fade(stage.resize((sw, sh), Image.LANCZOS))
    c.paste(stage, ((W - sw) // 2, (H - sh) // 2))
    p = os.path.join(OUT, 'mock-%dx%d.jpg' % (W, H))
    c.save(p, quality=90)
    print('saved', p, '舞台 %dx%d 居中' % (sw, sh))


def main():
    os.makedirs(OUT, exist_ok=True)
    args = sys.argv[1:] or ['1920x1080', '1088x543']
    for a in args:
        w, h = a.lower().split('x')
        mock(int(w), int(h))


if __name__ == '__main__':
    main()
