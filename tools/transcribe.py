#!/usr/bin/env python3
"""Local, free speech-to-text with word times (faster-whisper). Output is the format pick_takes.py reads.

  ~/.venvs/rustai/bin/python tools/transcribe.py AUDIO OUT.json [--model small.en] [--lang en]

OUT.json: [{s, e, t, w: [[start, end, word], ...]}, ...]
Hinglish recordings: --model small --lang hi (words come out in Devanagari; pick_takes needs English letters,
so for Hinglish scripts use --lang en, which keeps romanised spelling close enough for the fuzzy match).
Setup once: python3 -m venv ~/.venvs/rustai && ~/.venvs/rustai/bin/pip install faster-whisper rapidfuzz num2words numpy
"""
import json, subprocess, sys
import numpy as np
from faster_whisper import WhisperModel

audio, outp = sys.argv[1:3]
opt = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
model = WhisperModel(opt("--model", "small.en"), device="cpu", compute_type="int8")
# decode with ffmpeg (16 kHz mono float), not faster-whisper's own PyAV decoder, which breaks between versions
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", audio, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                     capture_output=True, check=True).stdout
segs, info = model.transcribe(np.frombuffer(pcm, np.float32), language=opt("--lang", "en"), word_timestamps=True,
                              vad_filter=True, vad_parameters={"min_silence_duration_ms": 300},
                              condition_on_previous_text=False)   # retakes repeat text; do not let one take bias the next
out = []
for s in segs:
    out.append({"s": round(s.start, 2), "e": round(s.end, 2), "t": s.text.strip(),
                "w": [[round(w.start, 2), round(w.end, 2), w.word] for w in s.words]})
    print(f"\r{s.end:7.1f} / {info.duration:.0f} s", end="", file=sys.stderr)
json.dump(out, open(outp, "w"), indent=0)
print(f"\n{len(out)} segments -> {outp}", file=sys.stderr)
