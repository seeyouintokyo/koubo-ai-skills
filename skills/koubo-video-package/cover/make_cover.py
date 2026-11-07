"""Make a cover from a person cutout: light the face, soften the edge, lay out the title.

Usage: make_cover.py config.json output.png
"""
import json, sys
from pathlib import Path
from PIL import Image, ImageChops, ImageEnhance, ImageFilter
from playwright.sync_api import sync_playwright

cfg = json.load(open(sys.argv[1]))
out = Path(sys.argv[2]).resolve()
work = out.parent / (out.stem + "_work")
work.mkdir(parents=True, exist_ok=True)


def prepare_person(path, face):
    img = Image.open(path).convert("RGBA")
    r, g, b, a = img.split()
    # Edge: pull in slightly and feather, which hides rough hair without an outline.
    a = a.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(cfg.get("feather", 1.6)))
    rgb = Image.merge("RGB", (r, g, b))
    rgb = rgb.filter(ImageFilter.UnsharpMask(radius=2.2, percent=70, threshold=3))
    W, H = img.size
    fx, fy, fw, fh = face  # normalized center and size
    # Face light: a soft ellipse around the face, so the hair stays dark.
    mask = Image.new("L", (W, H), 0)
    from PIL import ImageDraw
    d = ImageDraw.Draw(mask)
    cx, cy, rx, ry = fx * W, fy * H, fw * W * 0.86, fh * H * 1.05
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(rx * 0.32))
    lit = ImageEnhance.Brightness(rgb).enhance(cfg.get("face_light", 1.08))
    lit = ImageEnhance.Color(lit).enhance(1.04)
    rgb = Image.composite(lit, rgb, mask)
    rgb = ImageEnhance.Brightness(rgb).enhance(cfg.get("brightness", 1.0))
    res = rgb.convert("RGBA"); res.putalpha(a)
    res.save(work / "person.png")


# Labels around the person and the text tracks of the timeline panel. Set "pills" and "tracks" in the config;
# these placeholders only show the shape.
DEFAULT_PILLS = [["标签一", "left:28px;top:360px"], ["标签二", "right:28px;top:430px"], ["标签三", "left:20px;top:630px"]]
DEFAULT_TRACKS = [["字幕", [["第一句字幕", 210, ""], ["第二句", 150, ""], ["第三句字幕", 210, ""]]],
                  ["卡片", [["要点", 110, "r"], ["01 步骤", 180, "k"], ["数字", 160, "r"], ["02 步骤", 180, "k"]]]]
prepare_person(cfg["person"], cfg["face"])
if cfg.get("layout") == "stage":
    # Big title on top, smaller centered person, theme prop on the lower half.
    Image.open(cfg["strip"]).convert("RGB").save(work / "strip.jpg", quality=90)
    Image.open(cfg["win_left"]).convert("RGB").save(work / "win_left.jpg", quality=92)
    Image.open(cfg["win_right"]).convert("RGB").save(work / "win_right.jpg", quality=92)
    html = (Path(__file__).parent / "template_stage.html").read_text(encoding="utf8")
    vals = dict(KICKER=cfg.get("kicker", ""), TITLE=cfg["title"], TSIZE=cfg.get("title_size", 206), PTOP=cfg.get("person_top", 215),
                PHEIGHT=cfg.get("person_height", 860), PANELH=cfg.get("panel_height", 610), PANELTITLE=cfg.get("panel_title", ""),
                STRIP="strip.jpg", HEADTOP=cfg.get("playhead_top", 74),
                PILLS="".join(f'<div class="pill" style="{pos}"><i>✓</i>{txt}</div>' for txt, pos in cfg.get("pills", DEFAULT_PILLS)),
                TRACKS="".join(f'<div class="track"><label>{name}</label><div class="line">'
                               + "".join(f'<div class="clip {c}" style="width:{w}px">{txt}</div>' for txt, w, c in clips) + '</div></div>'
                               for name, clips in cfg.get("tracks", DEFAULT_TRACKS)))
else:
    Image.open(cfg["screen"]).convert("RGB").save(work / "screen.jpg", quality=92)
    html = (Path(__file__).parent / "template.html").read_text(encoding="utf8")
    vals = dict(KICKER=cfg.get("kicker", ""), LINE1=cfg["line1"], LINE2=cfg["line2"], SUB=cfg.get("sub", ""),
                SIZE1=cfg.get("size1", 176), SIZE2=cfg.get("size2", 205), TOP2=cfg.get("top2", 300), TOPSUB=cfg.get("top_sub", 512),
                PRIGHT=cfg.get("person_right", -130), PHEIGHT=cfg.get("person_height", 1120), SCREEN="screen.jpg", PERSON="person.png")
for k, v in vals.items():
    html = html.replace(f"__{k}__", str(v))
(work / "cover.html").write_text(html, encoding="utf8")
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True, args=["--allow-file-access-from-files"])
    pg = b.new_page(viewport={"width": 1080, "height": 1440})
    pg.goto((work / "cover.html").as_uri()); pg.evaluate("document.fonts.ready.then(()=>1)"); pg.wait_for_timeout(300)
    pg.screenshot(path=str(out)); b.close()
print(out)
