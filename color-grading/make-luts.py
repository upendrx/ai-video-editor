#!/usr/bin/env python3
"""Generate the default .cube LUTs (33-point). Pure numpy, no downloads.

soft.cube     gentle S-curve, lifted blacks, cool shadows / warm highlights (default)
clean-neutral.cube   tone curve only, no tint (use when a clip has a color cast you do not want to push)
"""
import numpy as np
from pathlib import Path

N = 33
OUT = Path(__file__).parent / "luts"

def smooth(v): return v * v * (3 - 2 * v)

def make(name, title, contrast, lift, sh_tint, hi_tint):
    g = np.linspace(0, 1, N)
    B, G, R = np.meshgrid(g, g, g, indexing="ij")          # r varies fastest when flattened
    rgb = np.stack([R, G, B], -1)
    tone = rgb + contrast * (smooth(rgb) - rgb)             # mild S-curve
    tone = lift + tone * (1 - lift)                         # lifted blacks
    luma = (0.2126 * tone[..., 0] + 0.7152 * tone[..., 1] + 0.0722 * tone[..., 2])[..., None]
    ws, wh = (1 - luma) ** 2, luma ** 2
    tone = tone + ws * np.array(sh_tint) + wh * np.array(hi_tint)
    tone = np.clip(tone, 0, 1)
    lines = [f'TITLE "{title}"', f"LUT_3D_SIZE {N}", "DOMAIN_MIN 0.0 0.0 0.0", "DOMAIN_MAX 1.0 1.0 1.0"]
    for b in range(N):
        for gi in range(N):
            for r in range(N):
                lines.append("%.6f %.6f %.6f" % tuple(tone[b, gi, r]))
    (OUT / name).write_text("\n".join(lines) + "\n")
    print("wrote", name)

make("soft.cube", "Soft", 0.30, 0.012, (-0.006, 0.0, 0.012), (0.010, 0.003, -0.008))
make("clean-neutral.cube", "Clean Neutral", 0.22, 0.008, (0, 0, 0), (0, 0, 0))
