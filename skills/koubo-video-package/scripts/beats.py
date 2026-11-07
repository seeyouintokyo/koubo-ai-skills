import subprocess, sys
import numpy as np
music = sys.argv[1]
raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", music, "-t", "70", "-ac", "1", "-ar", "11025", "-f", "f32le", "-"], capture_output=True).stdout
x = np.frombuffer(raw, np.float32)
hop = 128; win = 512; sr = 11025
frames = np.lib.stride_tricks.sliding_window_view(x, win)[::hop] * np.hanning(win)
S = np.abs(np.fft.rfft(frames, axis=1))
flux = np.maximum(0, np.diff(np.log1p(S), axis=0)).sum(1)
flux = flux - np.convolve(flux, np.ones(64) / 64, "same")
flux = np.maximum(flux, 0)
fr = sr / hop
ac = np.correlate(flux, flux, "full")[len(flux) - 1:]
lo, hi = int(fr * 60 / 180), int(fr * 60 / 70)
lag = lo + int(np.argmax(ac[lo:hi]))
bpm = 60 * fr / lag
best = max(range(lag), key=lambda p: flux[p::lag].sum())
print("bpm %.1f first_beat %.3f strength %.2f" % (bpm, best / fr, flux[best::lag].mean() / flux.mean()))
for a in (0, 10, 20, 30, 40):
    seg = flux[int(a * fr):int((a + 10) * fr)]
    print(a, "energy %.2f" % seg.mean())
