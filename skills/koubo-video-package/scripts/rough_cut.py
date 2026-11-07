"""Rough cut: remove retakes, tighten pauses, export video frames and clean audio."""
import json, os, subprocess, sys

SRC, WAV, TRANSCRIPT, EDIT, OUT = sys.argv[1:6]
edit = json.load(open(EDIT))
os.makedirs(OUT, exist_ok=True)
words = [w for seg in json.load(open(TRANSCRIPT)) for w in seg["w"]]
REMOVE = [tuple(x) for x in edit["remove"]]
FIX_LAST_START = edit.get("last_segment_start")
DURATION = edit["duration"]
PAD_IN, PAD_OUT, MAX_GAP = 0.06, 0.10, 0.28


def removed(word):
    mid = (word["s"] + word["e"]) / 2
    return any(a <= mid < b for a, b in REMOVE)


kept = [w for w in words if not removed(w)]
segments, start, end = [], max(0, kept[0]["s"] - PAD_IN), kept[0]["e"] + PAD_OUT
for w in kept[1:]:
    jumped = any(end - PAD_OUT <= a < w["s"] for a, _ in REMOVE)
    if jumped or w["s"] - (end - PAD_OUT) > MAX_GAP:
        segments.append((round(start, 3), round(end, 3)))
        start = w["s"] - PAD_IN
    end = w["e"] + PAD_OUT
segments.append((FIX_LAST_START or round(start, 3), round(min(end, DURATION), 3)))
json.dump(segments, open(f"{OUT}/edl.json", "w"), indent=0)
total = sum(b - a for a, b in segments)
print(len(segments), "segments, total", round(total, 2), "s")
if edit.get("edl_only"):
    sys.exit(0)

v = "".join(f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS[v{i}];" for i, (a, b) in enumerate(segments))
a_ = "".join(
    f"[1:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={b - a - 0.012:.3f}:d=0.012[a{i}];"
    for i, (a, b) in enumerate(segments)
)
n = len(segments)
graph = (
    v + a_ + "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0,fps=30[v];"
    + "".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[a]"
)
subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", SRC, "-i", WAV, "-filter_complex", graph,
                "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "12", "-preset", "fast",
                "-c:a", "pcm_s16le", f"{OUT}/cut.mov"], check=True)
os.makedirs(f"{OUT}/frames", exist_ok=True)
subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", f"{OUT}/cut.mov", "-q:v", "2",
                f"{OUT}/frames/f_%05d.jpg"], check=True)
subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", f"{OUT}/cut.mov", "-vn", "-ac", "1",
                "-c:a", "pcm_s16le", f"{OUT}/voice.wav"], check=True)
