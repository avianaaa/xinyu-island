"""按 CSS 定位规则合成布局预览图，用来检查物件大小 / 落点 / 遮挡关系。

坐标和尺寸直接读 index.html + styles/main.css，不再各写一份，
免得预览图好看、真站点却对不上。
"""
import os
import re

from PIL import Image, ImageDraw, ImageFilter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(BASE, '.shots')
os.makedirs(SHOTS, exist_ok=True)

HTML = open(os.path.join(BASE, 'index.html'), encoding='utf-8').read()
CSS = open(os.path.join(BASE, 'styles/main.css'), encoding='utf-8').read()

MEDIA = '@media (max-width: 720px)'
cut = CSS.index(MEDIA)

RULE = re.compile(r'\.([\w-]+)\s*\{([^}]*)\}')
IMG = re.compile(r'class="([^"]*)"[^>]*>\s*(?:<span[^>]*></span>\s*)?<img src="([^"]+\.(?:webp|png))"', re.S)
VAL = re.compile(r'--([\w-]+):\s*(-?[\d.]+)(%|vw|vh)?')


def parse(text):
    out = {}
    for cls, body in RULE.findall(text):
        if '--x' not in body:
            continue
        out[cls] = {'--' + k: (float(v), unit or '') for k, v, unit in VAL.findall(body)}
    return out


BASE_RULES = parse(CSS[:cut])
MOBILE_RULES = parse(CSS[cut:])

# class -> 图片路径
SRC = {}
for cls, src in IMG.findall(HTML):
    for c in cls.split():
        SRC[c] = src


def px(props, key, W, H, default=0.0, horiz=False):
    v, unit = props.get(key, (default, '%'))
    if unit == 'vw':
        return W * v / 100
    if unit == 'vh':
        return H * v / 100
    return (W if horiz else H) * v / 100


def nodes(mobile):
    out = []
    for cls, base in BASE_RULES.items():
        if cls not in SRC:
            continue
        props = dict(base)
        if mobile:
            props.update(MOBILE_RULES.get(cls, {}))
        out.append({
            'cls': cls,
            'props': props,
            'src': SRC[cls],
            'z': props.get('--z', (50, ''))[0],
            'flip': props.get('--flip', (1, ''))[0],
            'sh': props.get('--sh', (0, ''))[0],
        })
    out.sort(key=lambda n: n['z'])
    return out


def cover(img, W, H, focus=0.42):
    iw, ih = img.size
    k = max(W / iw, H / ih)
    nw, nh = round(iw * k), round(ih * k)
    im = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - W) // 2
    top = int((nh - H) * focus)
    return im.crop((left, top, left + W, top + H))


def fox_area():
    """狐狸活动区直接从 fox.js 读，别在预览里抄一份。"""
    js = open(os.path.join(BASE, 'scripts/fox.js'), encoding='utf-8').read()
    m = re.search(r'var AREA = \{([^}]*)\}', js)
    area = {k: float(v) for k, v in re.findall(r'(x0|x1|y0|y1):\s*([\d.]+)', m.group(1))}
    pos = re.search(r'S\.x = S\.tx = ([\d.]+);\s*\n\s*S\.y = S\.ty = ([\d.]+);', js)
    if pos:
        area['sx'], area['sy'] = float(pos.group(1)), float(pos.group(2))
    return area


def compose(W, H, mobile=False, out='layout.png', bg=None):
    # 背景从 main.css 里读，别写死——改方案时要跟着变
    css_txt = open(os.path.join(BASE, 'styles/main.css'), encoding='utf-8').read()
    mbg = re.search(r'--scene-img:\s*url\("\.\./([^"]+)"\)', css_txt)
    bg_rel = bg or (mbg.group(1) if mbg else 'assets/scenes/web/scene-sunny-path.jpg')
    scene = Image.open(os.path.join(BASE, bg_rel)).convert('RGB')
    canvas = cover(scene, W, H).convert('RGBA')

    for n in nodes(mobile):
        p = n['props']
        sp = Image.open(os.path.join(BASE, n['src'])).convert('RGBA')
        th = max(1, round(px(p, '--h', W, H)))
        tw = round(sp.width * th / sp.height)
        sp = sp.resize((tw, th), Image.LANCZOS)
        if n['flip'] < 0:
            sp = sp.transpose(Image.FLIP_LEFT_RIGHT)

        cx = round(px(p, '--x', W, H, horiz=True))
        cy = round(px(p, '--y', W, H))

        if n['sh']:
            sw = int(tw * n['sh'])
            sh = max(4, int(th * 0.024))
            pad = sh * 2
            shadow = Image.new('RGBA', (sw + pad * 2, sh + pad * 2), (0, 0, 0, 0))
            d = ImageDraw.Draw(shadow)
            d.ellipse([pad, pad, pad + sw, pad + sh], fill=(46, 58, 38, 96))
            shadow = shadow.filter(ImageFilter.GaussianBlur(sh * 0.5))
            canvas.alpha_composite(shadow, (cx - sw // 2 - pad, cy - sh // 2 - pad))

        canvas.alpha_composite(sp, (cx - tw // 2, cy - th))

    # 狐狸：按 .fox 的高度规则摆一张 idle 图，看大小和站位合不合适
    fa = fox_area()
    fx = Image.open(os.path.join(BASE, 'assets/animals/watercolor/sprites/fox-idle-t.png')).convert('RGBA')
    fw = round(H * 0.175)          # .fox{ height:17.5% }，跟舞台高走
    fx = fx.resize((fw, fw), Image.LANCZOS)
    fpx = round(W * (fa.get('sx', (fa['x0'] + fa['x1']) / 2)) / 100)
    fpy = round(H * (fa.get('sy', (fa['y0'] + fa['y1']) / 2)) / 100)
    canvas.alpha_composite(fx, (fpx - fw // 2, fpy - fw))

    d = ImageDraw.Draw(canvas)
    d.line([(0, H * 0.135), (W, H * 0.135)], fill=(220, 90, 60, 110), width=1)
    d.line([(0, H - 26), (W, H - 26)], fill=(60, 90, 220, 110), width=1)

    # 狐狸活动区（虚线框）
    box = [W * fa['x0'] / 100, H * fa['y0'] / 100, W * fa['x1'] / 100, H * fa['y1'] / 100]
    step = 9
    for x in range(int(box[0]), int(box[2]), step * 2):
        d.line([(x, box[1]), (min(x + step, box[2]), box[1])], fill=(214, 96, 76, 170), width=1)
        d.line([(x, box[3]), (min(x + step, box[2]), box[3])], fill=(214, 96, 76, 170), width=1)
    for y in range(int(box[1]), int(box[3]), step * 2):
        d.line([(box[0], y), (box[0], min(y + step, box[3]))], fill=(214, 96, 76, 170), width=1)
        d.line([(box[2], y), (box[2], min(y + step, box[3]))], fill=(214, 96, 76, 170), width=1)

    canvas.convert('RGB').save(os.path.join(SHOTS, out), quality=92)
    print('ok', out, canvas.size)


import sys

if '--bg' in sys.argv:
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else 'layout-path.png'
    compose(1440, 900, False, out, bg=sys.argv[sys.argv.index('--bg') + 1])
else:
    compose(1440, 900, False, 'layout-desktop.png')
    compose(390, 844, True, 'layout-mobile.png')
