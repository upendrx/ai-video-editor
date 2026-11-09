---
name: video-style
description: Edit and structure rules for @UpendraBuilds videos (standalone trend/news videos, no series): hook timing, pace, cuts, captions, graphics, sound, checklist. Use when planning an edit or storyboard, building shots, or judging whether an edit feels finished. For script voice use skill `script-writing`.
---

# Video style (standalone videos, no series)

Every video stands alone. Never call a video an episode or part of a series, and never tease "the next episode". The end points to one related video on the channel.
Reference analysis: Bilawal Sidhu and Greg Isenberg (Oct 2026), plus 007 analytics (half the viewers gone by 0:30 when the first proof came at 0:46).

## Script structure (voice and wording: skill `script-writing`)
- **Hook (first 10 s):** real, moving proof on screen in the first 5 s, one concrete claim a non-developer understands. No greeting, no channel intro.
- **Promise:** what the viewer will see, then a short "Let's get into it".
- **Body:** one idea per section, 30 to 60 s each: point, proof (a number, a real project, a real command), takeaway.
- **Pace:** 150 to 170 words per minute (5 min ≈ 800 words, 7 min ≈ 1,100).
- **Honest trade-off beat** in every video. Facts must be checkable; no invented numbers.
- **Mid-video (~45 %):** "If you're new here, I'm Upendra. On this channel I dig into what's really happening in AI, with the receipts."
- **End:** one-sentence takeaway, one question, point to one related video. Under 15 s.
- Tag lines [CAM] or [READ] (see `CLAUDE.md`, recording mode) and plan each line's visual in `03-edit/shot-list.md`.

## Editing
- **A new visual every 3 to 8 s** (graphic, screen recording, b-roll, or a punch-in). Never more than 8 s of unchanged picture.
- **Cuts:** remove pauses over 0.4 s and filler; keep natural breaths. One cut every 4 to 6 s in the first minute.
- **Open on the hook picture, not a logo.** Title card only after the hook (about 4 s).
- **One accent colour** on every graphic, caption highlight and chip. Red/green only for bad/good.
- **Captions:** word by word, bottom third, one highlighted word per phrase (`pace-adaptive`, position 78).
- **Diagram / screen sections:** speaker shrinks to a corner while the diagram builds step by step.
- **Name plates:** `lower_third` whenever a project or person is named on camera.
- **Numbers:** animate counters or `stat_compare` for any figure said aloud.
- **Sound:** one low music bed, ducked; whoosh on full-cover entries, pop on cards, ding on checks. Never a sound on every cut.
- **Look:** same grade every video, warm natural skin. No zoom above 10 %, no face retouching.

## Cinematic home talking head (reference: George Alexander, Nov 2026)
Analysis: `planning/research/2026-11-05-reference-george-alexander.md`; set and phone: `series/rust-in-ai/HOME-CINEMATIC-SETUP.md`.
- **Face time builds connection:** about 30 % [CAM]. Opinion, reaction, story and "what this means for you" lines go on camera; facts and proof stay [READ] over real proof.
- **Look:** room darker than the face, soft side light, warm lamp behind, muted colours with warm skin. Grade with preset `home-cinematic` (`"cam_preset": "home-cinematic"` in shots.json) once that set is in use.
- **Parts:** 3 named parts with a short title card on a solid muted colour from the theme (about 1.5 s, one word or two), so the viewer feels progress.
- **Memorable line on screen:** each part's key line appears as kinetic text (one word in amber) on a full-cover card; once per part (no text behind the speaker: needs a cutout, which we do not use), not more.
- **Viewer's problem as the first picture** when the topic allows: their search box, their feed, the headline they saw.
- **Then and now / two sides:** split screen or before/after counters for contrasts (e.g. "Subs: 7" vs "Subs: 56,842" style chips).
- **Proof stays real:** screenshots of the actual page, dashboard or filing (we already do this; keep it).
- **End screen:** solid theme colour, the next-video card, a handwritten-style "watch this next" arrow.
- **Not possible yet without filming b-roll:** his acted b-roll (walking, hands writing, top-down props). Optional: 3 to 5 short phone clips per video of hands on a laptop, a desk top-down, a window; Claude places them.

## Checklist before handing a draft to the user
1. First 5 s show real proof; first sentence is a claim, not a greeting.
2. Longest stretch without a new visual is under 8 s.
3. Names spelled per `series/rust-in-ai/vocabulary.txt` (shared word list, despite the folder name).
4. Graphics do not collide with captions (graphics y 140 to 690, captions y 722 to 962).
5. Trade-off beat present; no series or episode wording anywhere.
