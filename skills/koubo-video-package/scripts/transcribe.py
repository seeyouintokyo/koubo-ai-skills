import json
import os
import sys


from faster_whisper import WhisperModel

wav, out = sys.argv[1], sys.argv[2]
home = os.environ.get("KOUBO_VIDEO_HOME", os.path.expanduser("~/.cache/koubo-video"))
model_dir = os.path.join(home, "whisper-small")
m = WhisperModel(model_dir, device="cpu", compute_type="int8", local_files_only=True)
segs, info = m.transcribe(
    wav,
    language="zh",
    word_timestamps=True,
    vad_filter=False,
    # Put the names your video mentions into WHISPER_PROMPT so they are spelled right.
    initial_prompt=os.environ.get("WHISPER_PROMPT", "以下是普通话口播。"),
)
res = []
for s in segs:
    res.append(
        {
            "s": round(s.start, 2),
            "e": round(s.end, 2),
            "t": s.text,
            "w": [
                {"s": round(w.start, 2), "e": round(w.end, 2), "t": w.word}
                for w in (s.words or [])
            ],
        }
    )
with open(out, "w") as f:
    json.dump(res, f, ensure_ascii=False, indent=0)
