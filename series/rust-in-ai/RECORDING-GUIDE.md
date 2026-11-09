# Recording guide: tonight

Goal: five episodes, each 3 to 4 minutes, read from the teleprompter.

## Pick your setup (you have a MacBook Pro 14" M1 Pro and a phone whose camera cannot take your mic)

| | Picture | Voice | Sync needed | Best when |
|---|---|---|---|---|
| **A. MacBook camera + mic, all on the Mac** | FaceTime HD camera, 1080p | Your mic (or the Mac's built-in mic) | No, one file | You want the simplest setup, or the light is good |
| **B. Phone video + mic recorded on the Mac** (recommended) | Phone camera (much sharper and cleaner than a laptop webcam) | Your mic, recorded as a separate audio file | Yes, automatic: `tools/sync_audio.py` (tested to within a few milliseconds) | You want the best picture |
| C. Phone alone | Phone camera | Phone mic | No | Avoid: weakest voice |

If you are unsure, use **B**. It takes two extra minutes to set up and gives the best picture and the best voice.

### Setup A: MacBook camera + mic
1. Plug in your mic and open **QuickTime Player, File, New Movie Recording**.
2. Click the small arrow next to the red button: **Camera** = FaceTime HD Camera, **Microphone** = your mic, **Quality** = Maximum.
3. Put the teleprompter in a browser window shrunk to a strip at the **top center of the screen, right under the camera**: your eyes stay near the lens.
4. Raise the laptop so the camera is at eye level (stack of books). Light in front of you, not behind.
5. Record one episode per file. Save as `ep1_take01.mov`.
Note: the built-in camera is softer than a phone and noisy in dim rooms, so use the brightest, most even light you can.

### Setup B: phone picture + mic recorded on the Mac
1. **Phone:** landscape, on a tripod or books, right behind or just above the laptop, lens at eye level. Leave the phone's own microphone **on**: it is the reference the tool uses to line up the two recordings (do not mute it).
2. **Mac:** plug in your mic, open **QuickTime Player, File, New Audio Recording**, click the arrow, choose your mic as the input and **Maximum** quality.
3. Start the **phone** recording, then start the **Mac audio** recording, then **clap once** loudly in front of the phone, wait 2 seconds, and begin the episode (a clap is a bonus; the speech alone is enough).
4. Read the teleprompter on the laptop screen.
5. At the end, stay silent for 3 seconds, stop the phone, stop the Mac audio.
6. Save the audio as `ep1_mic.m4a` next to the video `ep1_take01.mov`. Both go into `02-raw/talking-head/`. I run the sync, then the grade.
Keep both recordings running for the whole episode without pausing. If you stop and restart one of them, the two files will not line up.

### Quick check before the real take (both setups)
Record 15 seconds, play it back with headphones: is the voice clear, no hum, mic not touching your breath? In Setup B also check that both the phone and the Mac audio recordings really started.

---

Open [RECORD-TONIGHT.html](RECORD-TONIGHT.html) in a browser: it has the checklist and a link to each episode's teleprompter.

## The one rule that matters most
**The picture must be landscape (16:9).** These are long YouTube videos. AI Producer cannot turn a vertical recording into a horizontal
one, so a vertical take would force a vertical video. On the Mac this is automatic; with the phone, **hold it horizontally**.
(Shorts can be cut later from a landscape master.)

## Phone settings (Setup B, 2 minutes)
- Back camera if you can; selfie camera only if you have a monitor to check framing.
- **4K at 30 fps** if you have the storage (about 1 GB for 5 minutes), otherwise 1080p at 30 fps. The grading step downsizes 4K to
  1080p, which looks sharper than a native 1080p capture.
- Lock exposure and focus (tap and hold on your face until "AE/AF lock"). Lock white balance if your camera app allows it
  (5000 to 5600 K). Turn off HDR and "auto framing". Switch on Do Not Disturb (or airplane mode) so a call cannot ruin a take.
- Lens at eye level, on a tripod or a stack of books. Phone horizontal, lens on the side, not the bottom.
- Wipe the lens. Seriously.

## Green screen (every episode)
I key the green out and put you on the series studio background (dark teal glow), so you match the graphics.
- **Screen:** flat, no wrinkles, evenly lit by two soft lights, one on each side, aimed at the screen only.
- **You:** sit 4 to 6 feet in front of the screen, lit from the front by a separate soft key light, so no green shadow falls on your shoulders or hair.
- **Clothes:** nothing green, teal or light green; no green-framed glasses. Solid dark or warm shirt.
- **Camera:** lock exposure and white balance; same distance, height and framing for every episode. Landscape.
- **Test first:** record 10 seconds turning your head and gesturing with both hands, and give it to me before the real takes. I run `python3 tools/key_green.py clip.mp4 out.png --preview` and fix the lighting advice from the result.
- **Delivery (from the reference channels):** about 160 words a minute, lively, hook first. See `.claude/skills/series-style/SKILL.md`.

## Light, clothes, background (without green screen)
Follow the checklist in [README.md](../../README.md) (key light at 45 degrees, no mixed light sources, solid jewel or earth-tone shirt, curated background).
Quick version: window or soft lamp **in front** of you, ceiling light off, you 4 to 6 feet from the wall, no busy shirt pattern.
Your teal curtain and wood door already look good on camera and match the graphics, so keep that background.

## Sound
Use your good mic, close to your mouth, out of frame. Keep the fan or AC off if you can, and avoid hard desk surfaces right next to the mic.
Do a 15-second test and listen back with headphones before the real take. Leave 5 seconds of silence at the start of every take.

## Teleprompter
- **Setup A:** shrink the browser window to a strip at the top center of the screen, right under the camera.
- **Setup B:** put the laptop right behind or just below the phone so your eyes stay near the lens.
Open the episode teleprompter, press Space to start, arrow up/down for speed, A+ for bigger text.
The orange lines are section labels: read the white lines only.

## How to record each episode
1. Start recording (Setup B: phone first, then the Mac audio, then a clap), then start the teleprompter.
2. Say "Episode N, take one", count to two, then read.
3. **If you mess up a line, pause for two seconds and repeat that sentence.** Do not stop the recording. I cut the retake.
4. Read the whole episode in one continuous take, section after section. Pauses between sections are fine.
5. At the end, stay still and silent for 3 seconds, then stop everything.
6. Play back the first 10 seconds to check light, sound and framing before you do the next episode.

Delivery tips: smile on the first line, talk to the lens like one friend, slow down on project names, vary your pace a little.
It is fine to be slightly slower than the teleprompter default: 3.5 to 4 minutes per episode is the target.

## Pronunciation cheat sheet
| Written | Say |
|---|---|
| PyO3 | pie-oh-three |
| Tiktoken | tick-token |
| Polars | polars |
| Pydantic-core | pie-dantic core |
| Safetensors | safe-tensors |
| Candle | candle |
| Burn | burn |
| Mistral.rs | mistral dot R S |
| Qdrant | quadrant |
| LanceDB | lance D B |
| HNSW | H N S W |
| SIMD | sim-dee |
| GIL | gill |
| CUDA | koo-da |
| maturin | mah-too-rin |
| GGUF | G G U F |

## After recording
Put the files in `videos/<episode folder>/02-raw/talking-head/` (AirDrop, USB or cloud, then move them in), named by episode:
- Setup A: `ep1_take01.mov`
- Setup B: `ep1_take01.mov` (phone video) **and** `ep1_mic.m4a` (the Mac audio), same episode number
Then tell me "footage is in 002" (and so on). I do not touch `02-raw/`. For Setup B I line up the mic with the picture automatically
(`python3 tools/sync_audio.py ep1_take01.mov ep1_mic.m4a ...`), check the result, then grade and edit.

| Folder | Episode |
|---|---|
| `videos/002-rust-ai-ep1-overview` | Ep 1: Python Is the Steering Wheel, Rust Is the Engine |
| `videos/003-rust-ai-ep2-python-stack` | Ep 2: The Hidden Rust Layer Inside Your Python AI Stack |
| `videos/004-rust-ai-ep3-pure-rust-inference` | Ep 3: Running LLMs Without Python |
| `videos/005-rust-ai-ep4-vector-memory` | Ep 4: Why AI Memory Runs on Rust |
| `videos/006-rust-ai-ep5-python-vs-rust` | Ep 5: Python vs. Rust in AI |

## If you only have time for one or two episodes tonight
Do Ep 1 first (it is the playlist kickoff), then Ep 5 or Ep 2. Order does not matter for editing.
