# Long videos (3 to 5 minutes) with AI Producer

## Verdict
Yes, AI Producer helps a lot with long videos, and it is the right tool for the editing layer. It is not enough on its own.
The best setup is a **hybrid**: local tools for color and file prep, AI Producer for everything timeline-related, my kit for matching graphics.

| Job | Best tool | Why |
|---|---|---|
| Remove the green screen | Local: `tools/key_green.py` (FFmpeg chromakey + despill) | Free, deterministic, background matches the theme exactly; AI Producer's matte did not look good on a normal background |
| Replace the phone's voice with the Mac mic recording | Local: `tools/sync_audio.py` | Best voice quality with the best picture; automatic alignment |
| Color grade, denoise, sharpen, downscale to 1080p | Local: `color-grading/preprocess.sh --preset series-standard` | AI Producer only has basic filters (contrast, brightness, saturation). Local FFmpeg + LUT is better, and it shrinks 4K phone files below the upload limit |
| Transcript with word timing | AI Producer | Built in. No speech-to-text tool is installed locally |
| Cut dead air, filler, retakes | AI Producer (word-accurate cuts, reviewable and editable) | The local silence-detector cuts by volume only and cannot see a repeated sentence |
| Captions | AI Producer | Real caption styles, always in sync with the cut. The local Pillow captions are hard-wired to video 001 |
| Animated graphics | AI Producer, built from the kit | Editable in the editor, moves with the cut. The kit makes them uniform |
| Music (ducked), sound effects | AI Producer | Generated, mixed and ducked automatically |
| Export | AI Producer (mp4 from the editable project) | Same renderer as the preview |
| Thumbnail, title, description | Local (browser render) | Already built and used for Ep 0 |

## Limits that matter for long videos (from this project's own runs)
- **Aspect:** a landscape recording stays 16:9. That is what we want for long videos.
- **File:** .mp4, .mov or .webm. About 1.5 GiB per source file. A 5-minute 4K phone clip can exceed that, so grade and downscale first (the preset does it: about 135 MB for 5 minutes).
- **Length:** up to 15 minutes by default, so 3 to 5 minutes is comfortable. A cut over 5 minutes is exported in stretches; ours stay under, so a single pass.
- **Graphics:** one composition file per moment, max 64 KiB each. Kit graphics are 3 to 5 KiB, so no problem.
- **Batch sizes:** 60 sound effects per call, 24 music sections, 8 cutout windows per call.
- **Cost:** everything is free for now except scene restyling (which we do not use). There is a daily free allowance, so five long episodes in one day may hit it. I check the allowance before each episode and tell you if it runs low.
- **Time:** prepare + transcribe took about 1.5 minutes for a 53-second clip; expect a few minutes for a 4-minute one.
- **What I cannot do:** watch the finished preview or export. I verify structure and timing; you review the look and levels, and I fix what you flag. Face retouching and background cutouts did not work well and are not part of the series look.

## Workflow per episode (what I do once you drop footage)
0. **If the voice was recorded separately (phone picture + Mac mic):** `python3 tools/sync_audio.py ep1_take01.mov ep1_mic.m4a 03-edit/processed/ep1_synced.mp4`. It lines the mic up with the picture (checked to a few milliseconds, drift-corrected) and refuses if the two files do not contain the same speech.
0b. **Green screen:** `python3 tools/key_green.py <clip> --preview` first (check edges on one frame), then the full key into `03-edit/processed/`. The speaker lands on `kit/studio-bg.png`. Key before grading.
1. **Analyze** a sample clip (`python3 color-grading/analyze-color.py`), note issues in `03-edit/edit-plan.md`.
2. **Grade**: `preprocess.sh --preset series-standard` into `03-edit/processed/`. Original in `02-raw/` is never touched.
3. **Upload and transcribe** in AI Producer (graded 1080p file). Read the transcript, check spelling of project names against [vocabulary.txt](vocabulary.txt).
4. **Rough cut** (balanced): remove dead air, retakes, long pauses. Keep every complete sentence.
5. **Storyboard** the graphics from `01-script/beats.json` using the table below, with exact times from the transcript.
6. **Build** the graphics with the kit: `python3 series/rust-in-ai/kit/moments.py spec.json build/`, commit to the project.
7. **Captions** (`pace-adaptive`), **music** (one bed per episode), **sound effects** (whoosh on entries, pops on cards, ding on checks).
8. **Link to you** for review. You say what to change. Export only when you say "export".
9. Thumbnail, title and description into `04-export/`.

Rough effort: 25 to 40 tool calls per episode, about 20 to 40 minutes of my time. Episodes are independent, so we can do them one by one as you record.

## Style targets (from the reference channels, details in `.claude/skills/series-style/SKILL.md`)
- A new visual every 3 to 8 s: kit graphic, screen recording (crate docs, GitHub page, terminal) or b-roll; face only between ideas.
- Hook picture first, title card after about 4 s; word-by-word captions with one amber highlight word.
- Diagram or screen-share sections: speaker shrinks to a corner (AI Producer overlay layout, see the `aip-framing` skill) while the kit graphic builds. Not yet tested here; I verify it on the first episode.
- Stock b-roll through AI Producer's `find_broll` (free tier), plus your own screen recordings dropped into `02-raw/screen-recordings/`.
- Cuts: no pauses over 0.4 s; one cut every 4 to 6 s in the first minute.

## Storyboard: which graphic for which part
| Ep | Part | Graphics |
|---|---|---|
| 1 | Hook | `title_card`, then `flow`: import line, Python API, Rust underneath |
| 1 | Layer 1: tokenization, validation | `layers` (highlight 1), `chip_cards`: Tokenizers, Tiktoken, Polars, Pydantic-core, `lower_third` per project |
| 1 | Layer 2: safe weights | `compare`: pickle vs Safetensors |
| 1 | Layer 3: inference | `code_card`: `cargo run --release`, `chip_cards`: Candle, Burn, Mistral.rs, TGI |
| 1 | Layer 4 + outro | `layers` (highlight 4), `chip_cards`: Qdrant, LanceDB, `outro_next` |
| 2 | Hook | `title_card`, `code_card`: pip install |
| 2 | Tokenization, GIL | `compare`: one Python thread vs Rust on every core |
| 2 | PyO3 in practice | `flow`: Rust function, maturin, import in Python |
| 2 | See it yourself | `code_card`: `pip show -f tokenizers` |
| 2 | Validation and weights | `chip_cards`: Pydantic-core, Safetensors, `outro_next` |
| 3 | Hook | `title_card`, `stat_compare`: 10 GB vs 15 MB |
| 3 | Candle, Mistral.rs | `chip_cards`, `lower_third` |
| 3 | What Candle feels like | `code_card`: tensors, device, load, forward |
| 3 | Burn, TGI | `chip_cards` (TGI tagged "maintenance mode") |
| 3 | Trade-offs, takeaway | `compare` (Python vs Rust strengths), `checklist`, `outro_next` |
| 4 | Hook | `title_card`, `stat_compare` or `flow` |
| 4 | How vector search works | `flow`: chunk, embed, store, retrieve, prompt |
| 4 | Qdrant | `chip_cards`, `lower_third` |
| 4 | Filters, memory, reality check | `checklist` (3 items) |
| 4 | LanceDB + outro | `chip_cards`, `lower_third`, `outro_next` |
| 5 | Hook | `title_card`, `compare`: Rust vs Python becomes Rust + Python |
| 5 | Rule 1 | `checklist` item 1 |
| 5 | Three mistakes | `checklist` (3 items) |
| 5 | Quiz | `chip_cards`: four scenarios and their tool |
| 5 | Rules 2 and 3 | `checklist`, `chip_cards` |
| 5 | How to learn it | `flow`: Rust Book, PyO3 + maturin, Candle example; end card |

## Alternative: the local pipeline (`auto-edit.py`)
It is free and runs offline, and it produced the 43-second vertical and landscape exports for video 001.
It is hard-wired to that one script (graphics, timings and file paths), has no transcription, and cuts by volume only.
To use it on long videos it would need a speech-to-text step (for example whisper.cpp) and a graphics layer driven by a beat sheet.
That is a bigger build than using AI Producer plus the kit, so I recommend it only as a fallback or for quick vertical shorts.
