# Editing Style (standing rules)

Claude reads this before every edit and applies it as the default. Change a rule here and it applies to every later video.

## Format
- **Long-form (the Rust in AI series):** **16:9 landscape**, 3 to 5 minutes, recorded horizontally. AI Producer cannot reframe a landscape source to vertical, so the recording orientation decides the output.
- **Shorts / Reels:** **9:16 vertical** short, 30 to 60 seconds, under 90 seconds, recorded vertically.
- Talking head fills the frame. Horizontal screen recordings are fitted into the vertical frame, normally full width with the speaker or a title above or below. They are not cropped to the center.

## Camera quality (soft footage)
- **Do not zoom in more than about 10%.** No punch-in zooms. They amplify softness and pixelation.
- Prefer reframing and cuts over zooming to add visual variety: switch between talking head, screen recording, B-roll and text instead.
- Hide softness with a clean layout, readable captions and good audio. Don't use effects that call attention to the image.
- If the source is below 1080p, flag it in `03-edit/edit-plan.md` and keep the layout conservative.

## Cutting
- Remove dead air, filler words ("um", "uh", "like") and retakes.
- Keep a pace of a visual change every 3 to 5 seconds (cut, screen clip, text, B-roll).
- First 2 seconds: the hook line, with no intro and no logo.

## Captions
- Always on. Dynamic style, chosen to match the content (energetic tech, so a bold word-by-word style).
- Keep captions inside the safe area (away from the bottom 15% where app buttons sit).
- Tech terms must be spelled correctly: Rust, Cargo, rustc, borrow checker, lifetimes, LLM, GPU, API. Claude checks the transcript for these.

## Audio
- Your mic is the master. Clean the voice only if it's noisy.
- Music: low, instrumental, modern, ducked under speech.
- Sound effects: light whoosh on transitions and a soft hit on key words. Never loud, and never on every cut.

## Visuals
- B-roll from search only where it adds meaning (logos, code screenshots, diagrams). No filler B-roll.
- Motion-graphic callouts for key terms and lower-thirds, used sparingly.
- No AI scene restyling unless you ask for it (it's the one paid tool).

## Color grading
- Before editing, preprocess all raw clips using `color-grading/preprocess.sh` or equivalent FFmpeg pipeline.
- **White balance:** lock it on the phone (5000-5600 K). Do **not** run `grayworld` by default: with a large colored object in frame (e.g. a teal curtain) it assumes the scene averages grey and turns skin pink/grey (measured on video 001). Use it only on a clip with a clear, uniform cast, and check the face afterwards.
- **Denoise** phone footage lightly with `hqdn3d=3:2:5:3.5` before editing (use `4:3:6:4.5` only for very noisy low-light clips).
- Apply the series LUT `series-soft` (from `color-grading/luts/`) at **50% intensity** to preserve natural skin tones (`--preset series-standard`).
- Preserve natural skin tones above all — never over-saturate. If a LUT makes skin look orange, magenta, or plastic, reduce intensity or switch LUTs.
- Keep **consistent color temperature** across all clips in a single video. If white balance looks different between takes, fix it per clip with a small `colorbalance` tweak judged by the face, not with `grayworld`.
- Recommended correction chain: `fps → scale(≤1080p) → hqdn3d → eq → lut3d (50%) → unsharp` (see `color-grading/presets/series-standard.txt`; the older `talking-head.txt` still includes `grayworld`).
- Log any color grading decisions in `03-edit/edit-plan.md` so changes are traceable.

## Video quality
- **Sharpen** soft phone footage gently with `unsharp=5:5:0.8:5:5:0.0`. Never over-sharpen (avoid halos).
- Never upscale beyond 2x — it amplifies artifacts.
- If source is below 1080p, flag it in `03-edit/edit-plan.md` and keep conservative framing.
- For severely soft or noisy footage, consider a two-pass approach: `nlmeans` for heavy denoise, then `unsharp` for recovery.
- Maintain CRF 18 or lower for exports to preserve grading quality. Never export above CRF 23.

## Cinematic look
- Target a warm, professional aesthetic: slightly warm highlights, neutral midtones, subtly lifted shadows.
- Use **teal-and-orange** sparingly and only when it suits the content. Default to clean, neutral warmth.
- Background should have slightly cooler tones than the subject's face (creates natural depth).
- Maintain a minimum contrast ratio between subject and background — don't let the speaker blend into the wall.
- Vignette only if it adds focus, never heavy, never noticeable.

## Delivery
- Claude shares the editable project link first. Export to mp4 only on your explicit request.
