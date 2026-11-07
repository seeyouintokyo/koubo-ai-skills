"""Pick the music start that lands the most hits on the beat; writes beat.json."""
import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

# bpm and first_beat come from beats.py
page, out, bpm, first = sys.argv[1:5]
PERIOD, FIRST = 60 / float(bpm), float(first)
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True, args=["--allow-file-access-from-files"])
    pg = b.new_page(); pg.goto(Path(page).resolve().as_uri()); pg.wait_for_function("window.EVENTS !== undefined")
    ev = pg.evaluate("EVENTS()"); b.close()
hits = sorted(set(ev["slams"] + ev["wipes"]))
def score(start):
    phase = (FIRST - start) % PERIOD
    return sum(1 for h in hits if min((h - phase) % PERIOD, PERIOD - (h - phase) % PERIOD) < 0.06)
best = max((round(i * 0.01, 2) for i in range(0, 200)), key=score)
json.dump({"period": PERIOD, "phase": (FIRST - best) % PERIOD, "music_start": best}, open(out, "w"))
print("music_start", best, "on-beat", score(best), "/", len(hits))
