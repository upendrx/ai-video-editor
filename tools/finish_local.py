#!/usr/bin/env python3
"""Finish an episode on this Mac with no AI Producer and no AI: graphics, captions, sound effects, music.
  python3 tools/finish_local.py videos/<ep>                    # after tools/post_record.py
  python3 tools/finish_local.py videos/<ep> --music ~/Music/bed.mp3 --music-db -24
  python3 tools/finish_local.py videos/<ep> --build build-dry  # preview with the dry-run timing (before recording)
Steps: 1) tools/fix_captions.py spells the captions as in the script, then node tools/render_graphics.mjs renders every kit graphic and the word captions to alpha video (cached),
2) sound effects from kit/sfx/ (made once with ffmpeg if missing) placed from sfx.json and each graphic's build beats,
3) music: --music, else the first file in kit/music/, ducked under the voice; none if neither exists,
4) everything composited over 03-edit/<build>/base.mp4 -> 03-edit/<build>/final-local.mp4 (H.264, 1080p, AAC).
"""
import json, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SFX_DIR, MUSIC_DIR = ROOT / "series/rust-in-ai/kit/sfx", ROOT / "series/rust-in-ai/kit/music"
BATCH = 12  # graphics per overlay pass

# Synthesised once with ffmpeg so the tool needs no downloads. Swap in nicer files with the same names any time.
SYNTH = {
    "whoosh": "anoisesrc=d=0.7:c=pink:a=0.6,highpass=f=300,lowpass=f=4000,afade=t=in:d=0.35,afade=t=out:st=0.35:d=0.35",
    "pop":    "sine=f=880:d=0.09,afade=t=out:d=0.09,volume=0.6",
    "ding":   "sine=f=1318:d=0.9,afade=t=out:st=0.05:d=0.85,volume=0.45",
    "riser":  "anoisesrc=d=1.4:c=white:a=0.35,highpass=f=800,afade=t=in:d=1.3,afade=t=out:st=1.3:d=0.1",
    "glitch": "anoisesrc=d=0.25:c=white:a=0.5,tremolo=f=28:d=1,afade=t=out:st=0.15:d=0.1",
}
GAIN_DB = {"whoosh": -14, "pop": -16, "ding": -15, "riser": -16, "glitch": -15}


def run(cmd):
    print("$", " ".join(str(c) for c in cmd[:6]), "…" if len(cmd) > 6 else "")
    subprocess.run([str(c) for c in cmd], check=True)


def dur(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                                capture_output=True, text=True).stdout.strip())


def ensure_sfx():
    SFX_DIR.mkdir(parents=True, exist_ok=True)
    for name, src in SYNTH.items():
        f = SFX_DIR / f"{name}.wav"
        if not f.exists():
            run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", src, "-ar", "48000", "-ac", "2", f])


def sfx_events(build, manifest):
    """(time, name) list. sfx.json gives the hints; pop-per-* hints pop on each build beat of that graphic."""
    hints = json.load(open(build / "sfx.json")) if (build / "sfx.json").exists() else []
    by_start = {round(g["start"], 2): g for g in manifest["graphics"]}
    ev = []
    for h in hints:
        t, kind = h["t"], h["hint"]
        if kind.startswith("pop"):
            g = by_start.get(round(t, 2))
            ev += [(t + b + 0.12, "pop") for b in (g["beats"] if g and g["beats"] else [0.2])]
        elif kind == "riser":
            ev.append((max(0, t - 1.3), "riser"))  # peaks on the moment
        elif kind in SYNTH:
            ev.append((t, kind))
    ev.sort()
    out, last = [], {}
    for t, k in ev:  # no machine-gun repeats of the same sound
        if t - last.get(k, -9) >= (0.12 if k == "pop" else 0.6):
            out.append((t, k)); last[k] = t
    return out


def main():
    a = sys.argv[1:]
    ep = (ROOT / a[0]).resolve() if not Path(a[0]).is_absolute() else Path(a[0])
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    build = ep / "03-edit" / opt("--build", "build")
    base = build / "base.mp4"
    if not base.exists():
        sys.exit(f"missing {base}: run python3 tools/post_record.py {a[0]} first")
    if "--no-render" not in a:
        if (ep / "01-script/script.md").exists() and (build / "words.json").exists():
            run([sys.executable, ROOT / "tools/fix_captions.py", ep, "--build", build.name])  # captions spelled as in the script
        run(["node", ROOT / "tools/render_graphics.mjs", build])
    rend = build / "render"
    manifest = json.load(open(rend / "manifest.json"))
    total = dur(base)
    tmp = build / "finish-tmp"; tmp.mkdir(exist_ok=True)

    # 1) Graphics, in batches of overlay passes (each pass is near-lossless).
    cur, gs = base, manifest["graphics"]
    for bi in range(0, len(gs), BATCH):
        part = gs[bi:bi + BATCH]
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", cur]
        fc, last = [], "0:v"
        for k, g in enumerate(part, 1):
            cmd += ["-i", rend / g["file"]]
            fc.append(f"[{k}:v]setpts=PTS-STARTPTS+{g['start']:.3f}/TB[g{k}]")
            fc.append(f"[{last}][g{k}]overlay=eof_action=pass:format=auto[v{k}]")
            last = f"v{k}"
        out = tmp / f"pass{bi // BATCH}.mp4"
        run(cmd + ["-filter_complex", ";".join(fc), "-map", f"[{last}]", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast",
                   "-crf", "12", "-pix_fmt", "yuv420p", "-c:a", "copy", out])
        cur = out

    # 2) Captions + audio mix in the final pass.
    ensure_sfx()
    ev = sfx_events(build, manifest)
    music = opt("--music")
    if not music and MUSIC_DIR.exists():
        music = next((str(p) for p in sorted(MUSIC_DIR.iterdir()) if p.suffix.lower() in (".mp3", ".wav", ".m4a", ".aac")), None)
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", cur]
    fc, n = [], 1
    vlast = "0:v"
    if manifest.get("captions") and "--no-captions" not in a:
        cmd += ["-i", rend / manifest["captions"]]
        fc.append(f"[0:v][{n}:v]overlay=eof_action=pass:format=auto[vc]"); vlast = "vc"; n += 1
    kinds = sorted({k for _, k in ev})
    idx = {}
    for k in kinds:
        cmd += ["-i", SFX_DIR / f"{k}.wav"]; idx[k] = n; n += 1
    mix = ["[voice]"]
    fc.append("[0:a]aresample=48000,asplit=2[voice][key]")
    for k in kinds:
        times = [t for t, kk in ev if kk == k]
        fc.append(f"[{idx[k]}:a]volume={GAIN_DB[k]}dB,asplit={len(times)}" + "".join(f"[{k}{i}]" for i in range(len(times))))
        for i, t in enumerate(times):
            ms = int(t * 1000)
            fc.append(f"[{k}{i}]adelay={ms}|{ms}[{k}d{i}]"); mix.append(f"[{k}d{i}]")
    if music:
        cmd += ["-stream_loop", "-1", "-i", music]
        db = float(opt("--music-db", -22))
        fc.append(f"[{n}:a]aresample=48000,volume={db}dB,afade=t=in:d=1.5,afade=t=out:st={max(0, total - 3):.2f}:d=3[mus]")
        fc.append("[mus][key]sidechaincompress=threshold=0.02:ratio=6:attack=30:release=500[duck]")
        mix.append("[duck]"); n += 1
    else:
        fc.append("[key]anullsink")
    fc.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,alimiter=limit=0.95[aout]")
    out = build / "final-local.mp4"  # review copy; it goes to 04-export/ only when you decide to publish it
    run(cmd + ["-filter_complex", ";".join(fc), "-map", f"[{vlast}]" if vlast != "0:v" else "0:v", "-map", "[aout]",
               "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nwrote {out} ({dur(out):.1f} s): {len(gs)} graphics, {len(ev)} sound effects, "
          f"captions {'on' if vlast == 'vc' else 'off'}, music {'on: ' + Path(music).name if music else 'off (add a file to series/rust-in-ai/kit/music/)'}")
    if manifest.get("failed"):
        print("graphics that failed to render (left out):", ", ".join(manifest["failed"]))


if __name__ == "__main__":
    main()
