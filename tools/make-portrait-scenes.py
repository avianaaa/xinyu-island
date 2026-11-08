# -*- coding: utf-8 -*-
"""
make-portrait-scenes.py —— 把横版背景重组成手机竖版（9:19.5）

为什么不能直接裁：
    原图 1536×960，竖屏 390×844 用 cover 只能看到中间 29% 的宽度 ——
    小木屋在 67.6%、石子路在左下角，两边全被裁掉。

思路（不做生成，只做重组，所以风格必然一致）：
    原图里海、沙滩、草地是三条横向色带，草地本身几乎没有具体内容（都是色斑）。
    那么竖屏就可以这样拼：
        · 海    —— 取一条干净海面，纵向拉伸 + 模糊，做成"远处的海"，景深上说得通
        · 中段  —— 原图完整保留（沙滩线、石子路都在）
        · 草地  —— 取右侧纯草地一段，镜像接续后压缩到目标高度，接缝用渐变融合

用法：python tools/make-portrait-scenes.py
输出：assets/scenes/phone/scene-{sunny,rainy,night}-portrait.jpg
"""
import os

from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, 'assets', 'scenes', 'web')
OUT_DIR = os.path.join(ROOT, 'assets', 'scenes', 'phone')

# 目标画布（iPhone 14 Pro Max 的物理像素，9:19.5）
W, H = 1080, 2340

# 原图按宽度铺满后的高度
SCALED_H = int(round(960 * W / 1536))          # 675
# 沙滩带在原图里的位置（采样得出：海 → 沙滩在 y≈270，草地从 y≈390 开始）
SAND_TOP_SRC, GRASS_TOP_SRC = 270, 390


def band(src, y0, y1, x0=0, x1=None):
    return src.crop((x0, y0, x1 or src.width, y1))


def mirror_tile(strip, times=2):
    """上下镜像拼接，消除重复方向的接缝"""
    out = Image.new('RGB', (strip.width, strip.height * times))
    for i in range(times):
        seg = strip if i % 2 == 0 else strip.transpose(Image.FLIP_TOP_BOTTOM)
        out.paste(seg, (0, i * strip.height))
    return out


def build(name):
    src = Image.open(os.path.join(SRC_DIR, name)).convert('RGB')
    src = src.resize((W, SCALED_H), Image.LANCZOS)

    # 沙滩带落在画布 46% 的位置：上面留够海，下面留够站人的草地
    sand_y = int(H * 0.462)
    top_h = sand_y - SCALED_H * SAND_TOP_SRC // 960
    canvas = Image.new('RGB', (W, H))

    # ---- 1. 海：取一条干净海面，纵向拉伸成远景，再虚化 ----
    sea_src = band(src, 30, 205)
    sea = mirror_tile(sea_src, 2).resize((W, max(top_h, 1)), Image.LANCZOS)
    sea = sea.filter(ImageFilter.GaussianBlur(4.5))
    canvas.paste(sea, (0, 0))

    # ---- 2. 中段：原图完整保留 ----
    canvas.paste(src, (0, top_h))
    mid_bottom = top_h + SCALED_H

    # ---- 3. 草地：取右侧纯草皮（避开石子路），镜像接续后压到剩余高度 ----
    rest_h = H - mid_bottom
    if rest_h > 0:
        grass_src = band(src, 640, 960, x0=560)
        grass = mirror_tile(grass_src, 3).resize((W, rest_h), Image.LANCZOS)
        grass = grass.filter(ImageFilter.GaussianBlur(1.2))
        canvas.paste(grass, (0, mid_bottom))

    # ---- 4. 两处接缝各做一段渐变融合，别留硬边 ----
    canvas = blend_seam(canvas, top_h, 46)
    canvas = blend_seam(canvas, mid_bottom, 70)

    out = os.path.join(OUT_DIR, name.replace('.jpg', '-portrait.jpg'))
    canvas.save(out, 'JPEG', quality=88, optimize=True, progressive=True)
    print('%-26s %s  %d×%d  %.0f KB' % (
        name, os.path.basename(out), W, H, os.path.getsize(out) / 1024.0))


def blend_seam(img, y, span):
    """在 y 附近做 span 像素的上下渐变，把接缝揉开"""
    a = max(0, y - span // 2)
    b = min(img.height, y + span // 2)
    if b - a < 4:
        return img
    strip = img.crop((0, a, img.width, b))
    # 上下各取 24 行做均值，压缩成一条覆盖整段的过渡
    top = img.crop((0, a, img.width, a + 24)).resize((img.width, 1), Image.LANCZOS)
    bot = img.crop((0, b - 24, img.width, b)).resize((img.width, 1), Image.LANCZOS)
    grad = Image.new('RGB', (img.width, b - a))
    for i in range(b - a):
        t = i / float(b - a - 1)
        px_t = top.getpixel((0, 0))
        px_b = bot.getpixel((0, 0))
        row = tuple(int(px_t[c] * (1 - t) + px_b[c] * t) for c in range(3))
        for x in range(img.width):
            grad.putpixel((x, i), row)
    # 用半透明把过渡色压上去，只吃掉硬边，不抹掉纹理
    mask = Image.new('L', (img.width, b - a), 0)
    for i in range(b - a):
        t = i / float(b - a - 1)
        mask.paste(int(150 * (1 - abs(t - 0.5) * 2)), (0, i, img.width, i + 1))
    strip = Image.composite(grad, strip, mask)
    img.paste(strip, (0, a))
    return img


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for n in ('scene-sunny-path.jpg', 'scene-rainy-path.jpg', 'scene-night-path.jpg'):
        build(n)


if __name__ == '__main__':
    main()
