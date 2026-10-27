#!/usr/bin/env python3
"""Replace a video's audio with a separately recorded (better) mic track, aligned automatically.

Use when the picture comes from the phone and the voice from a mic recorded on a computer.
Both recordings must contain the same speech (the phone's own mic audio is the reference).

  python3 tools/sync_audio.py PHONE_VIDEO MIC_AUDIO OUT.mp4
  python3 tools/sync_audio.py PHONE_VIDEO MIC_AUDIO --report      # only print the measured offset

How it works: both tracks are band-passed to the speech range, cross-correlated with an FFT to find the offset,
and re-checked near the end of the recording to catch clock drift (phone and computer clocks differ by a few
milliseconds per minute). A tiny `atempo` correction is applied only if the drift is large enough to matter.
The video stream is copied untouched. Needs: ffmpeg, numpy.
"""
import argparse
import subprocess
import sys
import numpy as np

SR = 8000  # analysis sample rate


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def load(path, start=0.0, dur=None):
    cmd = ["ffmpeg", "-v", "error"]
    if start > 0:  # never pass -ss 0: on AAC files it drops the first 1024 priming samples (64 ms at 16 kHz)
        cmd += ["-ss", f"{start:.3f}"]
    if dur:
        cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-af", "highpass=f=120,lowpass=f=3400", "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def xcorr(ref, other, max_lag_s):
    """Return (lag_seconds, confidence) such that other[t + lag] matches ref[t]."""
    n = 1 << int(np.ceil(np.log2(len(ref) + len(other))))
    A = np.fft.rfft(ref - ref.mean(), n)
    B = np.fft.rfft(other - other.mean(), n)
    c = np.fft.irfft(B * np.conj(A), n)
    L = int(max_lag_s * SR)
    L = min(L, n // 2 - 1)
    vals = np.r_[c[: L + 1], c[n - L:]]
    lags = np.r_[np.arange(0, L + 1), np.arange(-L, 0)]
    j = int(np.argmax(vals))
    conf = float((vals[j] - vals.mean()) / (vals.std() + 1e-12))
    return lags[j] / SR, conf


def local_lag(video, mic, t, length, guess, search):
    """Offset (mic time minus phone time) measured in one short window around phone time t."""
    ref = load(video, t, length)
    mstart = max(t + guess - search, 0.0)
    oth = load(mic, mstart, length + 2 * search)
    lag, conf = xcorr(ref, oth, search * 2)
    return lag + (mstart - t), conf


def measure(video, mic, max_lag, probe=90.0, win=20.0):
    dv, dm = duration(video), duration(mic)
    # 1) coarse offset from the first minutes of both recordings
    ref = load(video, 0, probe + max_lag)
    oth = load(mic, 0, probe + 2 * max_lag)
    lag0, conf0 = xcorr(ref, oth, max_lag)
    out = dict(lag=lag0, conf=conf0, rate=0.0, dv=dv, dm=dm, conf_end=conf0, lag_end=lag0, tail=None)
    if dv < 120 or dm < 120:
        return out
    # 2) fine offsets in two short windows (near the start and near the end) -> clock drift
    t1, t2 = 10.0, dv - win - 10.0
    la, ca = local_lag(video, mic, t1, win, lag0, 1.0)
    lb, cb = local_lag(video, mic, t2, win, lag0 + 0.0, 1.0)
    rate = (lb - la) / (t2 - t1)
    out.update(lag=la - rate * (t1 + win / 2), conf=min(conf0, ca), lag_end=lb, conf_end=cb, rate=rate, tail=t2)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("mic"); ap.add_argument("out", nargs="?")
    ap.add_argument("--max-lag", type=float, default=60.0, help="largest start-time difference to search, seconds (default 60)")
    ap.add_argument("--report", action="store_true", help="measure only, do not write a file")
    ap.add_argument("--bitrate", default="256k")
    a = ap.parse_args()
    if not a.report and not a.out:
        ap.error("OUT.mp4 is required unless --report is given")

    m = measure(a.video, a.mic, a.max_lag)
    print(f"offset at start: {m['lag']*1000:+.0f} ms  (confidence {m['conf']:.1f})")
    if m["tail"] is not None:
        print(f"offset near end: {m['lag_end']*1000:+.0f} ms  (confidence {m['conf_end']:.1f}),  drift {m['rate']*m['dv']*1000:+.0f} ms over {m['dv']:.0f} s")
    if m["conf"] < 6:
        sys.exit("Low confidence: the two recordings may not contain the same speech, or one is silent. Check the files (or add a clap at the start).")
    if a.report:
        return

    lag, filters = m["lag"], []
    use_tempo = m["tail"] is not None and abs(m["rate"] * m["dv"]) > 0.040 and m["conf_end"] >= 6
    if use_tempo:
        # mic time = phone time * (1 + rate) + lag0  ->  after trimming lag0, consume the mic at speed (1 + rate)
        factor = 1.0 + m["rate"]
        filters.append(f"atempo={factor:.6f}")
        print(f"applying drift correction atempo={factor:.6f}")
    dv = m["dv"]
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", a.video]
    if lag >= 0:
        cmd += ["-ss", f"{lag:.4f}", "-i", a.mic]          # mic started earlier: skip its head
    else:
        cmd += ["-i", a.mic]
        filters.insert(0, f"adelay={int(round(-lag*1000))}:all=1")  # mic started later: pad silence
    filters.append("apad")
    cmd += ["-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-af", ",".join(filters),
            "-c:a", "aac", "-b:a", a.bitrate, "-t", f"{dv:.3f}", "-movflags", "+faststart", a.out]
    subprocess.run(cmd, check=True)

    # verify: the phone's own audio vs the new audio should now line up at ~0 ms
    ref = load(a.video, 5, 60); new = load(a.out, 5, 60)
    resid, conf = xcorr(ref, new, 1.0)
    print(f"wrote {a.out}  (residual offset {resid*1000:+.1f} ms, confidence {conf:.1f})")
    if abs(resid) > 0.03:
        print("WARNING: residual offset above 30 ms; check the result by ear.")


if __name__ == "__main__":
    main()
