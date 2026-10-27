#!/usr/bin/env python3
"""Cut the chosen takes (pick_takes.py output) out of the long mic recording and join them into one voice track.

  python3 tools/assemble_audio.py MIC48.wav picks.json OUT_PREFIX [--override '{"text start": [t0, t1]}'] [--gap 0.2] [--sec-gap 0.4]

Writes OUT_PREFIX.wav (raw joined, 48 kHz mono) and OUT_PREFIX.timeline.json:
  [{text, mode, sec, mic0, mic1, t0, t1}]  t0/t1 = position in the joined track, mic0/mic1 = position in the mic file.
Cut points are snapped to the quietest 10 ms near the transcript time (transcript times are only +-0.15 s accurate),
edges get a 12 ms fade, and gaps are filled with room tone taken from the quietest half second of the recording.
"""
import json, sys, wave
import numpy as np

SR = 48000
mic_p, picks_p, out = sys.argv[1:4]
over = json.loads(sys.argv[sys.argv.index("--override") + 1]) if "--override" in sys.argv else {}
gap = float(sys.argv[sys.argv.index("--gap") + 1]) if "--gap" in sys.argv else 0.2
sgap = float(sys.argv[sys.argv.index("--sec-gap") + 1]) if "--sec-gap" in sys.argv else 0.4

w = wave.open(mic_p); assert w.getframerate() == SR
a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, w.getnchannels())[:, 0].astype(np.float32) / 32768
fr = SR // 100
env = np.sqrt((a[: len(a) // fr * fr].reshape(-1, fr) ** 2).mean(1))          # 10 ms RMS

# room tone: quietest 0.5 s window (50 frames) that is not digital silence
cs = np.convolve(env, np.ones(50) / 50, "valid"); cs[cs < 1e-5] = 1
rt0 = int(np.argmin(cs)) * fr; tone = a[rt0: rt0 + SR // 2].copy()
tone *= np.hanning(len(tone)) ** 0.25

def snap(t, lo, hi):
    i0, i1 = int((t + lo) * 100), int((t + hi) * 100)
    i = i0 + int(np.argmin(env[i0:i1 + 1]))
    return i / 100

# speech bursts: pauses = runs of >= 80 ms below 4x the noise floor; cut at the pause edge, not mid-word
thr = 4 * np.percentile(env, 5)
quiet = env < thr
pauses, i = [], 0
while i < len(quiet):
    if quiet[i]:
        j = i
        while j < len(quiet) and quiet[j]: j += 1
        if j - i >= 8: pauses.append((i / 100, j / 100))
        i = j
    else: i += 1
pstart = np.array([p[0] for p in pauses]); pend = np.array([p[1] for p in pauses])

def snap_start(t):                    # speech onset = end of the last pause before the word (within 0.5 s)
    k = np.searchsorted(pend, t + 0.12) - 1
    if k >= 0 and t - pend[k] <= 0.5: return max(pend[k] - 0.04, pstart[k])
    return snap(t, -0.3, 0.0)

def snap_end(t):                      # speech offset = start of the next pause after the word (within 0.5 s)
    k = np.searchsorted(pstart, t - 0.12)
    if k < len(pstart) and pstart[k] - t <= 0.5: return min(pstart[k] + 0.06, pend[k])
    return snap(t, -0.03, 0.16)

def room(n):
    out = np.zeros(n, np.float32)
    for k in range(0, n, len(tone) // 2):
        seg = tone[: n - k]; out[k: k + len(seg)] += seg[: len(out) - k]
    return out

picks = json.load(open(picks_p)); parts, tl, t = [], [], 0.0
prev_sec = None
# resolve overrides, then merge sentences that were spoken back to back in the same take (keeps natural flow, no cut mid-speech)
units = []
for p in picks:
    key = next((k for k in over if p["text"].startswith(k)), None)
    if key and over[key] is None: continue                           # null = drop this sentence
    lit = isinstance(over.get(key), list)                              # [t0, t1] = literal times, no snapping
    s, e = (over[key] if lit else (p.get("start"), p.get("end")))
    if s is None: print("MISSING", p["text"]); continue
    q = dict(p, start=s, end=e, delta=over[key] if key and not lit else {})
    key = key if lit else None
    u = units[-1] if units else None
    if u and not key and not u.get("fixed") and u["sec"] == q["sec"] and u["start"] <= q["start"] < u["end"] + 1.0 and q["end"] > u["end"]:
        u["end"] = q["end"]; u["text"] += " " + q["text"]
    else:
        q["fixed"] = bool(key); units.append(q)
for p in units:
    s, e = p["start"], p["end"]
    s2, e2 = (s, e) if p.get("fixed") else (snap_start(s), snap_end(e))
    s2 += p.get("delta", {}).get("ds", 0); e2 += p.get("delta", {}).get("de", 0)
    seg = a[int(s2 * SR): int(e2 * SR)].copy(); f = int(0.012 * SR)
    seg[:f] *= np.linspace(0, 1, f); seg[-f:] *= np.linspace(1, 0, f)
    if parts:
        g = room(int((sgap if p["sec"] != prev_sec else gap) * SR)); parts.append(g); t += len(g) / SR
    tl.append({"text": p["text"], "mode": p["mode"], "sec": p["sec"], "mic0": round(s2, 3), "mic1": round(e2, 3),
               "t0": round(t, 3), "t1": round(t + len(seg) / SR, 3)})
    parts.append(seg); t += len(seg) / SR; prev_sec = p["sec"]

y = np.concatenate(parts)
with wave.open(out + ".wav", "wb") as o:
    o.setnchannels(1); o.setsampwidth(2); o.setframerate(SR); o.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())
json.dump(tl, open(out + ".timeline.json", "w"), indent=1)
print(f"{len(tl)} units, {t:.1f} s -> {out}.wav")
