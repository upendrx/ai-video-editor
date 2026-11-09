#!/usr/bin/env python3
"""Build a teleprompter page from a script markdown (## headings, '> ' spoken lines; prefix [CAM] = on camera, [READ] = voice-over read from screen).
  python3 series/rust-in-ai/md_to_teleprompter.py videos/002-.../01-script/script-v2.md "Ep 1 v2" out.html
  python3 series/rust-in-ai/md_to_teleprompter.py SCRIPT.md "Ep 7" teleprompter-cam.html --only cam     # camera session
  python3 series/rust-in-ai/md_to_teleprompter.py SCRIPT.md "Ep 7" teleprompter-voice.html --only read  # voice session
--only cam: CAM lines only, numbered C1, C2... with the line before each as grey context (retake-friendly, short clips).
--only read: READ lines only; CAM lines stay as grey context so the voice flows into them. CAM numbers match in both pages.
"""
import json, re, sys
from pathlib import Path
args = [a for a in sys.argv[1:] if a != "--only"]
only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
if only: args.remove(only)
src, short, out = Path(args[0]), args[1], Path(args[2])
intro = {None: "say the episode number, pause 2 s, clap once, then start",
         "cam": "CAMERA SESSION · phone + Mac mic both running · clap at the start of every phone clip · say the number once per new line (\"cam one\"), pause 2 s, say the line · retakes: just pause 2 s and say the line again, no number (the last good take wins) · restart the phone clip before 8 min",
         "read": "VOICE SESSION · Mac mic only, no camera · clap once, then read calmly · if you trip, pause 2 s and say the whole sentence again"}[only]
lines = [{"t": "sec", "x": f"{short} · {intro}"}, {"t": "gap"}]
cam_n = 0
for raw in src.read_text().splitlines():
    if raw.startswith("## Check"): break
    if raw.startswith("## "):
        if lines[-1]["t"] != "gap": lines.append({"t": "gap"})
        lines.append({"t": "sec", "x": re.sub(r"\s*\(.*?\)", "", raw[3:]).strip()})
    elif raw.startswith("**Hook"):
        lines.append({"t": "sec", "x": re.sub(r"[*:]", "", raw).strip()})
    elif raw.startswith("**Visual plan:**") and only != "cam":
        lines.append({"t": "vis", "x": raw.split("**", 2)[2].strip()})
    elif raw.startswith("> "):
        t = raw[2:].strip(); m = None
        mm = re.match(r"\[(CAM|READ)\]\s*", t)
        if mm: m = mm.group(1).lower(); t = t[mm.end():]
        if m == "cam": cam_n += 1; t = f"C{cam_n} · {t}" if only else t
        if only and m != only:
            lines.append({"t": "ctx", "x": t})
        else:
            lines.append({"t": "say", "x": t, **({"m": m} if m else {})})
    elif raw.startswith("#") and not raw.startswith("##"):
        continue
    elif raw.strip() == "" and lines[-1]["t"] == "say":
        lines.append({"t": "gap"})
if only == "cam":
    # Keep only the one context line right before each CAM line, and the section headings that hold CAM lines.
    kept = [l for i, l in enumerate(lines) if l["t"] != "ctx" or (i + 1 < len(lines) and lines[i + 1]["t"] == "say")]
    lines = [l for i, l in enumerate(kept) if l["t"] != "sec" or i < 2 or any(k["t"] == "say" for k in kept[i + 1:next((j for j in range(i + 1, len(kept)) if kept[j]["t"] == "sec"), len(kept))])]
    lines = [l for l in lines if l["t"] != "gap"]
    lines = [x for l in lines for x in ([l, {"t": "gap"}] if l["t"] == "say" else [l])]
while lines and lines[-1]["t"] != "say": lines.pop()
lines += [{"t": "gap"}, {"t": "sec", "x": "End · stay still and silent for 3 seconds"}]
tpl = (Path(__file__).with_name("teleprompter-template.html")).read_text()
out.write_text(tpl.replace("__TITLE__", f"Teleprompter: {short}").replace("__TITLE_JSON__", json.dumps(short)).replace("__LINES_JSON__", json.dumps(lines)))
print(sum(len(l["x"].split()) for l in lines if l["t"] == "say"), "spoken words ->", out)
