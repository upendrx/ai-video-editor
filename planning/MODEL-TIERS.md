# Which model for which task

Three tiers. Every "Next action" in `BOARD.md` is tagged **[A]**, **[B]** or **[C]**, so you can see at a glance what can be done today with the tools you have.

| Tier | Use | Why |
|---|---|---|
| **[A] Premium** (Claude Opus / Sonnet in Claude Code) | Writing, research, editing, graphics | Long context, many tool calls, judgement. The AI Producer plugin and the Playwright proof capture are set up only in Claude Code. |
| **[B] Free model** (Gemini in Antigravity, or any small model) | Small, exact edits with the file path given | A few files, little thinking, little output. Free tokens run out on long tasks. |
| **[C] No AI** (you run one command in the terminal) | Measuring, converting, rendering | Scripts already do it. Using AI here only burns tokens. |

Rule: when Claude premium is available, clear **all [A] rows on the board in one session** (see "Premium session" below). Do [B] and [C] on other days.

## How the repo works

```
 IDEA ─────────────► SCRIPT ─────────────► RECORD ─────────────► EDIT ─────────────────► PUBLISH
 planning/            videos/NNN/            videos/NNN/            videos/NNN/03-edit/      videos/NNN/04-export/
 topics/, research/   01-script/             02-raw/ (never edit)   + AI Producer project

 [A] YouTube research [A] script.md          [C] you: camera +      [C] post_record.py        [A] export when you
 [A] topic plan       [A] shot-list.md +          voice sessions        (one command, no AI):      say "export"
 [B] BOARD row            shots.json          [C] RECORD-STEPS.md        transcribe, pick takes, [B] title, description,
                      [A] proof screenshots                             sync, grade, assemble,     chapters, tags
                          (capture_proof.js)                            base cut, kit graphics, [A] thumbnail design
                      [A/B] terminal demos                              sound plan              [B] BOARD → stage 8
                          (vhs tapes)                                [A] AI Producer finish:
                      [C] teleprompters                                 upload, graphics,
                          (md_to_teleprompter)                          captions, music, sfx
                      [C] dry run of the edit                        [A] review changes
                          (post_record --dry-run)

 Shared by every video: series/rust-in-ai/ (theme, kit/moments.py graphics, teleprompter tool, vocabulary.txt)
                        tools/ (post_record → transcribe, pick_takes, sync_audio, assemble_audio; key_green), color-grading/preprocess.sh
```

## [A] Premium tasks (save these for when you have Claude)

| Task | What to say to Claude |
|---|---|
| Find trending topics / YouTube research | "Research YouTube for <topic> this month, add the result to `planning/topics/` and the board." |
| Write a script + shot list + proof + teleprompters | "Write the script for video NNN from its row in BOARD.md, like 008: script, shot list, proof screenshots, terminal demos, teleprompters, RECORD-STEPS." |
| Shot plan before recording (`03-edit/shots.json`) | "Write shots.json for video NNN from its shot-list.md and run the dry run." |
| AI Producer finish after `post_record.py` | "Video NNN: build is done. Do the AI Producer finish from `03-edit/build/` and give me the review link." (short session) |
| Review changes in AI Producer | "On video NNN change: <list>." Batch all notes into one message. |
| Export + thumbnail | "Export NNN and make the thumbnail." |
| Fact-check numbers on their source pages | "Check every number in NNN's script against its source, capture proof." |

One premium session can usually do: **2 AI Producer finishes + 1 script**, or **2 scripts with proof and shots.json**. Run `/compact` between videos.

## [B] Free-model tasks (Gemini in Antigravity)

Always give the exact file and say "read only this file". Copy-paste prompts:

- **Fix lines in a script:** "In `videos/NNN/01-script/script.md`, change line '<old>' to '<new>'. Keep the [CAM]/[READ] tags. Do not touch other lines." Then run the teleprompter command from [C].
- **Hinglish draft of a finished English script:** "Translate `videos/NNN/01-script/script.md` into Hinglish written in English letters. Keep the tech words in English, keep every [CAM]/[READ] tag and heading, keep the numbers. Write to `videos/NNN-hi/01-script/script.md`." (Claude checks it later in an [A] session.)
- **Title, description, tags, chapters:** "From `videos/NNN/01-script/script.md` write 3 titles under 60 characters, a YouTube description with chapters (use the Part headings and their target times), and 15 tags. Save to `videos/NNN/04-export/description.md`."
- **Spelling check:** "Check `videos/NNN/01-script/script.md` against `series/rust-in-ai/vocabulary.txt` and list wrong spellings only."
- **Update the board:** "In `planning/BOARD.md` set video NNN to stage X and next action '<text>'. Also update `videos/NNN/STATUS.md`."
- **Shorts ideas:** "From `videos/NNN/01-script/script.md` pick 3 parts of 30 to 50 seconds that work alone as Shorts. List the line ranges and a hook line for each."
- **Small terminal demo change:** "In `videos/NNN/03-edit/terminal/<name>.tape` change <thing>." Then run `vhs` yourself ([C]).

Do not give the free model: AI Producer edits, whole-episode scripts from scratch, research across many pages, or anything that reads `02-raw/` media.

## [C] No-AI commands (run them yourself)

Run from the repo folder (`cd ~/Movies/video-editing-agent`).

| Task | Command |
|---|---|
| Teleprompters after a script change | `python3 series/rust-in-ai/md_to_teleprompter.py videos/NNN/01-script/script.md "<name>" videos/NNN/01-script/teleprompter-cam.html --only cam` (and `--only read` → `teleprompter-voice.html`) |
| Phone clip vs mic offset | `python3 tools/sync_audio.py videos/NNN/02-raw/talking-head/cam-01.mp4 videos/NNN/02-raw/audio/cam-session.m4a --report` |
| Replace phone audio with mic | `python3 tools/sync_audio.py <video> <mic.m4a> <out.mp4>` |
| Key a green-screen clip | `python3 tools/key_green.py <clip> <out> --preview` (check edges, then without `--preview`) |
| Colour grade | `./color-grading/preprocess.sh --outdir videos/NNN/03-edit/processed <clip>` |
| Re-record a terminal demo | `cd videos/NNN/03-edit/terminal && vhs <name>.tape` |
| Contact sheet to check a video | `ffmpeg -i <video> -vf "fps=1/10,scale=320:-1,tile=6x5" -frames:v 1 sheet.png` |
| Recording | Follow `videos/NNN/RECORD-STEPS.md` only |
| **Whole first cut after recording** | `python3 tools/post_record.py videos/NNN` then read `videos/NNN/03-edit/build/report.md` |
| Fix one take | add `{"start of sentence": [t0, t1]}` to `03-edit/overrides.json`, rerun with `--from assemble` |
| Test a shot plan without recordings | `python3 tools/post_record.py videos/NNN --dry-run` |
| Transcribe any audio | `~/.venvs/rustai/bin/python tools/transcribe.py <audio> <out.json>` |

`post_record.py` runs transcription, take picking, sync, grading, audio assembly, the base video, kit graphics and the sound plan in one go.
What is left for Claude after it: the AI Producer finish (upload, commit graphics, captions, music, sound effects).

## Premium session checklist

1. Open `planning/BOARD.md`, collect every row tagged **[A]**.
2. Order: edits of recorded videos first (they block publishing), then scripts due before the next weekend, then research.
3. Give Claude one message per video. After each, Claude updates the board.
4. Anything left goes back on the board with its tag. Nothing lives only in chat.
