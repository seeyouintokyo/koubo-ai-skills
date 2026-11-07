"""Soft-theme mix: fewer, quieter, varied sounds under the voice.

Usage: finish_audio_soft.py video voice.wav events.json music.mp3 music_start out.mp4 [start end]
start/end (output seconds) cut a range for samples.
"""
import json, re, subprocess, sys, wave
import numpy as np

video, voice, events_path, music, music_start, out = sys.argv[1:7]
t0, t1 = (float(sys.argv[7]), float(sys.argv[8])) if len(sys.argv) > 8 else (0.0, None)
SR = 48000
ev = json.load(open(events_path))
with wave.open(voice) as w:
    total = w.getnframes() / w.getframerate()
t1 = t1 or total
n = int((t1 - t0) * SR)
bed = np.zeros(n + SR)
rng = np.random.default_rng(11)


def add(sound, t, gain):
    i = int((t - t0) * SR)
    if i < 0 or i >= n:
        return
    bed[i:i + len(sound)] += sound[: max(0, len(bed) - i)] * gain


def whoosh(length=0.42, lo=300, hi=2600):
    m = int(length * SR)
    x = rng.standard_normal(m)
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(m, 1 / SR)
    centre = np.sqrt(lo * hi)
    spec *= np.exp(-0.5 * (np.log(np.maximum(f, 1) / centre) / 0.8) ** 2)
    y = np.fft.irfft(spec, m)
    env = np.sin(np.linspace(0, np.pi, m)) ** 2
    y = y * env
    return y / np.abs(y).max()


def chime(freq):
    t = np.arange(int(0.9 * SR)) / SR
    y = (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * freq * 2.01 * t)) * np.exp(-t * 5)
    y[: int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))
    return y / np.abs(y).max()


def tick(freq):
    t = np.arange(int(0.05 * SR)) / SR
    y = np.sin(2 * np.pi * freq * t) * np.exp(-t * 120)
    return y / np.abs(y).max()


for o in ev["wipes"]:
    add(whoosh(), o - 0.2, 0.06)
for o in ev.get("chapters", []):
    add(chime(880), o, 0.05)
    add(chime(1318.5), o + 0.08, 0.035)
last = -9
for o in sorted(ev["pops"]):
    if o - last < 0.45:
        continue
    last = o
    add(tick(rng.choice([1400, 1600, 1800, 2100])), o, 0.035)
bed = np.int16(np.clip(bed[:n], -1, 1) * 32767)
sfx = out + ".sfx.wav"
with wave.open(sfx, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(bed.tobytes())

dur = t1 - t0
fmt = "aformat=sample_rates=48000:channel_layouts=stereo"
mix = (f"[0:a]atrim={t0}:{t1},asetpts=PTS-STARTPTS,{fmt},asplit[vk][vm];[1:a]{fmt}[s];"
       f"[2:a]{fmt},atrim={float(music_start) + t0}:{float(music_start) + t1:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.25,afade=t=out:st={dur - 1.5:.3f}:d=1.5,volume=-23dB[b0];"
       "[b0][vk]sidechaincompress=threshold=0.03:ratio=5:attack=25:release=350[b];"
       "[vm][s][b]amix=inputs=3:normalize=0[m];[m]")
first = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", voice, "-i", sfx, "-i", music, "-filter_complex",
                        mix + "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
s = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", first, re.S).group())
ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:measured_I={s['input_i']}:measured_TP={s['input_tp']}:"
      f"measured_LRA={s['input_lra']}:measured_thresh={s['input_thresh']}:offset={s['target_offset']},aresample=48000")
subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", voice, "-i", sfx, "-i", music, "-i", video, "-filter_complex", mix + ln + "[a]",
                "-map", "3:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-movflags", "+faststart", "-shortest", out], check=True)
