"""Render stills (--at t1,t2) or the whole video to stdout-piped ffmpeg."""
import argparse, subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument("--page"); ap.add_argument("--out"); ap.add_argument("--at", default="")
ap.add_argument("--range", default="", help="start,end seconds of output to render")
a = ap.parse_args()
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True, args=["--allow-file-access-from-files"])
    pg = b.new_page(viewport={"width": 1080, "height": 1920})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(Path(a.page).resolve().as_uri())
    pg.wait_for_function("window.seek !== undefined")
    pg.evaluate("document.fonts.ready.then(()=>1)")
    if a.at:
        Path(a.out).mkdir(parents=True, exist_ok=True)
        for t in a.at.split(","):
            pg.evaluate("t => seek(t)", float(t))
            pg.wait_for_timeout(60)
            pg.screenshot(path=f"{a.out}/t_{float(t):06.2f}.jpg", type="jpeg", quality=85)
    else:
        dur, fps = pg.evaluate("[DURATION, FPS]")
        Path(a.out + ".events.json").write_text(__import__("json").dumps(pg.evaluate("EVENTS()")))
        n = int(dur * fps)
        i0, i1 = 0, n
        if a.range:
            s0, s1 = (float(x) for x in a.range.split(","))
            i0, i1 = int(s0 * fps), min(n, int(s1 * fps))
        ff = subprocess.Popen(["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "image2pipe", "-framerate", str(fps), "-c:v", "mjpeg",
                               "-i", "-", "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", a.out], stdin=subprocess.PIPE)
        for i in range(i0, i1):
            pg.evaluate("t => seek(t)", i / fps)
            ff.stdin.write(pg.screenshot(type="jpeg", quality=95))
            if i % 150 == 0:
                print(i, "/", n, flush=True)
        ff.stdin.close(); ff.wait()
    print("errors:", errs[:3])
    b.close()
