"""Replace a lip-synced video's audio with our own narration, stretched to match its timing.

Usage: align_voice.py video.mp4 ours.wav out.mp4

Both tracks must say the same words. Whisper transcribes both with per-word times,
the characters are matched, and ours is cut inside each of its own pauses. The
matching cut in the video is placed between the same two characters. Each piece
of ours is then time-stretched to the video's length.
Pieces stretched by more than 25% are listed so they can be checked by ear.
"""

import difflib
import re
import subprocess
import sys
import tempfile

import whisper


def dur(path: str) -> float:
    """Return a media file's duration in seconds."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True,
    ).stdout
    return float(out)


def pauses(path: str, db: int = -35) -> list[tuple[float, float]]:
    """Return (start, end) of silences at least 0.15 s long."""
    log = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", path, "-vn", "-af",
         f"silencedetect=n={db}dB:d=0.15", "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr
    s = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
    e = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    return list(zip(s, e))


def chars(model, path: str) -> list[tuple[str, float, float]]:
    """Return (character, start, end) for every spoken character."""
    res = model.transcribe(path, language="zh", word_timestamps=True,
                           initial_prompt="以下是普通话的句子。")
    out = []
    for seg in res["segments"]:
        for w in seg.get("words", []):
            text = re.sub(r"[^\w]", "", w["word"]).lower()
            if not text:
                continue
            step = (w["end"] - w["start"]) / len(text)
            for i, c in enumerate(text):
                out.append((c, w["start"] + i * step, w["start"] + (i + 1) * step))
    return out


def main() -> None:
    """Align ours to the video and write the muxed file."""
    video, ours, out = sys.argv[1:4]
    model = whisper.load_model("small")
    with tempfile.TemporaryDirectory() as tmp:
        vwav = f"{tmp}/v.wav"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", video, "-vn",
                        "-ac", "1", "-ar", "16000", vwav], check=True)
        oc, vc = chars(model, ours), chars(model, vwav)

    sm = difflib.SequenceMatcher(None, [c for c, _, _ in oc], [c for c, _, _ in vc], autojunk=False)
    match = {}
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            match[blk.a + k] = blk.b + k
    print(f"matched {len(match)}/{len(oc)} of ours, video has {len(vc)}")

    a, b = [0.0], [0.0]
    # speech start
    if 0 in match:
        a.append(max(oc[0][1] - 0.05, 0.01))
        b.append(max(vc[match[0]][1] - 0.05, 0.01))
    for s, e in pauses(ours):
        m = (s + e) / 2
        prev = max((i for i, c in enumerate(oc) if c[2] <= m + 0.1), default=None)
        if prev is None or prev + 1 >= len(oc):
            continue
        nxt = prev + 1
        if prev not in match or nxt not in match or match[nxt] != match[prev] + 1:
            continue
        vt = (vc[match[prev]][2] + vc[match[nxt]][1]) / 2
        if m > a[-1] + 0.2 and vt > b[-1] + 0.2:
            a.append(m)
            b.append(vt)
    # speech end
    last = len(oc) - 1
    if last in match:
        ae, be = oc[last][2] + 0.05, vc[match[last]][2] + 0.05
        if ae > a[-1] + 0.2 and be > b[-1] + 0.2:
            a.append(ae)
            b.append(be)
    ta, tb = dur(ours), dur(video)
    a.append(ta)
    b.append(tb)

    filt, labels = [], []
    for i in range(len(a) - 1):
        r = (a[i + 1] - a[i]) / (b[i + 1] - b[i])
        flag = "  <-- check" if not 0.8 <= r <= 1.25 and a[i + 1] - a[i] > 0.3 else ""
        r = min(max(r, 0.5), 2.0)
        filt.append(f"[1:a]atrim={a[i]}:{a[i + 1]},asetpts=PTS-STARTPTS,atempo={r:.4f}[p{i}]")
        labels.append(f"[p{i}]")
        print(f"{a[i]:.2f}-{a[i + 1]:.2f} -> {b[i]:.2f}-{b[i + 1]:.2f}  x{r:.3f}{flag}")
    fc = ";".join(filt) + ";" + "".join(labels) + f"concat=n={len(labels)}:v=0:a=1[aout]"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", video, "-i", ours,
                    "-filter_complex", fc, "-map", "0:v", "-map", "[aout]", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", out], check=True)
    print("saved", out)


if __name__ == "__main__":
    main()
