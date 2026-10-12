"""Show part of a plate at full resolution with the segment.py component boxes and ids.

Usage: zoom.py PLATE X0 Y0 X1 Y1 [OUT]   (coordinates in overlay pixels, as in work/seg/NNN_overlay.jpg)
Writes work/zoom/NNN_X0_Y0.jpg (or OUT), at most 1600 px on the long side. Boxes of every component,
including small ones (labels, leader dots), are drawn with their id; red = area >= 150, gray = smaller.
"""
import json
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
ZOOM = 1.4  # overlay scale relative to the segment.py downscale


def main():
    num, x0, y0, x1, y1 = map(int, sys.argv[1:6])
    seg = json.loads((ROOT / "work" / "seg" / f"{num:03d}.json").read_text())
    s = seg["scale"] / ZOOM  # overlay px -> plate px
    img = cv2.imread(str(ROOT / "plates" / f"{num:03d}.jpg"))
    X0, Y0, X1, Y1 = int(x0 * s), int(y0 * s), int(x1 * s), int(y1 * s)
    out = img[Y0:Y1, X0:X1].copy()
    f = min(1.0, 1600 / max(out.shape[:2]))
    out = cv2.resize(out, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    k = seg["scale"] * f  # downscale px -> output px
    for c in seg["components"]:
        bx, by = c["x"] * k - X0 * f, c["y"] * k - Y0 * f
        bw, bh = c["w"] * k, c["h"] * k
        if bx + bw < 0 or by + bh < 0 or bx > out.shape[1] or by > out.shape[0]:
            continue
        col = (0, 0, 220) if c["area"] >= 150 else (140, 140, 140)
        cv2.rectangle(out, (int(bx), int(by)), (int(bx + bw), int(by + bh)), col, 1)
        cv2.putText(out, str(c["id"]), (int(bx) + 2, int(by) + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1, cv2.LINE_AA)
    dest = Path(sys.argv[6]) if len(sys.argv) > 6 else ROOT / "work" / "zoom" / f"{num:03d}_{x0}_{y0}.jpg"
    dest.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dest), out, [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(dest)


if __name__ == "__main__":
    main()
