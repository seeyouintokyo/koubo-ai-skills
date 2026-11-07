"""v4 mix: real CC0 interface sounds (Kenney) mapped to motion events, quiet under the voice.

Usage: finish_audio_v4.py video voice.wav events.json music.mp3 music_start sfx_dir out.mp4 [start end]
"""
import json, re, subprocess, sys, wave
from pathlib import Path
import numpy as np

video, voice, events_path, music, music_start, sfx_dir, out = sys.argv[1:8]
t0, t1 = (float(sys.argv[8]), float(sys.argv[9])) if len(sys.argv) > 9 else (0.0, None)
SR = 48000
ev = json.load(open(events_path))
with wave.open(voice) as w:
    total = w.getnframes() / w.getframerate()
t1 = t1 or total
n = int((t1 - t0) * SR)
bed = np.zeros(n + 2 * SR)
rng = np.random.default_rng(5)
cache = {}


def load(name):
    if name not in cache:
        raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(Path(sfx_dir) / f"{name}.ogg"), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                             capture_output=True, check=True).stdout
        x = np.frombuffer(raw, np.float32).astype(np.float64)
        cache[name] = x / max(1e-6, np.abs(x).max())
    return cache[name]


def add(sound, t, gain):
    i = int((t - t0) * SR)
    if i < 0 or i >= n:
        return
    bed[i:i + len(sound)] += sound[: max(0, len(bed) - i)] * gain


def whoosh(length=0.38):
    m = int(length * SR)
    x = rng.standard_normal(m)
    spec = np.fft.rfft(x); f = np.fft.rfftfreq(m, 1 / SR)
    spec *= np.exp(-0.5 * (np.log(np.maximum(f, 1) / 1100) / 0.9) ** 2)
    y = np.fft.irfft(spec, m) * np.sin(np.linspace(0, np.pi, m)) ** 3
    return y / np.abs(y).max()


pick = lambda names: names[rng.integers(len(names))]
for o in ev["wipes"]:
    add(whoosh(), o - 0.18, 0.10)
    add(load(pick(["maximize_002", "maximize_004", "minimize_003", "maximize_006"])), o - 0.02, 0.10)
for o in ev.get("chapters", []):
    add(load(pick(["confirmation_001", "confirmation_003"])), o + 0.05, 0.12)
for o in ev.get("slams", []):
    add(load(pick(["drop_001", "drop_002", "drop_003", "drop_004"])), o, 0.20)
for o in ev.get("fullcuts", []):
    add(load(pick(["glass_001", "glass_003", "glass_005"])), o - 0.02, 0.09)
last = -9
for o in sorted(ev["pops"]):
    if o - last < 0.35:
        continue
    last = o
    add(load(pick(["click_001", "click_003", "select_002", "select_005", "switch_003", "toggle_002"])), o, 0.08)
bed = np.int16(np.clip(bed[:n], -1, 1) * 32767)
sfx = out + ".sfx.wav"
with wave.open(sfx, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(bed.tobytes())

dur = t1 - t0
fmt = "aformat=sample_rates=48000:channel_layouts=stereo"
mix = (f"[0:a]atrim={t0}:{t1},asetpts=PTS-STARTPTS,{fmt},asplit[vk][vm];[1:a]{fmt}[s];"
       f"[2:a]{fmt},atrim={float(music_start) + t0}:{float(music_start) + t1:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.25,afade=t=out:st={max(0.1, dur - 1.5):.3f}:d=1.5,volume=-22dB[b0];"
       "[b0][vk]sidechaincompress=threshold=0.03:ratio=5:attack=25:release=350[b];"
       "[vm][s][b]amix=inputs=3:normalize=0[m];[m]")
first = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", voice, "-i", sfx, "-i", music, "-filter_complex",
                        mix + "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
s = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", first, re.S).group())
ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:measured_I={s['input_i']}:measured_TP={s['input_tp']}:"
      f"measured_LRA={s['input_lra']}:measured_thresh={s['input_thresh']}:offset={s['target_offset']},aresample=48000")
subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", voice, "-i", sfx, "-i", music, "-i", video, "-filter_complex", mix + ln + "[a]",
                "-map", "3:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-movflags", "+faststart", "-shortest", out], check=True)
