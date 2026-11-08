from PIL import Image, ImageDraw
import os

BASE = r"C:\Users\Mayyy\WorkBuddy\2026-11-02-17-19-29\assets\animals"
POSES = os.path.join(BASE, "poses")
CREAM = (251, 246, 236)
INK = (74, 58, 46)

order = [
    ("fox-idle.png", "IDLE", "default standing"),
    ("fox-blink.png", "BLINK", "random 4-8s"),
    ("fox-happy.png", "HAPPY", "on pet / head touch"),
    ("fox-walk-a.png", "WALK A", "side view, stride 1"),
    ("fox-walk-b.png", "WALK B", "side view, stride 2"),
    ("fox-sit.png", "SIT", "stopped, resting"),
    ("fox-sleep.png", "SLEEP", "idle too long / no entry"),
]

# ---------- pose sheet ----------
COLS = 4
CELL = 380
GAP = 26
LABEL_H = 62
rows = (len(order) + COLS - 1) // COLS
W = COLS * CELL + (COLS + 1) * GAP
H = rows * (CELL + LABEL_H) + (rows + 1) * GAP + 76

sheet = Image.new("RGB", (W, H), CREAM)
d = ImageDraw.Draw(sheet)
d.text((GAP + 4, 32), "FOX  ·  pose set  ·  all shown at 380px", fill=INK)

for i, (fn, name, note) in enumerate(order):
    r, c = divmod(i, COLS)
    x = GAP + c * (CELL + GAP)
    y = 76 + GAP + r * (CELL + LABEL_H + GAP)
    im = Image.open(os.path.join(POSES, fn)).convert("RGBA").resize((CELL, CELL), Image.LANCZOS)
    bg = Image.new("RGBA", (CELL, CELL), CREAM + (255,))
    bg.alpha_composite(im)
    sheet.paste(bg.convert("RGB"), (x, y))
    d.rectangle([x, y, x + CELL - 1, y + CELL - 1], outline=(223, 212, 196))
    d.text((x + 2, y + CELL + 12), name, fill=INK)
    d.text((x + 2, y + CELL + 32), note, fill=(139, 111, 82))

out_sheet = os.path.join(BASE, "fox-pose-sheet.png")
sheet.save(out_sheet)
print("sheet", out_sheet, sheet.size)

# ---------- walk cycle gif ----------
frame_px = 320
bobs = [0, -4]  # fake the vertical bob between the two strides
frames = []
for fn, bob in zip(["fox-walk-a.png", "fox-walk-b.png"], bobs):
    im = Image.open(os.path.join(POSES, fn)).convert("RGBA").resize((frame_px, frame_px), Image.LANCZOS)
    canvas = Image.new("RGBA", (frame_px, frame_px), CREAM + (255,))
    canvas.alpha_composite(im, (0, bob))
    frames.append(canvas.convert("RGB"))

out_gif = os.path.join(BASE, "fox-walk-preview.gif")
frames[0].save(out_gif, save_all=True, append_images=frames[1:], duration=220, loop=0, optimize=True)
print("gif", out_gif)
