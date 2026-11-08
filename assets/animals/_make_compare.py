from PIL import Image, ImageDraw
import os

BASE = r"C:\Users\Mayyy\WorkBuddy\2026-11-02-17-19-29\assets\animals"
OUT = os.path.join(BASE, "compare-sheet.png")

files = [("A1-capybara.png", "A1  CAPYBARA"), ("A2-fox.png", "A2  FOX"), ("A3-duck.png", "A3  DUCK")]
CREAM = (251, 246, 236)
INK = (74, 58, 46)

W, H = 1740, 1180
sheet = Image.new("RGB", (W, H), CREAM)
d = ImageDraw.Draw(sheet)

def label(x, y, text, size_hint=""):
    d.text((x, y), text + ("  " + size_hint if size_hint else ""), fill=INK)

# Row 1: 480px
top = 90
for i, (fn, name) in enumerate(files):
    im = Image.open(os.path.join(BASE, fn)).convert("RGBA")
    im = im.resize((480, 480), Image.LANCZOS)
    bg = Image.new("RGBA", (480, 480), CREAM + (255,))
    bg.alpha_composite(im)
    x = 40 + i * 570
    sheet.paste(bg.convert("RGB"), (x, top))
    d.rectangle([x, top, x + 479, top + 479], outline=(220, 210, 195))
    d.text((x + 8, top + 8), name, fill=INK)

# Row 2: 96px
top2 = 640
d.text((40, top2 - 30), "at 96px  (the size it actually shows in the garden)", fill=INK)
for i, (fn, name) in enumerate(files):
    im = Image.open(os.path.join(BASE, fn)).convert("RGBA")
    im = im.resize((96, 96), Image.LANCZOS)
    bg = Image.new("RGBA", (96, 96), CREAM + (255,))
    bg.alpha_composite(im)
    x = 40 + i * 130
    sheet.paste(bg.convert("RGB"), (x, top2))
    d.text((x, top2 + 104), name.split()[-1], fill=INK)

# Row 3: 48px
top3 = 810
d.text((40, top3 - 30), "at 48px  (mood-selector scale, worst case)", fill=INK)
for i, (fn, name) in enumerate(files):
    im = Image.open(os.path.join(BASE, fn)).convert("RGBA")
    im = im.resize((48, 48), Image.LANCZOS)
    bg = Image.new("RGBA", (48, 48), CREAM + (255,))
    bg.alpha_composite(im)
    x = 40 + i * 70
    sheet.paste(bg.convert("RGB"), (x, top3))
    d.text((x, top3 + 56), name.split()[-1], fill=INK)

# Row 4: silhouette test - crush to pure shapes (per-image background detection)
top4 = 960
d.text((40, top4 - 30), "silhouette test  (can you tell them apart with no color?)", fill=INK)
for i, (fn, name) in enumerate(files):
    im = Image.open(os.path.join(BASE, fn)).convert("RGBA")
    im = im.resize((110, 110), Image.LANCZOS)
    rgb = im.convert("RGB")
    px = rgb.load()
    # detect this image's own background tone from its corners
    corners = [px[1, 1], px[108, 1], px[1, 108], px[108, 108]]
    br = sum(c[0] for c in corners) / 4.0
    bgc = sum(c[1] for c in corners) / 4.0
    bb = sum(c[2] for c in corners) / 4.0
    flat = Image.new("RGB", (110, 110), CREAM)
    fp = flat.load()
    for y in range(110):
        for x in range(110):
            r, g, b = px[x, y]
            dist = ((r - br) ** 2 + (g - bgc) ** 2 + (b - bb) ** 2) ** 0.5
            if dist > 40:
                fp[x, y] = (90, 76, 62)
    x = 40 + i * 150
    sheet.paste(flat, (x, top4))

sheet.save(OUT)
print("saved", OUT, sheet.size)
