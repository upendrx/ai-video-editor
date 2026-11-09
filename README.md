# ai-video-editor

A small, free toolkit and Claude Code workflow for recording and editing technical talking-head videos. Everything runs locally on top of FFmpeg and a few Python libraries — no paid services, no uploads.

## What's inside

| Path | Purpose |
|------|---------|
| `color-grading/preprocess.sh` | Batch grade clips: denoise, gentle colour correction, optional LUT, sharpen, constant frame rate, downscale to ≤1080p |
| `color-grading/analyze-color.py` | Measure a clip's colour balance (OpenCV) |
| `color-grading/make-luts.py` | Generate `.cube` LUTs with NumPy, no downloads |
| `tools/sync_audio.py` | Replace a video's audio with a separately recorded mic track, aligned by FFT cross-correlation with drift correction |
| `tools/key_green.py` | Replace a green-screen background using FFmpeg chromakey + despill, with a single-frame preview mode |
| `tools/pick_takes.py` | Choose the best take of each scripted sentence from a word-level transcript (fuzzy matching, penalises flubs) |
| `tools/assemble_audio.py` | Cut the chosen takes from a long recording and join them with room tone and fades |
| `tools/transcribe.py` | Word-level local transcript with faster-whisper |
| `tools/refine_takes.py`, `tools/check_cut.py` | Tighten take boundaries and check the cut against the script |
| `tools/post_record.py` | One command after recording: transcribe, pick takes, sync, grade, assemble, plan graphics and sfx from `shots.json` |
| `tools/finish_local.py`, `tools/render_graphics.mjs` | Render graphics, captions, sfx and music locally into a finished video (no AI, no paid tools) |
| `tools/fix_captions.py`, `tools/aip_root.py` | Caption clean-up and AI Producer composition helpers |
| `series/rust-in-ai/kit/` | Motion graphics kit (`moments.py`: title, layers, cards, compare, code, flow, checklist, stats, lower third), sound effects, studio background |
| `series/rust-in-ai/md_to_teleprompter.py` | Turn a `[CAM]` / `[READ]` script into a browser teleprompter |
| `studio/` | Small local web app (Vite + Fastify) to run jobs and track videos |
| `.claude/skills/` | Claude Code skills: `video-style` (pacing, cuts, captions, graphics) and `script-writing` (human-sounding technical scripts) |
| `STYLE.md`, `CLAUDE.md`, `series/rust-in-ai/*.md` | Editing rules, the full record-to-export workflow, theme, recording and speaking guides |
| `planning/PLAYBOOK-TREND-VIDEO.md`, `planning/MODEL-TIERS.md` | How to pick a trending topic, and which tasks need a premium model, a free model or no AI |

## Requirements

- FFmpeg / ffprobe on your `PATH`
- Python 3.9+

```bash
pip install -r requirements.txt
```

## Quick start

```bash
# 1. Align a separately recorded mic with the camera footage
python3 tools/sync_audio.py camera.mov mic.m4a synced.mp4

# 2. (Green screen only) check the key on one frame, then key the whole clip
python3 tools/key_green.py synced.mp4 preview.png --preview --bg background.png
python3 tools/key_green.py synced.mp4 keyed.mp4 --bg background.png

# 3. Grade
./color-grading/preprocess.sh --outdir processed keyed.mp4
```

Run any script with `-h` (or read its header) for the full option list. See [color-grading/README.md](color-grading/README.md) for presets and LUT details.

### Retake-heavy recordings

If you record a script with many retakes in one long audio file:

```bash
# transcript: word-level JSON [{s,e,t,w:[[start,end,word],...]}] (e.g. from faster-whisper)
python3 tools/pick_takes.py SCRIPT.md transcript.json picks.json
python3 tools/assemble_audio.py mic48.wav picks.json out
```

`SCRIPT.md` holds one sentence per line as `> [CAM] text` or `> [READ] text` under `## ` section headings.

## Notes

- Original footage is never modified; every tool writes a new file.
- Source media is not tracked in this repository (see `.gitignore`).

## License

[MIT](LICENSE)
