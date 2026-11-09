#!/usr/bin/env python3
"""Cut the chosen takes (pick_takes.py output) out of the long mic recording and join them into one voice track.

  python3 tools/assemble_audio.py MIC48.wav picks.json OUT_PREFIX [--override '{"text start": [t0, t1]}'] [--gap 0.2] [--sec-gap 0.4]

Writes OUT_PREFIX.wav (raw joined, 48 kHz mono) and OUT_PREFIX.timeline.json:
  [{text, mode, sec, mic0, mic1, t0, t1, lines}]  lines = [[script line #, start in joined track], ...]  t0/t1 = position in the joined track, mic0/mic1 = position in the mic file.
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
# --level DB: bring every unit's speech to the same level (RMS of its voiced 10 ms frames, dBFS). Two sessions recorded at
# different distances/gains (009: camera session 17 dB louder than the voice-over) then sound like one recording.
LEVEL = float(sys.argv[sys.argv.index("--level") + 1]) if "--level" in sys.argv else None
CAM_OFF = float(sys.argv[sys.argv.index("--cam-offset") + 1]) if "--cam-offset" in sys.argv else 0.0   # dB, camera units vs voice-over (room sound makes them read louder)

def unit_gain(s, e):
    if LEVEL is None: return 1.0
    x = a[int(s * SR): int(e * SR)]; n = len(x) // 480 * 480
    if n < 4800: return 1.0
    r = np.sqrt((x[:n].reshape(-1, 480) ** 2).mean(1)); v = r[r > 0.1 * r.max()]
    db = 20 * np.log10(np.sqrt((v ** 2).mean()) + 1e-9)
    return float(10 ** (np.clip(LEVEL - db, -12, 26) / 20))

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
prev_e = -1.0
prev_sec = None
# resolve overrides, then merge sentences that were spoken back to back in the same take (keeps natural flow, no cut mid-speech)
units = []
for p in picks:
    key = next((k for k in over if p["text"].startswith(k)), None)
    if key and over[key] is None: continue                           # null = drop this sentence
    lit = isinstance(over.get(key), list)                              # [t0, t1] = literal times, no snapping
    if lit and over[key] and isinstance(over[key][0], list):           # [[t0, t1], [t2, t3]] = literal pieces joined (skips a stall inside the take)
        for n, (s_, e_) in enumerate(over[key]):
            units.append(dict(p, start=s_, end=e_, delta={}, fixed=True, subs=[(p.get("line"), s_)] if n == 0 else []))
        continue
    s, e = (over[key] if lit else (p.get("start"), p.get("end")))
    if s is None: print("MISSING", p["text"]); continue
    q = dict(p, start=s, end=e, delta=over[key] if key and not lit else {})
    key = key if lit else None
    u = units[-1] if units else None
    said_between = q.get("prev_end") is not None and q["prev_end"] > u["end"] + 0.1 if u else False   # a retake word or false start sits in the gap
    if u and not key and not u.get("fixed") and not said_between and u["sec"] == q["sec"] and u["start"] <= q["start"] < u["end"] + 1.0 and q["end"] > u["end"]:
        u["end"] = q["end"]; u["text"] += " " + q["text"]; u["subs"].append((q.get("line"), q["start"])); u["next_start"] = q.get("next_start")
    else:
        q["fixed"] = bool(key); q["subs"] = [(q.get("line"), q["start"])]; units.append(q)
tighten = "--keep-pauses" not in sys.argv
PAUSE = 0.7                            # a quiet run longer than this inside a voice-over unit is shortened to about 0.45 s (the 0.2 s gap + 0.12 s kept each side)
def spans_of(p, s2, e2):
    """Trim silence at both ends (dead air before the first word / after the last), and cut long stalls out of the middle.
    Levels are relative to the loudest speech inside the unit (-16 dB ~ quiet), so a noisy room or a quiet voice both work."""
    if not tighten: return [(s2, e2)]
    i0, i1 = int(s2 * 100), int(e2 * 100); e = env[i0:i1]
    if len(e) < 30: return [(s2, e2)]
    ref = np.percentile(e, 90); loud = np.where(e > 0.16 * ref)[0]
    if len(loud) == 0: return [(s2, e2)]
    s3 = max(s2, (i0 + loud[0]) / 100 - 0.10); e3 = min(e2, (i0 + loud[-1] + 1) / 100 + 0.14)
    lim = 0.9 if p["mode"] == "CAM" else PAUSE     # camera takes only lose long stalls (post_record.py cuts the picture at each unit edge, so it stays in step)
    out, cur, k = [], s3, int(loud[0])
    quiet = e < 0.16 * ref
    while k <= loud[-1]:
        if quiet[k]:
            j = k
            while j <= loud[-1] and quiet[j]: j += 1
            if (j - k) / 100 >= lim and (i0 + k) / 100 > cur + 0.15 and (i0 + j) / 100 < e3 - 0.15:
                out.append((cur, (i0 + k) / 100 + 0.12)); cur = (i0 + j) / 100 - 0.12
            k = j
        else: k += 1
    out.append((cur, e3)); return out

for p in units:
    s, e = p["start"], p["end"]
    ug = unit_gain(s, e) * (10 ** (CAM_OFF / 20) if p["mode"] == "CAM" and LEVEL is not None else 1)
    s2, e2 = (s, e) if p.get("fixed") else (snap_start(s), snap_end(e))
    if not p.get("fixed"):            # never reach into the word said just before / after the take (a false start "I", "so", the retake)
        if p.get("prev_end") is not None and s - 0.6 < p["prev_end"] < s: s2 = max(s2, min(p["prev_end"] + 0.03, s - 0.02))
        if p.get("next_start") is not None and e < p["next_start"] < e + 0.6: e2 = min(e2, max(p["next_start"] - 0.03, e + 0.02))
    s2 += p.get("delta", {}).get("ds", 0); e2 += p.get("delta", {}).get("de", 0)
    pe = None                          # end of the previous piece of this unit: a line that starts inside a shortened stall belongs to the next piece
    for k, (s3, e3) in enumerate(spans_of(p, s2, e2)):
        # continues the previous piece in the mic (back to back, or a short pause that is really silent): keep the real
        # pause instead of room tone, so a sentence said in one breath (and its camera shot) is not cut apart
        quiet_gap = 0 <= s3 - prev_e < 0.6 and (s3 - prev_e < 0.06 or env[int(prev_e * 100): int(s3 * 100) + 1].max() < 2 * thr)
        joined = bool(parts) and quiet_gap
        if joined: s3 = prev_e
        seg = a[int(s3 * SR): int(e3 * SR)] * ug; f = int(0.012 * SR)
        if not joined:
            seg[:f] *= np.linspace(0, 1, f)
            if parts: parts[-1][-f:] *= np.linspace(1, 0, f)   # fade out the previous piece only where a gap follows
        if not joined and parts:
            g = room(int((sgap if p["sec"] != prev_sec else gap) * SR)) * (ug if LEVEL is not None else 1); parts.append(g); t += len(g) / SR
        subs = [(ln, st) for ln, st in p["subs"] if (s3 - 0.05 if pe is None else pe) <= st < e3 or (k == 0 and st < s3)]
        pe = e3
        tl.append({"text": p["text"], "mode": p["mode"], "sec": p["sec"], "mic0": round(s3, 3), "mic1": round(e3, 3),
                   "t0": round(t, 3), "t1": round(t + len(seg) / SR, 3),
                   "lines": [[ln, round(t + max(st - s3, 0), 3)] for ln, st in subs]})
        parts.append(seg); t += len(seg) / SR; prev_sec = p["sec"]; prev_e = e3

parts[-1][-int(0.012 * SR):] *= np.linspace(1, 0, int(0.012 * SR))
y = np.concatenate(parts)
with wave.open(out + ".wav", "wb") as o:
    o.setnchannels(1); o.setsampwidth(2); o.setframerate(SR); o.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())
json.dump(tl, open(out + ".timeline.json", "w"), indent=1)
print(f"{len(tl)} units, {t:.1f} s -> {out}.wav")
