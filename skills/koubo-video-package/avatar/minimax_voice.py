"""Clone a voice with MiniMax and read one line with it.

Usage: minimax_voice.py sample.mp3 voice_id "text" out.mp3
The key is read from the MINIMAX_API_KEY environment variable and never printed.
voice_id is a name you choose (letters and digits, starting with a letter). If that voice
already exists, the clone step reports it and the script goes on to synthesize.
"""
import json, os, sys, urllib.request, uuid
from pathlib import Path

sample, voice_id, text, out = sys.argv[1:5]
key = os.environ.get("MINIMAX_API_KEY") or sys.exit("Set MINIMAX_API_KEY first.")


def call(base, path, body=None, files=None):
    hdr = {"Authorization": f"Bearer {key}"}
    if files:
        b = uuid.uuid4().hex
        parts = []
        for k, v in files.items():
            if isinstance(v, tuple):
                parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{v[0]}"\r\nContent-Type: audio/mpeg\r\n\r\n'.encode() + v[1] + b"\r\n")
            else:
                parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        data = b"".join(parts) + f"--{b}--\r\n".encode()
        hdr["Content-Type"] = f"multipart/form-data; boundary={b}"
    else:
        data = json.dumps(body).encode(); hdr["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, data=data, headers=hdr)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def ok(r):
    br = r.get("base_resp") or {}
    return br.get("status_code", 0) == 0, br.get("status_msg", "")


for base in ("https://api.minimaxi.com", "https://api.minimax.io"):
    try:
        up = call(base, "/v1/files/upload", files={"purpose": "voice_clone", "file": ("sample.mp3", Path(sample).read_bytes())})
    except Exception as e:
        print(base, "upload error", type(e).__name__, str(e)[:120]); continue
    good, msg = ok(up)
    print(base, "upload", good, msg)
    if not good: continue
    fid = up["file"]["file_id"]
    cl = call(base, "/v1/voice_clone", {"file_id": fid, "voice_id": voice_id, "need_noise_reduction": False, "need_volume_normalization": True})
    print("clone", *ok(cl))
    msg = ok(cl)[1].lower()
    if not ok(cl)[0] and "exist" not in msg and "duplicate" not in msg: sys.exit(1)
    for model in ("speech-2.8-hd", "speech-2.6-hd", "speech-02-hd"):
        t = call(base, "/v1/t2a_v2", {"model": model, "text": text, "stream": False, "language_boost": "Chinese",
                                     "voice_setting": {"voice_id": voice_id, "speed": 1.0, "vol": 1.0, "pitch": 0},
                                     "audio_setting": {"sample_rate": 44100, "bitrate": 128000, "format": "mp3", "channel": 1}})
        g, m = ok(t); print("tts", model, g, m)
        if g:
            Path(out).write_bytes(bytes.fromhex(t["data"]["audio"])); print("saved", out, "model", model); sys.exit(0)
    sys.exit(1)
sys.exit(1)
