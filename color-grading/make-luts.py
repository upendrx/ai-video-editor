#!/usr/bin/env python3
"""Generate the series .cube LUTs (33-point). Pure numpy, no downloads.

series-soft.cube     gentle S-curve, lifted blacks, cool shadows / warm highlights (default for the series)
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

def make_home_film(name="home-film.cube"):
    """Low-key 'cinematic home studio' look (reference: George Alexander, Nov 2026).
    Measured on his talking-head frames: frame luma ~76/255, overall saturation low (~10),
    background cool (U>128, V<128), skin warm and kept saturated (V ~150, sat ~25-30).
    So: S-curve, small black lift, everything except skin hues muted ~25 %, cool shadows, warm highlights."""
    g = np.linspace(0, 1, N)
    B, G, R = np.meshgrid(g, g, g, indexing="ij")
    rgb = np.stack([R, G, B], -1)
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = np.where(mx - mn == 0, 1e-6, mx - mn)
    r, gg, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    hue = np.where(mx == r, ((gg - b) / d) % 6, np.where(mx == gg, (b - r) / d + 2, (r - b) / d + 4)) * 60
    hue = np.where(mx - mn == 0, 0, hue)
    dist = np.minimum(np.abs(hue - 25), 360 - np.abs(hue - 25))   # distance from skin hue (orange, ~25 deg)
    skin = np.exp(-(dist / 22) ** 2)
    sat = 0.74 + 0.30 * skin                                        # others x0.74, skin x1.04
    luma = (0.2126 * r + 0.7152 * gg + 0.0722 * b)[..., None]
    rgb = luma + sat[..., None] * (rgb - luma)
    tone = rgb + 0.24 * (smooth(np.clip(rgb, 0, 1)) - rgb)        # S-curve
    tone = 0.02 + tone * (1 - 0.02) - 0.035 * tone ** 4             # tiny lift, soft highlight roll-off
    luma = (0.2126 * tone[..., 0] + 0.7152 * tone[..., 1] + 0.0722 * tone[..., 2])[..., None]
    ws, wh = (1 - luma) ** 2, luma ** 2
    tone = tone + ws * np.array((-0.010, 0.002, 0.016)) + wh * np.array((0.012, 0.004, -0.010))
    tone = np.clip(tone, 0, 1)
    lines = ['TITLE "Home Film"', f"LUT_3D_SIZE {N}", "DOMAIN_MIN 0.0 0.0 0.0", "DOMAIN_MAX 1.0 1.0 1.0"]
    for bi in range(N):
        for gi in range(N):
            for ri in range(N):
                lines.append("%.6f %.6f %.6f" % tuple(tone[bi, gi, ri]))
    (OUT / name).write_text("\n".join(lines) + "\n")
    print("wrote", name)

make("series-soft.cube", "Series Soft", 0.30, 0.012, (-0.006, 0.0, 0.012), (0.010, 0.003, -0.008))
make("clean-neutral.cube", "Clean Neutral", 0.22, 0.008, (0, 0, 0), (0, 0, 0))
make_home_film()
