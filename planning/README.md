# How the folders work

```
planning/
  BOARD.md                 ← start here: every video, its stage, and the weekend plan
  MODEL-TIERS.md           ← which tasks need Claude premium [A], a free model [B], or no AI [C]
  topics/                  ← topic research and script plans (one file per research round, dated)
  research/                ← source material and fact sheets (your docs, numbers with sources)
videos/
  NNN-slug/                ← one folder per video, number never changes once given
                             Hindi/Hinglish videos: NNN-hi-slug
    STATUS.md              ← stage checklist, titles, thumbnail
    RECORD-STEPS.md        ← what you do on recording day
    01-script/             ← script.md ([CAM]/[READ] lines), teleprompter-cam.html, teleprompter-voice.html
    02-raw/                ← your recordings (never edited)
    03-edit/               ← shot-list.md, shots.json, edit-plan.md, proof/, terminal/, build/ (made by post_record.py)
    04-export/             ← final video, thumbnail
  _backlog/NNN-slug/       ← scripts kept for later (weaker YouTube demand or already covered); same layout
series/rust-in-ai/         ← theme, kit, teleprompter tool, vocabulary (shared by all videos)
```

Rules
- An idea stays a row in `BOARD.md` until it is scheduled; only then it gets a number and a folder.
- Recording day: open the video's `RECORD-STEPS.md`, nothing else.
- When a stage changes, the row in `BOARD.md` and the video's `STATUS.md` change together.
- Every script uses one format: each spoken line starts with `> [CAM]` (on camera) or `> [READ]` (voice-over). `⟨ ⟩` = a demo number still to fill; never record a script that has one.
- A video goes to `_backlog/` when YouTube demand is weak or another video already covers it. Its number is kept.
