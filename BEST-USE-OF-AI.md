# Best use of AI: Antigravity + Claude

My limits:
- **Antigravity IDE (premium):** a fresh set of model tokens every ~3 hours. Unused tokens are lost when the window resets, so use every window.
- **Claude (Claude Code):** the main brain. Its tokens are the expensive ones, so save them for work only Claude can do.

The idea: **Antigravity does the small, exact, repeatable jobs and prepares notes. Claude reads those notes and does the big jobs.** Antigravity writes everything into `planning/inbox/`, so Claude starts each session with the work already half done instead of reading the whole repo.

Detailed task tiers: `planning/MODEL-TIERS.md`. Master list of videos: `planning/BOARD.md`.

---

## Who does what

| Antigravity (use every window) | Claude (save tokens) |
|---|---|
| Spelling check against `vocabulary.txt` | Writing a full script from scratch |
| Fix given lines in a script | Research across many web pages, fact-checking with proof screenshots |
| Titles, descriptions, tags, chapters | AI Producer edits (only Claude has the plugin) |
| Shorts ideas from a finished script | Playwright proof capture, terminal demos (`vhs`) |
| Hinglish draft of a finished English script | Writing `shots.json`, shot lists, thumbnails |
| Updating `BOARD.md` and `STATUS.md` rows | Judging quality (review notes, "does this edit feel finished") |
| Summaries and checklists for Claude (inbox) | Export when I say "export" |
| Reading long files and writing a short summary | Anything that needs many tool calls or many files |

Never give Antigravity: AI Producer work, anything inside `02-raw/`, whole scripts from nothing, paid tools.
Never give either AI: things a script already does (sync, grading, levels, contact sheets). Run those commands yourself (`planning/MODEL-TIERS.md`, section [C]).

---

## Daily plan (3 Antigravity windows + 1 Claude session)

| Time | Tool | Job |
|---|---|---|
| Morning (window 1) | Antigravity | Daily check + inbox note for Claude |
| Midday (window 2) | Antigravity | Content work on scripts ready for it (titles, Shorts, Hinglish, spelling) |
| Evening (window 3) | Antigravity | Prep pack for tomorrow's Claude task + board cleanup |
| When Claude is available | Claude | Clear the **[A]** rows on the board, starting from the inbox note |

If a window has nothing useful to do, run the "weekly" prompts below instead. Do not let a window expire unused.

---

## Copy-paste prompts for Antigravity

Rule for every prompt: name the exact files, say "read only these files", and say where to write the result. Small and exact = cheap and correct.

### Window 1 — Morning check (daily)

```
Read only planning/BOARD.md and the STATUS.md of each video folder listed in it.
Write planning/inbox/YYYY-MM-DD-today.md with:
1. Every row tagged [A] (Claude work), oldest deadline first, one line each.
2. Every row tagged [B] that you can do now, one line each.
3. Every row tagged [C] that I must do myself (record, run a command).
4. Any row where BOARD.md and STATUS.md disagree.
Keep it under 40 lines. Do not change any other file.
```

### Window 2 — Content work (daily, pick what fits)

Spelling:
```
Check videos/NNN/01-script/script.md against series/rust-in-ai/vocabulary.txt.
Read only these two files. List wrong spellings with line numbers. Do not edit anything.
```

Titles, description, chapters, tags:
```
Read only videos/NNN/01-script/script.md.
Write 3 titles under 60 characters, a YouTube description with chapters (use the Part
headings and their target times) and 15 tags. Save to videos/NNN/04-export/description.md.
```

Shorts:
```
Read only videos/NNN/01-script/script.md. Pick 3 parts of 30 to 50 seconds that work
alone as YouTube Shorts. For each: line range, a hook line, and why it works alone.
Save to videos/NNN/03-edit/shorts-ideas.md.
```

Hinglish draft:
```
Translate videos/NNN/01-script/script.md into Hinglish written in English letters.
Keep tech words in English, keep every [CAM]/[READ] tag, heading and number.
Write to videos/NNN-hi/01-script/script.md. Read only the source file.
```

Fix lines:
```
In videos/NNN/01-script/script.md change the line "<old>" to "<new>".
Keep the [CAM]/[READ] tags. Do not touch other lines.
```
(Then run the teleprompter command yourself.)

### Window 3 — Prep pack for Claude (daily, evening)

This is the biggest token saver: Claude reads one short file instead of five long ones.

```
Tomorrow Claude will do: <task from the [A] list, e.g. "write the script for video 009">.
Read only planning/BOARD.md, the matching file in planning/topics/ and planning/research/,
and videos/NNN/STATUS.md.
Write planning/inbox/YYYY-MM-DD-prep-NNN.md with:
- Goal in one line, deadline from the board.
- Facts and numbers already collected, each with its source link.
- Open questions Claude must answer.
- Files Claude needs to open (paths only).
Under 60 lines. Do not invent facts or numbers. Mark anything unsure with "CHECK".
```

Board cleanup (after any change during the day):
```
In planning/BOARD.md set video NNN to stage X and next action "<text>".
Also update videos/NNN/STATUS.md. Change nothing else.
```

### Weekly prompts (when a window has nothing else)

Topic ideas (Claude checks them later):
```
Read only planning/BOARD.md and the files in planning/topics/.
Suggest 5 new video ideas for a Rust + AI channel that are not on the board.
For each: working title, one-line hook, kind (Trend / Explainer / Views), EN or HI.
Save to planning/inbox/YYYY-MM-DD-ideas.md.
```

Script review notes:
```
Read only videos/NNN/01-script/script.md and STYLE.md.
List lines that break STYLE.md (long sentences, missing hook in first 10 s, no visual
change for long stretches). Line number + short reason. Do not edit the script.
Save to planning/inbox/YYYY-MM-DD-review-NNN.md.
```

Published video prep:
```
For every video at stage 7 in planning/BOARD.md that has no videos/NNN/04-export/description.md,
write one (same format as the titles/description prompt). Read only each video's script.md.
```

---

## How to start a Claude session (saves the most tokens)

1. Open Claude in this repo.
2. First message: **"Read `planning/inbox/` (today's files only) and do the [A] tasks in order."**
3. One video per message. Batch all review notes for a video into one message.
4. Claude moves done inbox files to `planning/inbox/done/` and updates the board.
5. `/compact` between videos.

Claude should also check Antigravity's work quickly (facts, Hinglish drafts, titles) before anything is published. A quick check is cheap; writing it from zero is not.

---

## Simple rules

- Antigravity window open → give it a job. Claude available → give it only [A] work.
- Everything goes into a file (`planning/inbox/`, the board, or the video folder). Nothing lives only in chat.
- Never let any AI edit `02-raw/`.
- Paid AI Producer tools (`generate_scene_restyles`) only after I say yes.
