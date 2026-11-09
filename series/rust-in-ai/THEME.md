# Rust in AI: series theme (the template)

Every episode uses this theme, so the grade, graphics, captions, music and sound effects all match. The tokens live in
[kit/moments.py](kit/moments.py) (`T = dict(...)`). Change a value there and every graphic follows.

## Look in one sentence
Clean dark teal "studio", warm amber accent, calm motion. The teal comes from your own curtain, the amber from the wood door
and Rust's brand orange, so the graphics already match the footage.

## Color tokens
| Role | Hex | Used for |
|---|---|---|
| Ground | `#07191a` (to `#0d2a2c` glow) | Full-cover backgrounds |
| Panel / line | `#0d2a2c` / `#1d4a4c` | Cards and their borders |
| Ink | `#e8f3f1` | Main text |
| Muted | `#9fc2bf` | Secondary text |
| Accent (Rust amber) | `#ffa726` | Kickers, tags, highlights, arrows |
| Bad / good | `#ff5d5d` / `#3ddc97` | Errors and "problem" vs "fix" |
| Python blue | `#6aa9ff` | Only where Python is being compared against Rust |

Rule: amber is the only accent. Red and green are for meaning (bad/good), never decoration.

## Typography
Geist (variable, already installed in the project by the caption build) for text; JetBrains Mono, falling back to system mono, for code.
Title 88 px, card name 46 px, role 27 px, kicker 26 px uppercase with letter-spacing. Nothing smaller than 24 px.

## Layout (16:9, 1920x1080)
- Graphics live between y 140 and y 690. Captions sit at y 722 to 962 (caption position 78), so they never collide.
- Side margins 120 px. Center the focal idea. One idea per graphic.
- Speaker footage is never cropped or zoomed more than 6%: it is shown whole.

## Motion
- Entrances 0.35 to 0.5 s, `back.out(1.6)` for cards and chips, `power3.out` for text. Exits 0.25 s fades.
- A new visual every 4 to 8 seconds in explainer sections; leave a few seconds of plain speaker between sections to breathe.
- No shake, flash or spin. One gentle push-in (max 6%) per episode is fine.

## Graphic types (the kit)
| Type | Use it for |
|---|---|
| `title_card` | Episode opener (kicker + title + project names) |
| `layers` | The 4-layer map in Ep 1; highlight one layer as it is explained |
| `chip_cards` | Project names with a role and an owner tag (Tokenizers, Candle, Qdrant...) |
| `compare` | Two columns: pickle vs Safetensors, Python vs Rust, before vs after |
| `code_card` | Typed code or terminal output, with an optional red flagged line |
| `flow` | Pipelines: Python API, PyO3, Rust core; chunk, embed, store, retrieve |
| `checklist` | Numbered rules (Ep 5), takeaways |
| `stat_compare` | Big number vs big number (10 GB container vs 15 MB binary) |
| `outro_next` | "Next episode" end card |
| `lower_third` | Small project label and GitHub path while you are on camera |

Preview any of them: `python3 series/rust-in-ai/kit/moments.py series/rust-in-ai/kit/examples/demo.json series/rust-in-ai/kit/examples/demo`
and open [kit/examples/contact-sheet.png](kit/examples/contact-sheet.png).

## Speaker background
The speaker is recorded on a green screen and keyed (`tools/key_green.py`) onto `kit/studio-bg.png`: a dark teal radial glow, `#0d2a2c` center to `#07191a` edge. Same background every episode.

## Footage grade
`./color-grading/preprocess.sh --preset series-standard <clip>`. Gentle: light denoise, tiny contrast and saturation lift, the
`series-soft` LUT at 50%, light sharpen, downscaled to at most 1080p at 30 fps. No auto white balance (see [TOOLS-AUDIT.md](TOOLS-AUDIT.md)).
Skin tone must stay warm and natural. If it ever looks grey, pink or orange, lower the LUT blend.

## Captions, music, sound effects (same for every episode)
- Captions: `pace-adaptive`, Geist, caption position 78, always on.
- Music: one low, instrumental, modern bed per episode, ducked under speech. Direction text: "low, instrumental, modern, subtle".
- Sound effects: snappy whoosh when a full-cover graphic enters, bright pop per card or chip, warm ding for a correct/check moment,
  glitch only for a real error. Never on every cut.
- Voice: your original recording. No AI voice enhancement.

## Thumbnails and titles
Real video frame (eyes open, natural expression), dark gradient on the left for text, three lines max: topic in white,
hook in amber, a small mono tag in red. No cutouts. Titles under 60 characters; the clearest title first, the clickiest second.

## Episode skeleton
1. Cold-open hook (first 2 to 3 seconds are the claim, no logo)
2. `title_card` after the hook (about 4 s)
3. Sections with a graphic each, `lower_third` whenever a project is named on camera
4. Honest-trade-offs beat (builds trust with developers)
5. `outro_next` end card with the next episode
