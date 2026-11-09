#!/usr/bin/env python3
"""Second look at doubtful picks: re-transcribe a few seconds around each one with a bigger model and re-place the cut.

  ~/.venvs/rustai/bin/python tools/refine_takes.py PICKS.json SESSION48.wav [--model medium.en] [--all]

A long retake session makes faster-whisper merge 10-20 s of repeats into one segment, and its word times drift there.
For every pick that matched weakly (< 0.93), runs far longer than its words need, or was not found, this cuts the
window around it (from the end of the previous pick to the start of the next one), transcribes only that, and takes the
LATEST complete match of the sentence inside it. Picks are rewritten in place; "refined" marks the ones it changed.
"""
import json, re, subprocess, sys
import numpy as np
from faster_whisper import WhisperModel
from rapidfuzz import fuzz
from post_record import words_norm as norm     # same spelling rules as the take picker

picks_p, wav = sys.argv[1:3]
opt = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
picks = json.load(open(picks_p))
pcm = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", wav, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                                   capture_output=True, check=True).stdout, np.float32)
model = WhisperModel(opt("--model", "medium.en"), device="cpu", compute_type="int8")


def doubtful(p):
    if not p.get("found"): return True
    n = len(norm(p["text"]).split())
    return "--all" in sys.argv or p["score"] < 0.93 or (p["end"] - p["start"]) > 0.42 * n + 1.2


for i, p in enumerate(picks):
    if not doubtful(p): continue
    prev = next((q for q in reversed(picks[:i]) if q.get("found") and not q.get("drop")), None)
    nxt = next((q for q in picks[i + 1:] if q.get("found")), None)
    lo = prev["end"] - 0.15 if prev else max(0, (p.get("start") or 0) - 20)
    hi = nxt["start"] + 0.15 if nxt else (p.get("end") or lo) + 20
    if p.get("found"): lo, hi = min(lo, p["start"] - 3), max(hi, p["end"] + 1.5)
    if prev: lo = max(lo, prev["end"] - 0.15)
    if nxt: hi = min(hi, nxt["start"] + 0.15)
    if hi - lo < 0.4 or hi - lo > 60: continue
    segs, _ = model.transcribe(pcm[int(lo * 16000): int(hi * 16000)], language="en", word_timestamps=True,
                               condition_on_previous_text=False, initial_prompt=p["text"])
    ws = [(w.start + lo, w.end + lo, w.word) for s in segs for w in s.words]
    toks = [norm(w[2]) for w in ws]
    ref = norm(p["text"]); rw = ref.split(); n = len(rw)
    cands = []
    for a in range(len(ws)):
        if not toks[a]: continue
        for k in range(max(1, n - 2), n + 4):
            b = a + k
            if b > len(ws): break
            hyp = " ".join(t for t in toks[a:b] if t); sc = fuzz.ratio(ref, hyp) / 100
            first, lastw = toks[a].split()[0], (toks[b - 1].split() or [""])[-1]
            if sc >= 0.75 and fuzz.ratio(rw[0], first) >= 75 and fuzz.ratio(rw[-1], lastw) >= 75:
                cands.append((sc, a, b))
    if not cands:
        print(f"  no match  {p['text'][:50]!r} in {lo:.1f}-{hi:.1f}: {' '.join(w[2].strip() for w in ws)[:90]!r}"); continue
    best = max(c[0] for c in cands)
    sc, a, b = max((c for c in cands if c[0] >= best - 0.08), key=lambda c: (ws[c[1]][0], c[0]))
    old = (p.get("start"), p.get("end"))
    if p.get("found") and sc < p["score"] - 0.02:
        print(f"  kept      {p['text'][:45]} (refined match {sc:.2f} is weaker than {p['score']})"); continue
    p.update(found=True, score=round(sc, 3), start=round(ws[a][0], 2), end=round(ws[b - 1][1], 2), refined=True,
             prev_end=round(ws[a - 1][1], 2) if a else None, next_start=round(ws[b][0], 2) if b < len(ws) else None,
             heard=" ".join(w[2].strip() for w in ws[a:b]))
    print(f"  {old[0]}-{old[1]} -> {p['start']}-{p['end']} {sc:.2f} | {p['text'][:45]} | {p['heard'][:60]}")
json.dump(picks, open(picks_p, "w"), indent=1)
