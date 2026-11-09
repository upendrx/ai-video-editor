# Tools audit: what was added today and what is best for us

## Final toolset (everything free)
| Job | Tool |
|---|---|
| Voice sync (phone picture + Mac mic) | `tools/sync_audio.py` |
| Green screen removal | `tools/key_green.py` |
| Grade, denoise, downscale | `color-grading/preprocess.sh` (default preset `series-standard`, LUT `series-soft`) |
| Cut, captions, music, sfx, export | AI Producer (`plugin:aip:ai-producer`) |
| Graphics | `series/rust-in-ai/kit/moments.py` (+ HyperFrames catalog blocks if the trial shows a gain) |
| Scripts, teleprompters | `series/rust-in-ai/build_episodes.py` |
| Style rules | `.claude/skills/series-style/SKILL.md`, `THEME.md` |
Retired to `_backup/`: `auto-edit.py` and `PIPELINE.md` (one-video script, no transcription), the `talking-head` preset and `cinematic-warm`
and `moody-teal-orange` LUTs (auto white balance and strong looks hurt skin), the local-pipeline overlay PNGs of video 001.

---
Original audit below (2026-10-22).

Checked on 2026-10-22 against your real footage (`videos/001-rust-ownership`, 1512x982, teal curtain, wood door).

## What is in the folder now
| Item | What it is | State |
|---|---|---|
| `color-grading/preprocess.sh` | FFmpeg pipeline: white balance, denoise, eq, LUT, sharpen | Works; supports `--preset`, `--lut`, `--dry-run` |
| `color-grading/analyze-color.py` | OpenCV color report with suggested fixes | Works (OpenCV 5, NumPy installed) |
| `color-grading/luts/cinematic-warm.cube` | One custom 17-point LUT | Works; the only LUT that existed |
| `color-grading/presets/talking-head.txt` | The default filter chain | Works, but see finding 1 |
| `auto-edit.py` + `PIPELINE.md` | Local end-to-end editor (FFmpeg, Pillow, OpenCV) | Works for video 001 only, see finding 3 |
| `STYLE.md`, `README.md`, `CLAUDE.md` | Rules and checklists | Good; one rule corrected (below) |
| Installed tools | ffmpeg (lut3d, hqdn3d, nlmeans, unsharp, loudnorm, minterpolate), yt-dlp, node, OpenCV, NumPy, Pillow | Not installed: whisper / speech-to-text, auto-editor, ImageMagick, upscalers, rembg, mediapipe |

## Findings
**1. The auto white balance step (`grayworld`) hurts this scene.** It assumes the average color of the frame is grey.
With a big teal curtain and a wood door that assumption is false, so it pulled your skin toward pink-grey.
Measured on the same frame (face region, RGB):

| Version | Face RGB | Red minus green | Saturation | Frame brightness |
|---|---|---|---|---|
| Raw | 167, 127, 105 | 41 | 40% | 105 |
| Current pipeline (`cine`) | 142, 121, 124 | 21 | 28% | 95 |
| New `series-standard` | 169, 128, 100 | 41 | 44% | 103 |

Healthy skin keeps red clearly above green above blue. The current pipeline loses that (blue exceeds green) and darkens the frame.
The new preset keeps your natural tone and adds a little richness. You can see the side-by-side by running the preset on a clip.
`analyze-color.py` has the same blind spot: it reported a "red/warm cast" that is really just your warm skin and wood door.
Trust its skin-tone hue (18 degrees here, which is healthy) over its cast warning. **Fix: lock white balance on the phone instead (5000 to 5600 K).**

**2. LUT library was incomplete.** `color-grading/README.md` lists `clean-neutral.cube` and `moody-teal-orange.cube`, but only `cinematic-warm.cube` existed.
I generated three 33-point LUTs with `color-grading/make-luts.py` (no downloads needed): `series-soft` (default), `clean-neutral`, `moody-teal-orange`.

**3. `auto-edit.py` is a one-video script.** Graphics, timings and the input path are hard-coded to video 001.
It has no transcription (no whisper installed), cuts by volume only, and its captions are pre-rendered pictures, not text tied to the cut.
It is a good proof of concept and a fine fallback for quick vertical shorts, but it cannot edit a new 4-minute episode by itself.

**4. Large phone files.** The default chain does not downscale. A 5-minute 4K phone clip would stay 4K at CRF 18, which can exceed AI Producer's upload limit.
The new preset converts to 30 fps and at most 1080p, without ever upscaling. Test result: 53-second clip, 24 MB.

## Recommendation (what to use for what)
| Need | Use |
|---|---|
| Grade every episode | `./color-grading/preprocess.sh --preset series-standard <clip>` (run from the repo root) |
| Check light before recording | `python3 color-grading/analyze-color.py test_clip.mov`, but read exposure and skin hue, not the "cast" line |
| Edit, captions, music, effects, export | AI Producer, see [LONG-FORM-WITH-AIP.md](LONG-FORM-WITH-AIP.md) |
| Matching graphics | The kit: [kit/moments.py](kit/moments.py), theme in [THEME.md](THEME.md) |
| Quick vertical shorts later | `auto-edit.py`, after generalizing it |

## LUTs: what is best for us
- **Default for every episode: `series-soft` at 50%.** Mild S-curve, lifted blacks, cooler shadows and warmer highlights. Keeps skin safe.
- **`clean-neutral`:** tone only, for a clip with a color problem you do not want to push further.
- **`moody-teal-orange`:** stronger look, only for an intro or a special episode; check skin first.
- **Downloaded LUTs** (Luttie, FilterGrade, Editor Hub, as the README suggests): drop `.cube` files into `color-grading/luts/` and test them with
  `--lut` at 40 to 60%. Pick by skin tone, not by how dramatic the preview looks. Avoid "film" LUTs that crush blacks or push orange.
- Better than any LUT: good light, locked white balance, a bit of distance from the wall. The checklist in the README covers this.

## Changes I made
- Added `color-grading/presets/series-standard.txt`, `color-grading/make-luts.py` and three LUTs.
- Added `series/rust-in-ai/` (theme, kit, episode builder, teleprompter template, guides).
- Corrected the white-balance rule in `STYLE.md` and pointed `CLAUDE.md` and `README.md` at the new preset. The old preset and `cinematic-warm.cube` are unchanged.
