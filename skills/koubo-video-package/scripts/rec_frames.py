"""Turn a screen recording into a frame sequence with brand names blurred.

Usage: rec_frames.py recording.mp4 out_dir fps width [crop_bottom_px]

Frames are sampled at `fps` (2x speed-up = half the edit's frame rate), scaled to `width`,
and the bottom `crop_bottom_px` source pixels are cut off (status bars, model pickers).
macOS Vision OCR (ocr.swift next to this script) finds text lines; the
characters of a brand word inside a line are located proportionally and blurred.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageFilter

# Words to blur. Override with BLUR_WORDS="词1|词2" for the tools your recording shows.
BRANDS = re.compile(os.environ.get("BLUR_WORDS", r"飞书|豆包|opus|claude|feishu|lark|libtv|liblib|minimax|seedance|kling|可灵|即梦"), re.I)
OCR = Path(__file__).resolve().parent / "ocr.swift"


def main() -> None:
    """Extract, OCR and blur."""
    src, out, fps, width = sys.argv[1], Path(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4])
    crop = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    out.mkdir(parents=True, exist_ok=True)
    vf = f"fps={fps}" + (f",crop=iw:ih-{crop}:0:0" if crop else "")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", vf, "-q:v", "2", str(out / "f_%05d.jpg")], check=True)
    log = subprocess.run(["swift", str(OCR), str(out)], capture_output=True, text=True, check=True).stdout
    hits = 0
    for row in log.splitlines():
        name, _, items = row.partition("\t")
        img = Image.open(out / name).convert("RGB")
        W, H = img.size
        for it in items.split(" ;; ") if items else []:
            m = re.match(r"(.*)\|y=([\d.-]+)\|h=([\d.-]+)\|x=([\d.-]+)\|w=([\d.-]+)$", it)
            if not m:
                continue
            text, y, h, x, w = m[1], *map(float, m.groups()[1:])
            for b in BRANDS.finditer(text):
                # Wide (CJK) characters count double so Latin and Chinese mix lands roughly right.
                wt = [2 if ord(c) > 0x2E80 else 1 for c in text]
                tot = sum(wt) or 1
                a, e = sum(wt[: b.start()]) / tot, sum(wt[: b.end()]) / tot
                x0 = (x - w / 2 + a * w) * W - 0.6 * h * H
                x1 = (x - w / 2 + e * w) * W + 0.6 * h * H
                y0, y1 = (y - h * 0.9) * H, (y + h * 0.9) * H
                box = tuple(int(v) for v in (max(0, x0), max(0, y0), min(W, x1), min(H, y1)))
                if box[2] > box[0] and box[3] > box[1]:
                    img.paste(img.crop(box).filter(ImageFilter.GaussianBlur(10)), box[:2])
                    hits += 1
        img.thumbnail((width, 10000))
        img.save(out / name, quality=88)
    print(f"{len(log.splitlines())} frames, {hits} brand boxes blurred -> {out}")


if __name__ == "__main__":
    main()
