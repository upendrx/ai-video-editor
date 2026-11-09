#!/usr/bin/env python3
"""Check the finished voice cut against the script: every extra, missing or doubled word, with its time in the cut.

  ~/.venvs/rustai/bin/python tools/check_cut.py videos/NNN-slug [--retranscribe]

Transcribes 03-edit/build/voice.wav again (cut.tr.json, kept), aligns its words to the script ([CAM]/[READ] lines)
and prints insertions (false starts, "I I", a word said twice across a cut), deletions (a word lost at a cut edge)
and replacements. Whisper mishears a few names, so read the list, do not trust it blindly.
"""
import difflib, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from post_record import script_lines, words_norm   # same spelling rules as the take picker

v = Path(sys.argv[1]).resolve(); b = v / "03-edit/build"
tr = b / "cut.tr.json"
if "--retranscribe" in sys.argv or not tr.exists() or tr.stat().st_mtime < (b / "voice.wav").stat().st_mtime:
    subprocess.run([sys.executable, ROOT / "tools/transcribe.py", b / "voice.wav", tr, "--model", "medium.en"], check=True)
heard = []                                          # (normalised token, start s)
for seg in json.load(open(tr)):
    for w in seg["w"]:
        for t in words_norm(w[2]).split(): heard.append((t, w[0]))
ref = []                                            # (token, script line #)
for L in script_lines(v / "01-script/script.md"):
    for t in words_norm(L["text"]).split(): ref.append((t, L["line"]))

sm = difflib.SequenceMatcher(None, [r[0] for r in ref], [h[0] for h in heard], autojunk=False)
issues = []
for op, i1, i2, j1, j2 in sm.get_opcodes():
    if op == "equal": continue
    t = heard[j1][1] if j1 < len(heard) else heard[-1][1]
    ln = ref[min(i1, len(ref) - 1)][1]
    said = " ".join(h[0] for h in heard[j1:j2]); want = " ".join(r[0] for r in ref[i1:i2])
    doubled = op == "insert" and said and (said in " ".join(h[0] for h in heard[max(0, j1 - 6):j1]) or said in want)
    issues.append({"t": round(t, 2), "line": ln, "op": "DOUBLED" if doubled else op.upper(), "said": said, "script": want})
print(f"{len(ref)} script words, {len(heard)} heard, match {sm.ratio():.3f}")
for x in issues:
    print(f"{x['t']:8.2f}s line {x['line']:>3} {x['op']:<8} said: {x['said']!r:<40} script: {x['script']!r}")
json.dump(issues, open(b / "cut_check.json", "w"), indent=1)
