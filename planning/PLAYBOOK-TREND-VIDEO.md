# Playbook: find a trending topic and make the video (works without Claude)

Written 3 Nov 2026 from what made 007 work (46K impressions, 5% CTR, 15K views in 3 days) and what hurt it (half the viewers gone by 0:30).
Ready-made packages built with this method: `videos/012-…`, `videos/013-…`, `videos/014-…` (script, teleprompters, proof, terminal demos, shots.json, title and thumbnail brief).

## 1. Find the topic (30 min, once a week)

A topic is worth a video when **all three** are true:
1. **News from the last 14 days** with a concrete number (lines of code, x faster, days, $).
2. **A famous name or brand** in it (Elon, OpenAI, GitHub, Anthropic, NVIDIA, Linux), so Home shows it to non-developers.
3. **A Rust angle you can prove on your own laptop** (a race, a compiler error, a file size). Proof you run yourself is what separates us from channels that only talk.

Where to look (in this order):
- YouTube search "rust ai", "rewritten in rust", "elon coding", Filters → Upload date: **This week** → Sort by: **View count**. Write down any video with **more views than its channel has subscribers**, or more than 50K views in 7 days. That is the trend signal. 007 copied the idea of "Why AI Infrastructure Is Moving to Rust" (779K views in 13 days).
- daily.dev → "Rust Digest" (weekly), Hacker News front page (search "Rust"), reddit.com/r/rust (Top → This week).
- Google Trends: compare the topic words over the last 7 days, region Worldwide and India.
- X: search the famous name plus "Rust" or "coding", sort by Top.

Do not copy a video. Take the **claim**, then check it yourself and add your own test. Write the topic into `planning/BOARD.md` with a number.

## 2. Verify (1 h)
- Every number must link to the original source (company blog, GitHub repo, official docs). A news site quoting a tweet is not enough; find the tweet or blog.
- Note the caveat the source itself gives (own benchmarks, prototype, not audited). Saying it on camera builds trust; 007's "honest part" kept viewers.
- Save each link in the description draft as you go.

## 3. Script (rules that come from our own analytics)
Template: copy `videos/012-…/01-script/script.md` and replace the content. Keep the `> [CAM]` / `> [READ]` marks.

| Time | What | Rule |
|---|---|---|
| 0:00–0:05 | **Cold open on moving real proof** | A terminal run, a real page scrolling, a number appearing. No logo, no "hi guys", no static tweet. |
| 0:05–0:10 | One concrete claim, on camera | One sentence. |
| 0:10–0:30 | Promise + "let's get into it" | Say what the viewer will see ("I ran three tests…"). |
| before 0:45 | First real proof or demo | 007 waited until 0:46 and lost half its viewers first. |
| ~40 % | One line: why subscribe | "This channel follows the Rust hiding under the AI tools you use every day." |
| near end | Honest caveat, verdict, next video | Verdict in one sentence a non-developer understands. |

- 150–170 words per minute; 6 to 7 minutes is enough.
- About 15 % on camera (short lines), the rest voice-over covered by proof.
- New visual every 3 to 8 s. No static card longer than 5 s in the first minute.
- Explain like the viewer is smart but not a programmer: 99 % of 007's views came from Home, next to non-tech videos.

Free AI that can help with this step: Gemini (free) or Antigravity. Prompt: "Here is my script template and the 6 rules above. Here are my verified facts with links. Write a 6.5-minute documentary script with [CAM] and [READ] lines." Then check every number yourself.

## 4. Proof and demos (before recording)
- Screenshots: `node videos/<ep>/03-edit/capture_proof.js` (needs `npm i playwright` once in any folder; it runs headless, no window). Edit the list of URLs and phrases at the top. It saves a page shot and an amber-highlighted close-up of each key sentence.
- Terminal demos: write a `.tape` file (copy one from `videos/012-…/03-edit/terminal/`) and run `vhs file.tape`. It types the commands and records an MP4 in the channel colours.
- Write `03-edit/shots.json` (which visual goes on which script line); check with `python3 tools/post_record.py videos/<ep> --dry-run`. If this is too much without Claude, skip shots.json and place the visuals by hand in the editor (step 6).

## 5. Record (about 1 h)
- Teleprompters: `python3 series/rust-in-ai/md_to_teleprompter.py SCRIPT "<name>" teleprompter-cam.html --only cam` and `--only read` → `teleprompter-voice.html`.
- Follow the episode's `RECORD-STEPS.md`: camera session (phone + Mac mic, clap per clip, say the C-number once per new line), then voice session (Mac mic only).

## 6. Edit
- With shots.json: `python3 tools/post_record.py videos/<ep>` builds the whole first cut with no AI (best takes, sync, colour, graphics). Result in `03-edit/build/`.
- Then `python3 tools/finish_local.py videos/<ep>`: renders every kit graphic and animation (headless browser, no window), word captions with the amber word, sound effects and a music bed ducked under the voice → `03-edit/build/final-local.mp4`, ready to upload. No AI, about 10 min. Music: one file in `series/rust-in-ai/kit/music/` or `--music file.mp3` (pace around 100 bpm; slow music felt wrong on 007).
- Captions are spelled from the script automatically (`tools/fix_captions.py`, run by `finish_local.py`). If a word is still wrong, add a line `heard words => right words` to `03-edit/caption-fixes.txt` and run `finish_local.py` again (graphics are cached, about 5 min).
- Preview the graphics before recording: `python3 tools/finish_local.py videos/<ep> --build build-dry` (uses the dry-run timing).
- Only for small fixes after that (a typo in a caption, a trim): DaVinci Resolve (free) on `final-local.mp4`.
- With Claude: the AI Producer finish (captions, music, sfx) as on 007.

## 7. Title, thumbnail, publish
- Title = famous name or big number + a question or twist, under 60 characters. Worked: "Why AI Is Quietly Moving to Rust? Elon Was Right!"
- Thumbnail (5 % CTR on 007): one **real receipt** (tweet, headline or terminal line) + the crab + max 3 big words, one amber word.
- Description: 2-line hook, chapters, every source link, the pinned-comment question.
- Publish within 14 days of the news, while it is still in people's feeds. Add an end screen to the previous video and turn on English captions (8 % of 007 viewers used them).
- After 48 h compare: CTR (aim ≥ 5 %), viewers left at 0:30 (aim ≥ 60 %), and write 3 lines in `planning/analytics/`.
