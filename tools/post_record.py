#!/usr/bin/env python3
"""After recording: one command builds the first cut of a documentary-style episode. No AI, no tokens.

  python3 tools/post_record.py videos/NNN-slug             # recordings are in 02-raw/
  python3 tools/post_record.py videos/NNN-slug --dry-run   # no recordings yet: timing faked from the script (155 wpm)
  python3 tools/post_record.py videos/NNN-slug --from base # redo from a step: wav, transcribe, picks, sync, grade, assemble, base, graphics

Reads  01-script/script.md (> [CAM]/[READ] lines), 03-edit/shots.json (what is on screen per script line),
       03-edit/overrides.json (optional, assemble_audio overrides, e.g. {"Test one.": [812.4, 814.1]}),
       02-raw/audio/cam-session.m4a, 02-raw/audio/voice-session.m4a, 02-raw/talking-head/cam-NN.mp4 (never written to).
Writes 03-edit/build/ (or build-dry/): voice.wav, timeline.json, lines.json, words.json, base.mp4 (all real media cut to
       the voice: speaker takes, proof screenshots with a slow push-in, terminal clips), graphics/{main,over}/ (kit
       compositions for AI Producer), sfx.json, report.md (missing takes, weak matches, long shots: read this first).
Each step keeps its output; a step re-runs only if its output is missing or --from names it (or an earlier step).

shots.json: {"lines": {"<script line #>": [item, ...]}, "terminal_dir": "terminal", "proof_dir": "proof"}
  A line with no entry keeps the previous visual running. Items, in order within the line:
    {"cam": true}                                   speaker take (default for [CAM] lines without items)
    {"proof": "x-hl1-zoom.png", "zoom": 0.06}       screenshot, push-in 0..10 %
    {"term": "weights.mp4", "from": "cmd2+1.5", "freeze": false, "speed": 2}   terminal clip from 1.5 s after the
                                                    2nd shown command of its .tape (or seconds after the hidden setup)
    {"kit": {kit spec without id/start/duration}}   full-cover kit graphic (series/rust-in-ai/kit/moments.py)
    {"over": {lower_third / stat_chip spec}, "dur": 3.5}   overlay on top, does not change the base visual
  Every item may carry "at": "@phrase" (first word of the phrase in this line) or seconds from the line start
  (default: the first item at the line start, the rest spread evenly), and "sfx": "ding" (extra sound hint).
  Inside kit specs, "@phrase" values become seconds from the moment's start (same as build_ep1.py).
"""
import json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VPY = Path.home() / ".venvs/rustai/bin/python"           # faster-whisper, rapidfuzz, num2words, numpy, pillow
if VPY.exists() and Path(sys.prefix).resolve() != VPY.parents[1].resolve():
    os.execv(str(VPY), [str(VPY), *sys.argv])             # always run inside the venv (fuzzy cue matching needs it)
from rapidfuzz import fuzz
from num2words import num2words
FPS, W, H = 30, 1920, 1080
WPM = 155
TERM_BG = "0x07191a"
STEPS = ["wav", "transcribe", "picks", "sync", "grade", "assemble", "base", "graphics"]
sys.path.insert(0, str(ROOT / "series/rust-in-ai/kit"))


def sh(cmd, **kw):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    if r.returncode:
        sys.exit(f"FAILED: {' '.join(map(str, cmd))}\n{r.stderr[-2000:]}")
    return r.stdout


def dur(p):
    return float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).strip())


def words_norm(s):
    """Same spelling rules as pick_takes.py: digits to words, "x.y" to "x dot y", no punctuation."""
    s = s.lower().replace("%", " percent ").replace("++", " plus plus")
    s = re.sub(r"(?<=[a-z])\.(?=[a-z])", " dot ", s)
    s = re.sub(r"(\d+)\.(\d+)", lambda m: num2words(int(m[1])) + " point " + " ".join(num2words(int(c)) for c in m[2]), s)
    s = re.sub(r"\d+", lambda m: num2words(int(m[0])), s)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", s.replace("-", " "))).strip()


# ---------------------------------------------------------------- script and tapes
def script_lines(path):
    out = []
    for l in Path(path).read_text().splitlines():
        m = re.match(r"> \[(CAM|READ)\] (.*)", l)
        if m:
            out.append({"line": len(out) + 1, "mode": m[1], "text": m[2]})
    return out


def tape_marks(tape):
    """Visible timeline of a vhs tape: (content start, [start of each shown command]) in seconds of the mp4.
    Content starts at the first Show that follows a Hide (setup typing before it is trimmed off)."""
    speed, t, vis, hid, start, cmds = 0.05, 0.0, True, False, None, []
    for l in Path(tape).read_text().splitlines():
        l = l.strip()
        if m := re.match(r"Set TypingSpeed (\d+)ms", l): speed = int(m[1]) / 1000
        elif l == "Hide": vis, hid = False, True
        elif l == "Show":
            vis = True
            if hid and start is None: start = t
        elif m := re.match(r"Type (['\"`])(.*)\1", l):
            if vis and start is not None: cmds.append(t)
            if vis: t += len(m[2]) * speed
        elif l.startswith("Enter") and vis: t += speed
        elif m := re.match(r"Sleep ([\d.]+)(ms|s)", l):
            if vis: t += float(m[1]) / (1000 if m[2] == "ms" else 1)
    if start:                                   # measured on 008: the hidden setup ends ~0.25 s later than typed time
        start += 0.25; cmds = [start] + [c + 0.15 for c in cmds[1:]]
    return (start or 0.0), cmds


# ---------------------------------------------------------------- steps
class Ep:
    def __init__(self, vdir, dry, redo):
        self.v = Path(vdir).resolve(); self.dry = dry
        self.raw = self.v / "02-raw"; self.edit = self.v / "03-edit"
        self.b = self.edit / ("build-dry" if dry else "build"); self.b.mkdir(parents=True, exist_ok=True)
        self.redo = STEPS.index(redo) if redo else 99
        self.script = self.v / "01-script/script.md"
        self.lines = script_lines(self.script)
        self.shots = json.loads((self.edit / "shots.json").read_text()) if (self.edit / "shots.json").exists() else {"lines": {}}
        self.notes = []

    def audio(self, name):
        for ext in ("m4a", "aifc", "aif", "wav", "mp3"):
            f = self.raw / f"audio/{name}-session.{ext}"
            if f.exists(): return f
        sys.exit(f"missing {self.raw / f'audio/{name}-session.m4a'} (or .aifc/.wav/.mp3)")

    def need(self, step, *outs):
        return STEPS.index(step) >= self.redo or not all((self.b / o).exists() for o in outs)

    # 1-4: audio, transcripts, picks, sync (real mode only)
    def wav(self):
        for name in ("cam", "voice"):
            src = self.audio(name)
            if self.need("wav", f"{name}48.wav"):
                sh(["ffmpeg", "-v", "error", "-y", "-i", src, "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", self.b / f"{name}48.wav"])
        if self.need("wav", "mic48.wav"):   # one file for assemble_audio: cam session, then voice session
            sh(["ffmpeg", "-v", "error", "-y", "-i", self.b / "cam48.wav", "-i", self.b / "voice48.wav",
                "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1", "-c:a", "pcm_s16le", self.b / "mic48.wav"])
        self.cam_len = dur(self.b / "cam48.wav")

    def transcribe(self):
        for name in ("cam", "voice"):
            if self.need("transcribe", f"{name}.tr.json"):
                print(f"transcribing {name} session (a few minutes)…")
                sh([VPY, ROOT / "tools/transcribe.py", self.b / f"{name}48.wav", self.b / f"{name}.tr.json"])

    def picks(self):
        if self.need("picks", "picks.json"):
            for name in ("cam", "read"):
                tr = "cam" if name == "cam" else "voice"
                sh([VPY, ROOT / "tools/pick_takes.py", self.script, self.b / f"{tr}.tr.json", self.b / f"picks_{name}.json", "--only", name, *(["--last"] if self.shots.get("prefer_last_take") else [])])
            cam = json.load(open(self.b / "picks_cam.json"))
            rd = json.load(open(self.b / "picks_read.json"))
            for p in rd:
                p["src"] = "voice"
                if p.get("found"): p["start"] += self.cam_len; p["end"] += self.cam_len
            for p in cam: p["src"] = "cam"
            allp = sorted(cam + rd, key=lambda p: p["line"])      # stable: keeps sentence order inside a line
            json.dump(allp, open(self.b / "picks.json", "w"), indent=1)
        self.pk = json.load(open(self.b / "picks.json"))
        for p in self.pk:
            if not p.get("found"): self.notes.append(f"NOT FOUND line {p['line']} ({p['mode']}): {p['text']}")
            elif p["score"] < 0.9: self.notes.append(f"weak match {p['score']} line {p['line']}: said \"{p['heard']}\"")

    def sync(self):
        clips = sorted((self.raw / "talking-head").glob("cam-*.mp4"))
        if not clips: sys.exit("no 02-raw/talking-head/cam-NN.mp4")
        if self.need("sync", "sync.json"):
            mic = self.audio("cam"); md = dur(mic); res = []
            for c in clips:
                out = sh([sys.executable, ROOT / "tools/sync_audio.py", c, mic, "--report", "--max-lag", f"{md:.0f}"])
                m = re.search(r"offset at start: ([+-]\d+) ms\s+\(confidence ([\d.]+)", out)
                res.append({"clip": c.name, "lag": int(m[1]) / 1000, "conf": float(m[2]), "dur": dur(c)})
                print(f"  {c.name}: phone starts at {res[-1]['lag']:.2f} s of the cam mic (confidence {m[2]})")
            json.dump(res, open(self.b / "sync.json", "w"), indent=1)
        self.sync_ = json.load(open(self.b / "sync.json"))

    def grade(self):
        out = self.edit / "processed"
        preset = self.shots.get("cam_preset", "series-standard")      # an episode preset in color-grading/presets/
        cc = self.shots.get("cam_crop")      # hide the room: crop the 4K frame (16:9 kept) before the 1920 scale, so no upscaling
        if cc:
            chain = (ROOT / "color-grading/presets/series-standard.txt").read_text().strip().splitlines()[-1]
            preset = "_ep-cropped"
            (ROOT / f"color-grading/presets/{preset}.txt").write_text(
                f"crop=iw*{cc['w']}:ih*{cc['w']}:iw*{cc['x']}:ih*{cc['y']},{chain}\n")
        for s in self.sync_:
            stem = Path(s["clip"]).stem
            if STEPS.index("grade") >= self.redo or not list(out.glob(f"{stem}_graded.*")):
                print(f"grading {s['clip']} (series-standard)…")
                sh([ROOT / "color-grading/preprocess.sh", "--preset", preset, "--outdir", out, self.raw / "talking-head" / s["clip"]])
            s["graded"] = str(next(out.glob(f"{stem}_graded.*")))

    def assemble(self):
        if self.need("assemble", "voice.wav", "timeline.json"):
            ov = (self.edit / "overrides.json").read_text() if (self.edit / "overrides.json").exists() else "{}"
            print(sh([VPY, ROOT / "tools/assemble_audio.py", self.b / "mic48.wav", self.b / "picks.json", self.b / "voice", "--override", ov,
                         "--gap", self.shots.get("gap", 0.2), "--sec-gap", self.shots.get("sec_gap", 0.4),
                         *(["--level", self.shots["voice_level"], "--cam-offset", self.shots.get("cam_level_offset", 0)] if self.shots.get("voice_level") is not None else [])]).strip())
            (self.b / "voice.timeline.json").rename(self.b / "timeline.json")
        self.tl = json.load(open(self.b / "timeline.json"))
        # words of the finished cut (for "@phrase" cues): transcript words inside each unit, moved to cut time
        tw = []
        for name, shift in (("cam", 0.0), ("voice", self.cam_len)):
            tw += [[w[0] + shift, w[1] + shift, w[2]] for seg in json.load(open(self.b / f"{name}.tr.json")) for w in seg["w"]]
        tw.sort()
        words = []
        for u in self.tl:
            for w in tw:
                if u["mic0"] - 0.05 <= w[0] < u["mic1"]:
                    words.append([w[2].strip(), round(u["t0"] + w[0] - u["mic0"], 3), round(u["t0"] + w[1] - u["mic0"], 3)])
        # better: the finished cut transcribed again (check_cut.py, medium.en). Session words mapped through the units drop a
        # unit's first word or pull in a neighbour's ("Cam", a retake's last word) when Whisper's times drift (009 captions)
        ct = self.b / "cut.tr.json"
        if ct.exists() and ct.stat().st_mtime > (self.b / "voice.wav").stat().st_mtime:
            words = [[w[2].strip(), w[0], w[1]] for seg in json.load(open(ct)) for w in seg["w"] if w[2].strip()]
        json.dump(words, open(self.b / "words.json", "w"))
        self.words = words
        self.total = self.tl[-1]["t1"] + 0.8

    def dry_assemble(self):
        """No recordings: every script line takes its word count at 155 wpm, 0.35 s pause between lines."""
        t, words, tl = 0.5, [], []
        for L in self.lines:
            t0 = t
            for w in L["text"].split():
                d = 60 / WPM * (1.6 if w[-1] in ".,?!" else 1.0); words.append([w, round(t, 3), round(t + d * 0.85, 3)]); t += d
            tl.append({"text": L["text"], "mode": L["mode"], "t0": round(t0, 3), "t1": round(t, 3), "lines": [[L["line"], round(t0, 3)]], "src": "dry"})
            t += 0.35
        self.tl, self.words, self.total = tl, words, t + 0.8
        json.dump(tl, open(self.b / "timeline.json", "w"), indent=1); json.dump(words, open(self.b / "words.json", "w"))
        sh(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", f"{self.total:.2f}", self.b / "voice.wav"])

    # 5: plan every visual on the cut timeline
    def line_spans(self):
        starts = {}
        for u in self.tl:
            for ln, t in u["lines"]:
                if ln is not None and ln not in starts: starts[ln] = t
        ks = sorted(starts)
        for L in self.lines:
            if L["line"] not in starts: self.notes.append(f"line {L['line']} has no take, its visuals are skipped")
        spans = {k: [starts[k], starts[ks[i + 1]] if i + 1 < len(ks) else self.total] for i, k in enumerate(ks)}
        json.dump(spans, open(self.b / "lines.json", "w"), indent=1)
        return spans

    def cue(self, phrase, t_from, t_to):
        """Start time of the spoken phrase inside [t_from, t_to): fuzzy, so "8 threads" or "Saffertensors" still match."""
        want = words_norm(phrase); n = len(want.split())
        best = (0, None)
        for i, w in enumerate(self.words):
            if not (t_from - 0.3 <= w[1] < t_to): continue
            for k in (n, n + 1, max(n - 1, 1)):
                hyp = words_norm(" ".join(x[0] for x in self.words[i:i + k]))
                sc = fuzz.ratio(want, hyp)
                if sc > best[0] + 0.5: best = (sc, w[1])
        if best[0] >= 75: return best[1]
        self.notes.append(f"cue not found in its line: \"{phrase}\" (used the line start)")
        return t_from

    def resolve(self, v, t0, span):
        if isinstance(v, str) and v.startswith("@"):
            m = re.match(r"^@(.*?)(?:([+-][\d.]+))?$", v)
            return round(max(self.cue(m[1], *span) + float(m[2] or 0) - t0, 0), 2)
        if isinstance(v, list): return [self.resolve(x, t0, span) for x in v]
        if isinstance(v, dict): return {k: self.resolve(x, t0, span) for k, x in v.items()}
        return v

    def plan(self):
        spans = self.line_spans(); base, over = [], []
        for L in self.lines:
            k = L["line"]
            if k not in spans: continue
            s, e = spans[k]
            items = self.shots["lines"].get(str(k)) or ([{"cam": True}] if L["mode"] == "CAM" else [])
            n_main = sum(1 for it in items if "over" not in it); i_main = 0
            for it in items:
                at = it.get("at")
                if isinstance(at, str):
                    m = re.match(r"^@(.*?)(?:([+-][\d.]+))?$", at); t = self.cue(m[1], s, e) + float(m[2] or 0)
                elif isinstance(at, (int, float)): t = s + at
                elif "over" in it: t = s
                else: t = s + (e - s) * i_main / max(n_main, 1)
                if "over" not in it: i_main += 1
                rec = dict(it, t=round(t, 3), line=k, span=[s, e])
                (over if "over" in it else base).append(rec)
        if not base or base[0]["t"] > 0.01: base.insert(0, {"kit": None, "t": 0.0, "line": 0, "span": [0, 0]})
        base.sort(key=lambda r: r["t"]); over.sort(key=lambda r: r["t"])
        # a camera shot that spans a cut inside the speech (a long stall was removed) is split there, so the picture follows the audio cut
        cuts = [u["t0"] for u in self.tl if u["mode"] == "CAM" and u.get("src", "cam") != "voice"]
        out = []
        for i, r in enumerate(base):
            end = base[i + 1]["t"] if i + 1 < len(base) else self.total
            out.append(r)
            if r.get("cam"):
                for c in cuts:
                    if r["t"] + 0.02 < c < end - 0.02:      # every camera take starts its own shot, so lips stay on the voice
                        out.append(dict(r, t=round(c, 3)))
        base = sorted(out, key=lambda r: r["t"])
        # leave the speaker when the speech ends, not after the pause: he looks down at the script right after a line (009 review)
        cam_ends = [u["t1"] for u in self.tl if u["mode"] == "CAM" and u.get("src", "cam") != "voice"]
        for i in range(len(base) - 1):
            r, n = base[i], base[i + 1]
            if r.get("cam") and not n.get("cam"):
                ends = [x for x in cam_ends if r["t"] < x <= n["t"] + 0.01]
                if ends: n["t"] = round(min(n["t"], max(ends) - self.shots.get("cam_exit", 0.25)), 3)   # J-cut: the last syllable plays under the next visual
        for i, r in enumerate(base): r["end"] = base[i + 1]["t"] if i + 1 < len(base) else self.total
        base = [r for r in base if r["end"] - r["t"] >= 1 / FPS]
        for r in base:
            d = r["end"] - r["t"]
            if d > 8.5 and not r.get("cam"): self.notes.append(f"line {r['line']}: one visual for {d:.1f} s (style: new visual every 3-8 s)")
        self.base, self.over = base, over
        return base, over

    # 6: base video = real media only; kit slots stay as the studio ground (AI Producer draws the graphic on top)
    def cam_source(self, t_cut):
        for u in sorted((u for u in self.tl if u["t0"] - 0.5 <= t_cut <= u["t1"] + 0.6 and u.get("src", "cam") != "voice" and u["mode"] == "CAM"),
                        key=lambda u: max(u["t0"] - t_cut, t_cut - u["t1"], 0)):       # the unit that contains the cut time first
            if True:
                mic = u["mic0"] + (t_cut - u["t0"])
                for s in self.sync_:
                    if s["lag"] <= mic <= s["lag"] + s["dur"] - 0.2:
                        return s["graded"], mic - s["lag"]
        return None, 0

    def seg(self, i, r):
        f0, f1 = round(r["t"] * FPS), round(r["end"] * FPS); n = f1 - f0
        out = self.b / "seg" / f"{i:04d}.mp4"; d = n / FPS
        enc = ["-an", "-r", str(FPS), "-frames:v", str(n), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", out]
        bg = self.edit / self.shots["studio_bg"] if self.shots.get("studio_bg") else ROOT / "series/rust-in-ai/kit/studio-bg.png"
        cover = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1"
        if r.get("cam") and not self.dry:
            src, tin = self.cam_source(r["t"])
            if src:
                return sh(["ffmpeg", "-v", "error", "-y", "-ss", f"{tin:.3f}", "-i", src, "-vf", cover + ",tpad=stop_mode=clone:stop_duration=10", *enc])
            self.notes.append(f"line {r['line']}: no phone clip covers this CAM take, used the studio background")
        if r.get("proof"):
            img = self.edit / self.shots.get("proof_dir", "proof") / r["proof"]
            z = min(float(r.get("zoom", 0.06)), 0.10)
            vf = (f"scale=3840:2160:force_original_aspect_ratio=decrease,pad=3840:2160:(ow-iw)/2:(oh-ih)/2:color={self.shots.get('proof_pad', '0xe4efeb')},"
                  f"zoompan=z='1+{z}*on/{max(n - 1, 1)}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={W}x{H}:fps={FPS}")
            return sh(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-i", img, "-vf", vf, *enc])
        if r.get("term"):
            tdir = self.edit / self.shots.get("terminal_dir", "terminal"); clip = tdir / r["term"]
            start, cmds = tape_marks(clip.with_suffix(".tape")) if clip.with_suffix(".tape").exists() else (0.0, [])
            fr = r.get("from", 0)
            if isinstance(fr, str) and fr.startswith("cmd"):
                m = re.match(r"cmd(\d+)([+-][\d.]+)?", fr); tin = cmds[int(m[1]) - 1] + float(m[2] or 0)
            else: tin = start + float(fr)
            sp = f"setpts=PTS/{float(r['speed'])}," if r.get("speed") else ""     # fast-forward a long wait
            hold = (",trim=end_frame=1" if r.get("freeze") else "") + f",tpad=stop_mode=clone:stop_duration={d + 1}"
            if self.shots.get("term_box"):        # terminal as a rounded window on the episode ground (shots.json term_box, term_ground, term_mask)
                x, y, w, h = self.shots["term_box"]
                fc = (f"[0:v]{sp}scale={w}:{h},setsar=1{hold}[t];[t][2:v]alphamerge[tw];[1:v]loop=-1:1,setsar=1[g];"
                      f"[g][tw]overlay={x}:{y}:shortest=1,format=yuv420p")
                return sh(["ffmpeg", "-v", "error", "-y", "-ss", f"{tin:.3f}", "-i", clip, "-i", self.edit / self.shots["term_ground"],
                           "-loop", "1", "-i", self.edit / self.shots["term_mask"], "-filter_complex", fc, *enc])
            pad = f"{sp}scale={W}:-2,pad={W}:{H}:0:(oh-ih)/2:color={TERM_BG},setsar=1"
            return sh(["ffmpeg", "-v", "error", "-y", "-ss", f"{tin:.3f}", "-i", clip, "-vf", pad + hold, *enc])
        img = bg
        if self.dry and r.get("cam"):
            img = self.placeholder(r["line"])
        return sh(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-i", img, "-vf", cover, *enc])

    def placeholder(self, line):
        p = self.b / "seg" / f"cam-{line}.png"
        if not p.exists():
            try:
                from PIL import Image, ImageDraw, ImageFont
                im = Image.open(ROOT / "series/rust-in-ai/kit/studio-bg.png").convert("RGB"); d = ImageDraw.Draw(im)
                f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 90)
                c = sum(1 for L in self.lines if L["mode"] == "CAM" and L["line"] <= line)
                d.text((W // 2, H // 2), f"SPEAKER  C{c}", fill=(40, 60, 60), font=f, anchor="mm"); im.save(p)
            except Exception:
                return ROOT / "series/rust-in-ai/kit/studio-bg.png"
        return p

    def render_base(self):
        if not self.need("base", "base.mp4"): return
        (self.b / "seg").mkdir(exist_ok=True)
        for i, r in enumerate(self.base):
            self.seg(i, r); print(f"\r  base video: segment {i + 1}/{len(self.base)}", end="")
        print()
        lst = self.b / "seg" / "list.txt"
        lst.write_text("".join(f"file '{i:04d}.mp4'\n" for i in range(len(self.base))))
        sh(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", self.b / "voice.wav",
            "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", self.b / "base.mp4"])
        print(f"wrote {self.b / 'base.mp4'} ({dur(self.b / 'base.mp4'):.1f} s)")

    # 7: kit graphics + sound plan for AI Producer
    def graphics(self):
        import moments as K
        main, over, sfx = [], [], []
        for i, r in enumerate(self.base):
            if r.get("kit"):
                d = dict(r["kit"]); d.update(id=f"l{r['line']:02d}-{i}", start=round(r["t"], 2), duration=round(round(r["end"], 2) - round(r["t"], 2), 2))
                main.append({k: (self.resolve(v, r["t"], [r["t"], r["end"]]) if k not in ("id", "type", "start", "duration") else v) for k, v in d.items()})
            elif (r.get("proof") or r.get("term")) and (i == 0 or not (self.base[i - 1].get("proof") or self.base[i - 1].get("term"))):
                sfx.append({"t": round(r["t"], 2), "hint": "whoosh", "why": f"line {r['line']} proof enters"})
            if r.get("sfx"): sfx.append({"t": round(r["t"], 2), "hint": r["sfx"], "why": f"line {r['line']}"})
        for j, r in enumerate(self.over):
            nxt = self.over[j + 1]["t"] if j + 1 < len(self.over) else self.total
            d = dict(r["over"]); d.update(id=f"o{r['line']:02d}", start=round(r["t"], 2), duration=round(min(float(r.get("dur", 3.5)), round(nxt, 2) - round(r["t"], 2) - 0.05), 2))
            over.append({k: (self.resolve(v, r["t"], r["span"]) if k not in ("id", "type", "start", "duration") else v) for k, v in d.items()})
            if r.get("sfx"): sfx.append({"t": round(r["t"], 2), "hint": r["sfx"], "why": f"line {r['line']}"})
        g = self.b / "graphics"
        for name, ms in (("main", main), ("over", over)):
            spec = {"theme": self.shots.get("theme"), "moments": ms}      # shots.json "theme": kit variant, e.g. studio-red
            json.dump(spec, open(g.parent / f"spec_{name}.json", "w"), indent=1)
            if ms: K.build(spec, str(g / name))
        for h in (json.load(open(g / "main/sfx_hints.json")) if main else []):
            sfx.append({"t": h["start"], "hint": h["hint"], "why": h["id"]})
        sfx.sort(key=lambda x: x["t"])
        json.dump(sfx, open(self.b / "sfx.json", "w"), indent=1)
        print(f"graphics: {len(main)} full-cover, {len(over)} overlays, {len(sfx)} sound hints")

    def report(self):
        n_cam = sum(1 for r in self.base if r.get("cam"))
        rel = lambda p: p.relative_to(ROOT) if p.is_relative_to(ROOT) else p
        txt = [f"# Build report ({'DRY RUN, timing faked from the script' if self.dry else 'real recordings'})", "",
               f"- Length: {self.total / 60:.1f} min, {len(self.base)} visuals ({n_cam} speaker shots), {len(self.over)} overlays",
               f"- Base video: `{rel(self.b / 'base.mp4')}`  Graphics: `{rel(self.b / 'graphics')}/`", "",
               "## Check these", ""] + [f"- {n}" for n in dict.fromkeys(self.notes)] + (["- nothing"] if not self.notes else [])
        (self.b / "report.md").write_text("\n".join(txt) + "\n")
        print("\n".join(txt))

    def run(self):
        if self.dry:
            self.dry_assemble()
        else:
            self.wav(); self.transcribe(); self.picks(); self.sync(); self.grade(); self.assemble()
        self.plan(); self.render_base(); self.graphics(); self.report()


if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(__doc__)
    a = sys.argv
    Ep(a[1], "--dry-run" in a, a[a.index("--from") + 1] if "--from" in a else None).run()
