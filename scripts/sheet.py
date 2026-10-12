"""Contact sheet of one plate's crops: sheet.py PLATE -> work/sheets/NNN.jpg (file name above each crop)."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
num = int(sys.argv[1])
files = sorted((ROOT / "work" / "crops").glob(f"{num:03d}_*.jpg"))
C, T = 6, 300
rows = max(1, (len(files) + C - 1) // C)
sheet = Image.new("RGB", (C * T, rows * (T + 16)), (150, 150, 150))
d = ImageDraw.Draw(sheet)
for k, f in enumerate(files):
    im = Image.open(f)
    im.thumbnail((T - 6, T - 6))
    x, y = (k % C) * T, (k // C) * (T + 16)
    sheet.paste(im, (x + 3, y + 16))
    d.text((x + 4, y + 2), f.stem, fill="black")
out = ROOT / "work" / "sheets" / f"{num:03d}.jpg"
out.parent.mkdir(parents=True, exist_ok=True)
sheet.save(out, quality=85)
print(out, len(files))
