# Instructions for Claude

Video production workflow for Upendra's channel @UpendraBuilds (general tech, mostly AI). **No series:** every video is a standalone, trending, technical AI news topic; never call a video an episode or part of a series ("Rust in AI" was only a past topic; the `series/rust-in-ai/` folder just holds shared tools and the theme). Before writing a new video, check the topic is trending now, not fading. Rules: [STYLE.md](STYLE.md), theme: `series/rust-in-ai/THEME.md`, structure and editing: skill `video-style`, script voice (write, humanize, review): skill `script-writing`, workflow: `series/rust-in-ai/LONG-FORM-WITH-AIP.md`. Read a file only when the task needs it.
Master list of all videos, stages and the weekend recording plan: `planning/BOARD.md`; Antigravity prep notes for Claude: `planning/inbox/` (read today's files first; strategy in `BEST-USE-OF-AI.md`); task tiers (premium / free model / no AI): `planning/MODEL-TIERS.md` (topic plans in `planning/topics/`, facts in `planning/research/`). Update the board row whenever a video's stage changes.

## Pipeline (per episode, in this order)
1. `python3 tools/sync_audio.py <video> epN_mic.m4a <out.mp4>` only if a separate mic file exists.
2. Only if the footage is on a green screen: `python3 tools/key_green.py <clip> <png> --preview`, check edges, then key the full clip (speaker on `kit/studio-bg.png`).
3. `./color-grading/preprocess.sh --outdir videos/<ep>/03-edit/processed <clip>` (default preset `series-standard`; never grayworld).
4. Edit in AI Producer (`plugin:aip:ai-producer`, skill `aip`): transcript, balanced cut, kit graphics (`kit/moments.py`), `pace-adaptive` captions, one music bed, sfx. Check spelling against `vocabulary.txt`.
5. Give the review link. Export to `04-export/` only when the user says "export". Then thumbnail, title, description.
Log the plan, project link and decisions in `03-edit/edit-plan.md`; update `STATUS.md` at each stage.

## Recording mode (Upendra, from ep 007, Oct 2026)
Documentary style. Script lines are tagged [CAM] (on camera, about 30 %: hook, opinion, reaction, story, honesty beat, key takeaways, verdict, CTA) or [READ] (voice-over, fully covered by real proof and kit graphics). Two separate sessions, retakes welcome:
- **Camera session:** phone video (max 8 min per clip, clap at each clip start) + Mac mic running throughout. Only [CAM] lines, numbered C1, C2…: say the number once per new line, retakes without the number, long pauses. Teleprompter: `md_to_teleprompter.py SCRIPT "<name>" teleprompter-cam.html --only cam`.
- **Voice session:** Mac mic only, all [READ] lines. Teleprompter: `--only read` → `teleprompter-voice.html`.
- Set and look (Nov 2026 reference, George Alexander): `series/rust-in-ai/HOME-CINEMATIC-SETUP.md`; grade preset `home-cinematic` via `"cam_preset"` in shots.json once the new set is used.
- Files: `02-raw/talking-head/cam-NN.mp4`, `02-raw/audio/cam-session.m4a`, `02-raw/audio/voice-session.m4a`. Each episode gets a `RECORD-STEPS.md` (template: `videos/007-rust-ai-elon-was-right/RECORD-STEPS.md`).
- Edit: `python3 tools/post_record.py videos/<ep>` does transcribe, pick_takes, sync, grade, assemble, base video, kit graphics and sfx plan from `03-edit/shots.json` (write it before recording; check with `--dry-run`). Then `python3 tools/finish_local.py videos/<ep>` renders graphics, captions, sfx and music locally into `03-edit/build/final-local.mp4` (no AI, no tokens; `--build build-dry` previews before recording). AI Producer finish only if the user asks for it.
- Claude does all screen work: real proof screenshots via Playwright (template `videos/007-…/03-edit/capture_proof.js`, tweets via platform.twitter.com/embed), terminal demos via `vhs` tapes. Upendra never records screens. Plan every line in `03-edit/shot-list.md` before recording.

## Retake-heavy recordings (ep 1 workflow, Oct 2026)
Long mic file + short phone video: transcribe locally (faster-whisper in a venv), `tools/pick_takes.py` (best take per sentence), `tools/assemble_audio.py` (join, room tone, loudnorm), phone video only where it exists (offset by cross-correlation), crop 4K to the speaker. Graphics: `videos/<ep>/03-edit/build_ep1.py` (phrase cues -> kit), soft light theme. In AI Producer: commit graphics, remove false starts by exploding the speaker lane + `editing_script_sync`, then `build_captions` (words fixed in editing-script first).

## Rules
- Never touch `02-raw/`. Ask before `generate_scene_restyles` (paid). Everything else must be free tools.
- Style: no zoom above 10 %, one amber accent, a new visual every 3 to 8 s, hook first, no AI voice enhancement, no cutout or face retouching (judged bad on 001).
- Retired tools live in `_backup/`; do not use them.

## Save Claude tokens
- Do not re-read docs already summarised here; open only the section you need (use offset/limit or grep).
- Prefer scripts over manual steps: `build_episodes.py`, `moments.py`, `sync_audio.py`, `key_green.py`, `preprocess.sh`.
- Batch AI Producer calls (all captions, all sfx hits, all graphics in one commit); do not poll `wait_task` in tight loops.
- Never view full frames repeatedly: use one contact sheet (`ffmpeg ... tile=`) per check.
- Do not transcribe or analyse with the model what a script can measure (levels, cuts, offsets).
- Keep replies short: result, what needs the user's eye, next step. Use `/compact` between episodes.

## Learnings from reference channels (Oct 2026; full list in skill `video-style`)
- Hook = one concrete claim in the first 10 s, then a promise, then "let's get into it". 150-170 words per minute.
- Cut every 4-6 s early on; new visual every 3-8 s; word-by-word captions with one amber highlight.
- Speaker shrinks to a corner (picture in picture) when a diagram or screen recording builds.
- Green screen keyed onto the series studio background gives one uniform look across episodes.
- HyperFrames (HeyGen, Apache-2.0) uses the same HTML/GSAP model as AI Producer; use its catalog blocks inside the kit only after a trial shows a gain.
