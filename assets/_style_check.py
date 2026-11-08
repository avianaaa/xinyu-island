from PIL import Image, ImageDraw
import os

ROOT = r"C:\Users\Mayyy\WorkBuddy\2026-11-02-17-19-29\assets"
CREAM = (251, 246, 236)
INK = (74, 58, 46)

items = [
    (r"animals\watercolor\Match_the_ART_STYLE_of_the_ref_2026-11-02T11-50-07.png", "FOX (watercolor)", "new"),
    (r"items\item-mailbox.png", "MAILBOX", "watercolor"),
    (r"items\item-radio.png", "RADIO", "watercolor"),
    (r"items\item-plant.png", "POT + CAN", "watercolor"),
    (r"animals\poses\fox-idle.png", "FOX (old flat)", "replaced"),
]

CELL = 400
GAP = 24
LAB = 54
COLS = 5
W = COLS * CELL + (COLS + 1) * GAP
H = 74 + CELL + LAB + GAP

sheet = Image.new("RGB", (W, H), CREAM)
d = ImageDraw.Draw(sheet)
d.text((GAP + 2, 28), "STYLE CHECK  -  does the fox belong with the objects?", fill=INK)

for i, (rel, name, tag) in enumerate(items):
    p = os.path.join(ROOT, rel)
    im = Image.open(p).convert("RGB").resize((CELL, CELL), Image.LANCZOS)
    x = GAP + i * (CELL + GAP)
    y = 74
    sheet.paste(im, (x, y))
    d.rectangle([x, y, x + CELL - 1, y + CELL - 1], outline=(223, 212, 196))
    d.text((x + 2, y + CELL + 10), name, fill=INK)
    d.text((x + 2, y + CELL + 30), tag, fill=(139, 111, 82))

out = os.path.join(ROOT, "style-check.png")
sheet.save(out)
print("saved", out, sheet.size)
