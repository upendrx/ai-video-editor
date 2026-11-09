#!/usr/bin/env python3
"""Build the AI Producer render-engine tree for one episode from the kit output of tools/post_record.py.

  python3 tools/aip_root.py videos/NNN-slug INDEX.html   # INDEX.html = the project's own render-engine/index.html, saved locally

Writes 03-edit/build/render-engine/: index.html (the project's scaffold with every kit host mounted: full-cover moments on
track 3, overlays on track 4 above them) and compositions/*.html. Each host gets a readable editor title from its spec.
Captions are added later from build_captions' host_div (see --captions-host).
"""
import json, re, shutil, sys
from pathlib import Path

v = Path(sys.argv[1]).resolve(); b = v / "03-edit/build"; g = b / "graphics"
idx = Path(sys.argv[2]).read_text()
cap = sys.argv[sys.argv.index("--captions-host") + 1] if "--captions-host" in sys.argv else None
out = b / "render-engine"; (out / "compositions").mkdir(parents=True, exist_ok=True)


def title(m):
    t = m.get("label") or m.get("heading") or m.get("title") or m.get("text") or m.get("kicker") or m["type"]
    return re.sub(r"\s+", " ", str(t)).strip()[:40]


hosts = []
for name, track in (("main", 3), ("over", 4)):
    spec = json.loads((b / f"spec_{name}.json").read_text())
    names = {"m-" + re.sub(r"[^a-z0-9-]", "-", m["id"].lower()): title(m) for m in spec["moments"]}
    for line in (g / name / "hosts.html").read_text().splitlines():
        if not line.strip(): continue
        cid = re.search(r'data-composition-id="([^"]+)"', line)[1]
        line = re.sub(r'data-title="[^"]*"', f'data-title="{names.get(cid, cid)}"', line)
        hosts.append(line.replace('data-track-index="3"', f'data-track-index="{track}"'))
        shutil.copy(g / name / "compositions" / f"{cid}.html", out / "compositions" / f"{cid}.html")
if cap: hosts.append("      " + cap.strip())

mark = "<!-- Track 3: Visual moment overlays"
i = idx.index(mark); j = idx.index("-->", i) + 3
idx = idx[:j] + "\n" + "\n".join(hosts) + "\n" + idx[j:]
idx = idx.replace('#stage > .visual-host[data-track-index="3"] { z-index: 10; }',
                  '#stage > .visual-host[data-track-index="3"] { z-index: 10; }\n      #stage > .visual-host[data-track-index="4"] { z-index: 11; }', 1)
(out / "index.html").write_text(idx)
print(f"{len(hosts)} hosts -> {out}")
