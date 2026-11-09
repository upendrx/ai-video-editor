#!/usr/bin/env python3
"""Pick the best take of every script sentence from a word-timestamped transcript of a many-retake recording.

  python3 tools/pick_takes.py SCRIPT.md TRANSCRIPT.json OUT.json [--skip-hooks BC] [--only cam|read] [--last]

SCRIPT.md: '> [CAM]/[READ] sentence' lines under '## ' headings (see series/rust-in-ai/md_to_teleprompter.py).
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
    s = re.sub(r"(?<=[a-z])\.(?=[a-z])", " dot ", s)          # whisper writes "torch.matmul" for "torch dot matmul"
    s = re.sub(r"(\d+)\.(\d+)", lambda m: num2words(int(m[1])) + " point " + " ".join(num2words(int(c)) for c in m[2]), s)
    s = re.sub(r"\d+", lambda m: num2words(int(m[0])), s)
    s = re.sub(r"[^a-z ]", " ", s.replace("-", " "))
    return re.sub(r"\s+", " ", s).strip()

def load_script(path, skip_hooks):
    out, sec, line = [], "", 0
    for l in open(path).read().splitlines():
        if l.startswith("## "): sec = l[3:]
        if l.startswith("**Hook"): hook = l[7:8]
        if l.startswith("> ["):
            m = re.match(r"> \[(CAM|READ)\] (.*)", l); line += 1     # line = row # in shot-list.md
            if sec.startswith("HOOK") and hook in skip_hooks: continue
            for sent in re.split(r"(?<=[.!?])\s+", m[2]):
                out.append({"sec": sec.split("(")[0].strip(), "mode": m[1], "text": sent, "line": line})
    return out

def main():
    script, tr, outp = sys.argv[1:4]
    skip = sys.argv[sys.argv.index("--skip-hooks") + 1] if "--skip-hooks" in sys.argv else ""
    only = sys.argv[sys.argv.index("--only") + 1].upper() if "--only" in sys.argv else None   # CAM or READ
    last = "--last" in sys.argv                                    # prefer the last complete take over a slightly better earlier one
    words = [w for seg in json.load(open(tr)) for w in seg["w"]]
    toks = [norm(w[2]) for w in words]
    units = [u for u in load_script(script, skip) if not (only and u["mode"] != only)]
    allc = []
    for u in units:
        ref = norm(u["text"]); n = len(ref.split())
        cands = []
        for i in range(len(words)):
            if not toks[i]: continue
            for k in range(max(1, n - 3), n + 7):                   # 1-word sentences ("Candle.") too
                j = i + k
                if j > len(words): break
                hyp = " ".join(t for t in toks[i:j] if t)
                sc = fuzz.ratio(ref, hyp) / 100
                if sc < (0.7 if last else 0.8): continue
                gaps = max((words[x + 1][0] - words[x][1] for x in range(i, j - 1)), default=0)
                slow = max((words[x][1] - words[x][0] for x in range(i, j)), default=0)  # a word held >1 s = hesitation
                sc -= 0.06 * max(0, gaps - 0.7) + 0.06 * max(0, slow - 1.0)
                cands.append((sc, words[i][0], words[j - 1][1], i, j))
        cands.sort(reverse=True)
        allc.append((ref, n, cands))

    def choose(k, lo=-1e9, hi=1e9, gbest=False):
        ref, n, cands = allc[k]
        cs = [c for c in cands if lo <= c[1] and c[2] <= hi]
        if not cs: return None
        best = cands[0][0] if gbest else cs[0][0]
        pool = [c for c in cs if c[0] >= best - 0.04]
        if last:     # the speaker retakes until it is right: latest complete take (same first and last word) close to the best
            rw = ref.split()
            edge = lambda c: (fuzz.ratio(rw[0], toks[c[3]]) >= 75 and fuzz.ratio(rw[-1], toks[c[4] - 1].split()[-1] if toks[c[4] - 1] else "") >= 75)
            pool = ([c for c in cs if c[0] >= best - 0.10 and edge(c)] or [c for c in cs if c[0] >= best - 0.20 and edge(c)]
                    or ([] if gbest else pool))
            if not pool: return None
        return max(pool, key=lambda c: (c[1], c[0]))

    picks = [None] * len(units)
    if last:
        # takes come in script order, and the last complete take of a line comes before the takes of the next line.
        # Walk the script backwards: every sentence gets its latest complete take that ends before the take chosen
        # for the sentence after it. Long sentences first (anchors), then short ones ("One thread.") only inside the
        # gap between their neighbours, so they cannot borrow the same words from another paragraph or reuse audio.
        anchors = [k for k in range(len(units)) if allc[k][1] >= 5]
        hi = 1e9
        for k in reversed(anchors):
            picks[k] = choose(k, -1e9, hi, gbest=True)
            if picks[k]: hi = picks[k][1] + 0.1
        hi = 1e9
        for k in reversed(range(len(units))):
            if picks[k]: hi = picks[k][1] + 0.1; continue
            lo = next((picks[k2][2] - 0.1 for k2 in range(k - 1, -1, -1) if picks[k2]), -1e9)
            picks[k] = choose(k, lo, hi)
            if picks[k]: hi = picks[k][1] + 0.1
    else:
        picks = [choose(k) for k in range(len(units))]
    res = []
    for u, pick in zip(units, picks):
        if not pick: res.append({**u, "found": False}); continue
        res.append({**u, "found": True, "score": round(pick[0], 3), "start": pick[1], "end": pick[2],
                    "prev_end": words[pick[3] - 1][1] if pick[3] else None, "next_start": words[pick[4]][0] if pick[4] < len(words) else None,
                    "heard": " ".join(w[2].strip() for w in words[pick[3]:pick[4]])})
    json.dump(res, open(outp, "w"), indent=1)
    for r in res:
        print(r["mode"], f'{r.get("start","-"):>7} {r.get("end","-"):>7} {r.get("score","-")}', "|", r["text"][:50], "|", (r.get("heard") or "")[:50])

main()
