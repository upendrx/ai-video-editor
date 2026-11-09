# Record steps: 007 Elon said Rust

Two separate sessions. Order does not matter. Retakes are fine everywhere: the last good take of each sentence is picked automatically.

## Session 1: camera (about 5 to 7 min with retakes)
Teleprompter: `01-script/teleprompter-cam.html` (16 lines, C1 to C16). Put it directly under the phone lens.

1. Start the **Mac mic** recording first and leave it running for the whole session.
2. Start the **phone** video (landscape, real background, same framing as the other episodes).
3. **Clap once** (this lines the phone up with the mic).
4. When you START a new line, say its number once ("cam one"), pause 2 s, then say the line looking at the lens, pause 2 s.
   Retakes: do NOT repeat the number, just say the line again after the pause. 2 or 3 tries with different energy is great.
   Forgot a number? No problem, takes are matched by their words.
5. Before the phone hits 8 min: stop it, start a new phone clip, **clap again**, carry on. The mic keeps running.
6. Hold still and silent for 3 s at the end.

Files: phone clips → `02-raw/talking-head/cam-01.mp4`, `cam-02.mp4`…  Mic → `02-raw/audio/cam-session.m4a`

## Session 2: voice only (about 6 to 8 min with retakes)
Teleprompter: `01-script/teleprompter-voice.html`. No camera.

1. Start the Mac mic. Clap once.
2. Read calmly, like explaining to a friend. Grey lines are camera lines: skip them.
3. Trip on a word? Pause 2 s and say the whole sentence again.

File: `02-raw/audio/voice-session.m4a`

## Then
Drop the files in and run `python3 tools/post_record.py videos/007-rust-ai-elon-was-right`, then read `03-edit/build/report.md`. Then a short Claude session for the AI Producer finish.
