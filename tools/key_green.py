#!/usr/bin/env python3
"""Replace a green-screen background with a studio background (free: FFmpeg chromakey + despill).

  python3 tools/key_green.py IN.mp4 OUT.mp4 [--bg image.png] [--sim 0.14] [--blend 0.06] [--preview]

The key colour is sampled from the frame corners (so uneven or slightly yellow-green screens still key).
--preview writes OUT as a single PNG frame at 5 s so you can check edges before keying the whole take.
Order of work: sync audio -> key_green.py -> grade (preprocess.sh) -> your editor. Original footage is never modified.
Needs: ffmpeg, numpy, Pillow.
"""
import argparse, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
from PIL import Image

DEFAULT_BG = Path("studio-bg.png")  # generated on first run if missing


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True, check=True).stdout.split()
    w, h = map(int, out[0].split(",")[:2]); return w, h, float(out[1])


def sample_key(path, t):
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "f.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", path, "-frames:v", "1", str(f)], check=True)
        a = np.asarray(Image.open(f).convert("RGB"), dtype=float)
    h, w, _ = a.shape
    patches = [a[:h // 8, :w // 8], a[:h // 8, -w // 8:], a[h // 3:2 * h // 3, :w // 10], a[h // 3:2 * h // 3, -w // 10:]]
    px = np.concatenate([p.reshape(-1, 3) for p in patches])
    g = px[(px[:, 1] > px[:, 0] + 25) & (px[:, 1] > px[:, 2] + 25)]  # only green-dominant pixels
    if len(g) < 200:
        sys.exit("No green screen found at the frame edges. Is the screen lit and in frame on both sides?")
    return "0x%02x%02x%02x" % tuple(int(v) for v in np.median(g, axis=0)), len(g) / len(px)


def make_bg(w, h, path):
    y, x = np.mgrid[0:h, 0:w]
    r = np.hypot((x - w * .5) / w, (y - h * .45) / h) / .75
    t = np.clip(r, 0, 1)[..., None]
    c0, c1 = np.array([13, 42, 44.]), np.array([7, 25, 26.])  # THEME.md: #0d2a2c glow -> #07191a ground
    Image.fromarray((c0 * (1 - t) + c1 * t).astype("uint8")).save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--bg"); ap.add_argument("--sim", type=float, default=0.14); ap.add_argument("--blend", type=float, default=0.06)
    ap.add_argument("--preview", action="store_true"); ap.add_argument("--crf", default="16")
    a = ap.parse_args()
    w, h, dur = probe(a.inp)
    key, cover = sample_key(a.inp, min(5, dur / 2))
    print(f"key colour {key} (screen visible in {cover:.0%} of the sampled edge pixels)")
    bg = Path(a.bg) if a.bg else DEFAULT_BG
    if not bg.exists():
        make_bg(w, h, bg); print(f"made studio background {bg}")
    fc = (f"[0:v]chromakey=color={key}:similarity={a.sim}:blend={a.blend},despill=type=green:mix=0.6:expand=0.2[fg];"
          f"[1:v]scale={w}:{h},setsar=1[bg];[bg][fg]overlay=shortest=1,format=yuv420p[v]")
    cmd = ["ffmpeg", "-v", "error", "-y"]
    if a.preview:
        cmd += ["-ss", str(min(5, dur / 2)), "-i", a.inp, "-loop", "1", "-i", str(bg), "-filter_complex", fc, "-map", "[v]", "-frames:v", "1", a.out]
    else:
        cmd += ["-i", a.inp, "-loop", "1", "-i", str(bg), "-filter_complex", fc, "-map", "[v]", "-map", "0:a?",
                "-c:v", "libx264", "-preset", "slow", "-crf", a.crf, "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", a.out]
    subprocess.run(cmd, check=True); print("wrote", a.out)


if __name__ == "__main__":
    main()
