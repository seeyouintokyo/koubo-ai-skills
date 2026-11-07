"""Synthesize light UI sounds from composition events, mix under the voice, normalize, and mux."""
import json, re, subprocess, sys, wave
import numpy as np

video, voice, events_path, music, music_start, out = sys.argv[1:7]
SR = 48000
ev = json.load(open(events_path))
with wave.open(voice) as w:
    n = w.getnframes()
bed = np.zeros(n + SR)
rng = np.random.default_rng(7)

def add(sound, t, gain):
    i = int(t * SR)
    bed[i:i + len(sound)] += sound[: max(0, len(bed) - i)] * gain

t = np.arange(int(0.07 * SR)) / SR
pop = np.sin(2 * np.pi * (1100 - 5000 * t) * t) * np.exp(-t * 70)
m = int(0.22 * SR)
noise = np.convolve(rng.standard_normal(m), np.ones(24) / 24, "same")
whoosh = noise * np.hanning(m) / np.abs(noise).max()
tb = np.arange(int(0.32 * SR)) / SR
boom = np.sin(2 * np.pi * (95 - 90 * tb) * tb) * np.exp(-tb * 13)
boom[: int(0.012 * SR)] += rng.standard_normal(int(0.012 * SR)) * 0.5
for o in ev["wipes"]:
    add(whoosh, max(0, o - 0.1), 0.13)
for o in ev["pops"]:
    add(pop, o, 0.05)
for o in ev["slams"]:
    add(boom, o, 0.16)
    add(whoosh, max(0, o - 0.05), 0.05)
bed = np.int16(np.clip(bed[:n], -1, 1) * 32767)
sfx = out + ".sfx.wav"
with wave.open(sfx, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(bed.tobytes())

dur = n / SR
fmt = "aformat=sample_rates=48000:channel_layouts=stereo"
mix = (f"[0:a]{fmt},asplit[vk][vm];[1:a]{fmt}[s];"
       f"[2:a]{fmt},atrim={music_start}:{float(music_start) + dur:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.25,afade=t=out:st={dur - 2.2:.3f}:d=2.2,volume=-22dB[b0];"
       "[b0][vk]sidechaincompress=threshold=0.03:ratio=5:attack=25:release=350[b];"
       "[vm][s][b]amix=inputs=3:normalize=0[m];[m]")
first = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", voice, "-i", sfx, "-i", music, "-filter_complex",
                        mix + "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
s = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", first, re.S).group())
ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:measured_I={s['input_i']}:measured_TP={s['input_tp']}:"
      f"measured_LRA={s['input_lra']}:measured_thresh={s['input_thresh']}:offset={s['target_offset']},aresample=48000")
subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", voice, "-i", sfx, "-i", music, "-i", video, "-filter_complex", mix + ln + "[a]",
                "-map", "3:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-movflags", "+faststart", "-shortest", out], check=True)
