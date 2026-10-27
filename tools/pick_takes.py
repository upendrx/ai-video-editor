#!/usr/bin/env python3
"""Pick the best take of every script sentence from a word-timestamped transcript of a many-retake recording.

  python3 tools/pick_takes.py SCRIPT.md TRANSCRIPT.json OUT.json [--skip-hooks BC]

SCRIPT.md: '> [CAM]/[READ] sentence' lines under '## ' headings .
TRANSCRIPT.json: faster-whisper output [{s,e,t,w:[[start,end,word],...]}].
For each sentence: slide a word window over the transcript, score text similarity (rapidfuzz), penalise windows with
long internal pauses (a flub/restart), take the best score and, among near-ties, the LATEST (speakers retake until right).
Needs: rapidfuzz, num2words.
"""
import json, re, sys
from rapidfuzz import fuzz
from num2words import num2words

def norm(s):
    s = s.lower().replace("%", " percent ")
    s = re.sub(r"(\d+)\.(\d+)", lambda m: num2words(int(m[1])) + " point " + " ".join(num2words(int(c)) for c in m[2]), s)
    s = re.sub(r"\d+", lambda m: num2words(int(m[0])), s)
    s = re.sub(r"[^a-z ]", " ", s.replace("-", " "))
    return re.sub(r"\s+", " ", s).strip()

def load_script(path, skip_hooks):
    out, sec = [], ""
    for l in open(path).read().splitlines():
        if l.startswith("## "): sec = l[3:]
        if l.startswith("**Hook"): hook = l[7:8]
        if l.startswith("> ["):
            m = re.match(r"> \[(CAM|READ)\] (.*)", l)
            if sec.startswith("HOOK") and hook in skip_hooks: continue
            for sent in re.split(r"(?<=[.!?])\s+", m[2]):
                out.append({"sec": sec.split("(")[0].strip(), "mode": m[1], "text": sent})
    return out

def main():
    script, tr, outp = sys.argv[1:4]
    skip = sys.argv[sys.argv.index("--skip-hooks") + 1] if "--skip-hooks" in sys.argv else ""
    words = [w for seg in json.load(open(tr)) for w in seg["w"]]
    toks = [norm(w[2]) for w in words]
    res = []
    for u in load_script(script, skip):
        ref = norm(u["text"]); n = len(ref.split())
        cands = []
        for i in range(len(words)):
            if not toks[i]: continue
            for k in range(max(2, n - 3), n + 7):
                j = i + k
                if j > len(words): break
                hyp = " ".join(t for t in toks[i:j] if t)
                sc = fuzz.ratio(ref, hyp) / 100
                if sc < 0.8: continue
                gaps = max((words[x + 1][0] - words[x][1] for x in range(i, j - 1)), default=0)
                slow = max((words[x][1] - words[x][0] for x in range(i, j)), default=0)  # a word held >1 s = hesitation
                sc -= 0.06 * max(0, gaps - 0.7) + 0.06 * max(0, slow - 1.0)
                cands.append((sc, words[i][0], words[j - 1][1], i, j))
        cands.sort(reverse=True)
        if not cands: res.append({**u, "found": False}); continue
        best = cands[0][0]
        pool = [c for c in cands if c[0] >= best - 0.04]
        pick = max(pool, key=lambda c: c[1])
        res.append({**u, "found": True, "score": round(pick[0], 3), "start": pick[1], "end": pick[2],
                    "heard": " ".join(w[2].strip() for w in words[pick[3]:pick[4]])})
    json.dump(res, open(outp, "w"), indent=1)
    for r in res:
        print(r["mode"], f'{r.get("start","-"):>7} {r.get("end","-"):>7} {r.get("score","-")}', "|", r["text"][:50], "|", (r.get("heard") or "")[:50])

main()
