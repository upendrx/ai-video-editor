#!/usr/bin/env python3
"""Spell the captions the way the script does (no AI): aligns build/words.json to the [CAM]/[READ] lines of
01-script/script.md and writes build/words-fixed.json, which tools/render_graphics.mjs uses for the captions.
  python3 tools/fix_captions.py videos/<ep> [--build build]
Words that match keep the script's spelling, capitals and punctuation ("hugging face" -> "Hugging Face,").
Short mis-hearings inside a matched run take the script words ("rush" -> "Rust", "he pews" -> "Heap use"),
but only when a heard word never occurs in the script and sounds close; real re-phrasings stay as said.
Numbers you spoke stay as digits, and ad-libs that are not in the script stay as heard.
After that, 03-edit/caption-fixes.txt ("wrong words => right words", one per line) is applied by the renderer.
"""
import difflib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_SWAP = 4  # longest mis-heard run replaced from the script


def norm(w):
    return re.sub(r"[^a-z0-9']", "", w.lower().replace("’", "'"))


def script_words(md):
    out = []
    for line in md.read_text().splitlines():
        m = re.match(r"\s*>\s*\[(?:CAM|READ)\]\s*(.*)", line)
        if m:
            text = re.sub(r"[*`_]", "", m.group(1)).replace("’", "'")
            out += [w for w in text.split() if norm(w)]
    return out


def main():
    a = sys.argv[1:]
    ep = (ROOT / a[0]).resolve() if not Path(a[0]).is_absolute() else Path(a[0])
    build = ep / "03-edit" / (a[a.index("--build") + 1] if "--build" in a else "build")
    words = json.load(open(build / "words.json"))
    script = script_words(ep / "01-script" / "script.md")
    if not script:
        sys.exit("no [CAM]/[READ] lines in the script; captions left as heard")
    A, B = [norm(w[0]) for w in words], [norm(w) for w in script]
    known = set(B)
    out, swapped, kept = [], 0, 0
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, A, B, autojunk=False).get_opcodes():
        seg = words[i1:i2]
        if op == "equal":
            out += [[script[j1 + k], w[1], w[2]] for k, w in enumerate(seg)]
        elif (op == "replace" and i2 - i1 <= MAX_SWAP and j2 - j1 <= MAX_SWAP
              and not any(re.search(r"\d", w[0]) for w in seg)
              and any(x not in known for x in A[i1:i2])  # a word the script never uses: mis-heard, not re-phrased
              and difflib.SequenceMatcher(None, "".join(A[i1:i2]), "".join(B[j1:j2])).ratio() >= 0.4):
            t0, t1 = seg[0][1], seg[-1][2]
            step = (t1 - t0) / (j2 - j1)
            out += [[script[j1 + k], t0 + k * step, t0 + (k + 1) * step] for k in range(j2 - j1)]
            swapped += 1
            print(f"  {' '.join(w[0] for w in seg)!r} -> {' '.join(script[j1:j2])!r}")
        else:  # deleted script words need no caption; ad-libs and numbers stay as heard
            out += seg; kept += len(seg)
    json.dump(out, open(build / "words-fixed.json", "w"))
    print(f"wrote {build / 'words-fixed.json'}: {swapped} mis-hearings fixed from the script, {kept} words kept as heard")


if __name__ == "__main__":
    main()
