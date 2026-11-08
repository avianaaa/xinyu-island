from PIL import Image, ImageDraw
import os

ROOT = r"C:\Users\Mayyy\WorkBuddy\2026-11-02-17-19-29\assets"
FOX = os.path.join(ROOT, "animals", "watercolor")
ITEMS = os.path.join(ROOT, "items")
SCENES = os.path.join(ROOT, "scenes")
MOODS = os.path.join(ROOT, "moods")

CREAM = (251, 246, 236)
INK = (74, 58, 46)
SUB = (140, 112, 82)
LINE = (226, 214, 197)

W = 1920
PAD = 56

def paste_cell(sheet, path, box, label="", sublabel=""):
    x, y, s = box
    im = Image.open(path).convert("RGB")
    im = im.resize((s, s), Image.LANCZOS)
    sheet.paste(im, (x, y))
    d.rectangle([x, y, x + s - 1, y + s - 1], outline=LINE)
    if label:
        d.text((x + 2, y + s + 8), label, fill=INK)
    if sublabel:
        d.text((x + 2, y + s + 26), sublabel, fill=SUB)

# ---------- sizes ----------
TITLE_H = 92
PAL_H = 78
FOX_S, FOX_GAP = 208, 22
ITEM_S, ITEM_GAP = 208, 22
SC_W, SC_H, SC_GAP = 560, 373, 24
MOOD_S, MOOD_GAP = 132, 18
LAB = 46

fox_y = TITLE_H + PAL_H + 30
item_y = fox_y + FOX_S + LAB + 34
sc_y = item_y + ITEM_S + LAB + 34
mood_y = sc_y + SC_H + LAB + 34

H = mood_y + MOOD_S + LAB + PAD

sheet = Image.new("RGB", (W, H), CREAM)
d = ImageDraw.Draw(sheet)

d.text((PAD, 34), "XINYU  /  ASSET BOARD  /  watercolor set", fill=INK)
d.text((PAD, 58), "16 assets, one palette, one hand.  everything below is final except where marked.", fill=SUB)

# ---------- palette ----------
pal = [("#FBF6EC", "cream"), ("#A8C09A", "sage"), ("#F2B5A0", "peach"),
       ("#A8C8DC", "sky"), ("#8B6F52", "wood")]
px = PAD
for hexv, name in pal:
    rgb = tuple(int(hexv[i:i+2], 16) for i in (1, 3, 5))
    d.rectangle([px, TITLE_H, px + 96, TITLE_H + 46], fill=rgb, outline=LINE)
    d.text((px, TITLE_H + 52), name, fill=SUB)
    d.text((px + 52, TITLE_H + 52), hexv, fill=SUB)
    px += 130

mo = [("mood-1", "#9FB0BC"), ("mood-2", "#A9B39B"), ("mood-3", "#F0E4CC"),
      ("mood-4", "#F2B5A0"), ("mood-5", "#EFA06E")]
px = PAD + 5 * 130 + 60
d.text((px, TITLE_H + 52), "mood scale", fill=SUB)
px += 78
for _, hexv in mo:
    rgb = tuple(int(hexv[i:i+2], 16) for i in (1, 3, 5))
    d.rectangle([px, TITLE_H, px + 48, TITLE_H + 46], fill=rgb, outline=LINE)
    px += 54

# ---------- fox poses ----------
d.text((PAD, fox_y - 24), "ISLANDER  /  fox  /  7 states", fill=INK)
foxes = [("fox-idle.png", "IDLE", "default standing"),
         ("fox-blink.png", "BLINK", "random 4-8s"),
         ("fox-happy.png", "HAPPY", "on pet"),
         ("fox-sit.png", "SIT", "stopped"),
         ("fox-sleep.png", "SLEEP", "no entry today"),
         ("fox-walk-a.png", "WALK A", "stride 1"),
         ("fox-walk-b.png", "WALK B", "stride 2")]
for i, (fn, lb, sb) in enumerate(foxes):
    paste_cell(sheet, os.path.join(FOX, fn), (PAD + i * (FOX_S + FOX_GAP), fox_y, FOX_S), lb, sb)

# ---------- items ----------
d.text((PAD, item_y - 24), "OBJECTS  /  navigation  /  5", fill=INK)
items = [("item-mailbox.png", "MAILBOX", "to /record"),
         ("item-radio.png", "RADIO", "to /analysis"),
         ("item-plant.png", "POT + CAN", "to /garden"),
         ("item-board.png", "NOTICE BOARD", "to /calendar"),
         ("item-cabin.png", "CABIN", "to /settings")]
for i, (fn, lb, sb) in enumerate(items):
    paste_cell(sheet, os.path.join(ITEMS, fn), (PAD + i * (ITEM_S + ITEM_GAP), item_y, ITEM_S), lb, sb)

# ---------- scenes ----------
d.text((PAD, sc_y - 24), "SCENES  /  full bleed  /  center kept empty for UI", fill=INK)
scenes = [("scene-sunny.png", "SUNNY", "default"),
          ("scene-rainy.png", "RAINY", "mood <= 2"),
          ("scene-night.png", "NIGHT", "late visit")]
for i, (fn, lb, sb) in enumerate(scenes):
    im = Image.open(os.path.join(SCENES, fn)).convert("RGB").resize((SC_W, SC_H), Image.LANCZOS)
    x = PAD + i * (SC_W + SC_GAP)
    sheet.paste(im, (x, sc_y))
    d.rectangle([x, sc_y, x + SC_W - 1, sc_y + SC_H - 1], outline=LINE)
    d.text((x + 2, sc_y + SC_H + 8), lb, fill=INK)
    d.text((x + 2, sc_y + SC_H + 26), sb, fill=SUB)

# ---------- moods ----------
d.text((PAD, mood_y - 24), "MOOD SCALE  /  1-5  /  same body, only expression + tint + sprout", fill=INK)
names = ["1  very low", "2  low", "3  okay", "4  good", "5  great"]
for i in range(5):
    paste_cell(sheet, os.path.join(MOODS, f"mood-{i+1}.png"),
               (PAD + i * (MOOD_S + MOOD_GAP), mood_y, MOOD_S), names[i])

out = os.path.join(ROOT, "board-style.png")
sheet.save(out)
print("board", out, sheet.size)

# ---------- walk gif ----------
frames = []
for fn, bob in [("fox-walk-a.png", 0), ("fox-walk-b.png", -5)]:
    im = Image.open(os.path.join(FOX, fn)).convert("RGB").resize((360, 360), Image.LANCZOS)
    canvas = Image.new("RGB", (360, 380), CREAM)
    canvas.paste(im, (0, max(0, bob + 4)))
    frames.append(canvas)
out_gif = os.path.join(ROOT, "fox-walk-preview.gif")
frames[0].save(out_gif, save_all=True, append_images=frames[1:], duration=240, loop=0, optimize=True)
print("gif", out_gif)
