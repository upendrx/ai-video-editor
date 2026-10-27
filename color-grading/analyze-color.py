#!/usr/bin/env python3
"""
analyze-color.py — Analyze video color balance and suggest corrections.

Samples frames from a video, detects faces/skin regions, and reports:
  - Auto white balance gains (Gray World algorithm)
  - Average skin tone HSV values
  - Suggested FFmpeg eq/colorbalance parameters
  - Whether a LUT is likely to help

Usage:
    python3 color-grading/analyze-color.py <video_file>
    python3 color-grading/analyze-color.py --frames 10 take01.mov
"""

import sys
import argparse
import os

try:
    import cv2
    import numpy as np
except ImportError:
    print("ERROR: opencv-python and numpy are required.")
    print("Install with: pip install opencv-python numpy")
    sys.exit(1)


def sample_frames(video_path, num_frames=5):
    """Extract evenly spaced frames from a video."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"ERROR: Cannot open video: {video_path}")
        sys.exit(1)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames < 1:
        print("ERROR: Video has no frames.")
        sys.exit(1)

    indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
    frames = []

    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            frames.append(frame)

    cap.release()
    return frames


def detect_skin_mask(frame):
    """Detect skin regions using HSV color thresholding."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Skin tone HSV range (tuned for diverse skin tones)
    lower_skin = np.array([0, 20, 70], dtype=np.uint8)
    upper_skin = np.array([30, 255, 255], dtype=np.uint8)
    mask1 = cv2.inRange(hsv, lower_skin, upper_skin)

    # Extended range for darker tones
    lower_skin2 = np.array([160, 20, 70], dtype=np.uint8)
    upper_skin2 = np.array([180, 255, 255], dtype=np.uint8)
    mask2 = cv2.inRange(hsv, lower_skin2, upper_skin2)

    mask = mask1 | mask2

    # Clean up the mask
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    mask = cv2.erode(mask, kernel, iterations=2)
    mask = cv2.dilate(mask, kernel, iterations=2)

    return mask


def analyze_white_balance(frame):
    """Compute Gray World white balance gains."""
    b_avg = np.mean(frame[:, :, 0])
    g_avg = np.mean(frame[:, :, 1])
    r_avg = np.mean(frame[:, :, 2])

    overall_avg = (b_avg + g_avg + r_avg) / 3.0

    gain_r = overall_avg / (r_avg + 1e-6)
    gain_g = overall_avg / (g_avg + 1e-6)
    gain_b = overall_avg / (b_avg + 1e-6)

    return {
        "r_avg": r_avg,
        "g_avg": g_avg,
        "b_avg": b_avg,
        "gain_r": gain_r,
        "gain_g": gain_g,
        "gain_b": gain_b,
        "dominant_cast": (
            "blue" if b_avg > r_avg and b_avg > g_avg else
            "red/warm" if r_avg > b_avg and r_avg > g_avg else
            "green"
        ),
    }


def analyze_skin_tones(frame, mask):
    """Analyze skin tone distribution in HSV."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    skin_pixels = hsv[mask > 0]

    if len(skin_pixels) < 100:
        return None

    h_mean, s_mean, v_mean = np.mean(skin_pixels, axis=0)
    h_std, s_std, v_std = np.std(skin_pixels, axis=0)

    return {
        "h_mean": h_mean,
        "s_mean": s_mean,
        "v_mean": v_mean,
        "h_std": h_std,
        "s_std": s_std,
        "v_std": v_std,
        "pixel_count": len(skin_pixels),
        "frame_coverage_pct": len(skin_pixels) / (frame.shape[0] * frame.shape[1]) * 100,
    }


def analyze_exposure(frame):
    """Analyze overall exposure (brightness distribution)."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mean_brightness = np.mean(gray)
    std_brightness = np.std(gray)

    # Check for clipping
    dark_pct = np.sum(gray < 16) / gray.size * 100
    bright_pct = np.sum(gray > 240) / gray.size * 100

    return {
        "mean_brightness": mean_brightness,
        "std_brightness": std_brightness,
        "dark_clipping_pct": dark_pct,
        "bright_clipping_pct": bright_pct,
        "assessment": (
            "UNDEREXPOSED" if mean_brightness < 80 else
            "OVEREXPOSED" if mean_brightness > 180 else
            "GOOD"
        ),
    }


def suggest_corrections(wb, skin, exposure):
    """Generate FFmpeg correction suggestions."""
    suggestions = []

    # White balance
    if abs(wb["gain_r"] - 1.0) > 0.05 or abs(wb["gain_b"] - 1.0) > 0.05:
        rs = round((wb["gain_r"] - 1.0) * 0.3, 3)
        bs = round((wb["gain_b"] - 1.0) * 0.3, 3)
        suggestions.append({
            "issue": f"Color cast detected ({wb['dominant_cast']})",
            "fix": f"colorbalance=rs={rs}:gs=0:bs={bs}:rm={rs}:gm=0:bm={bs}",
            "or": "Use grayworld filter for automatic correction",
        })

    # Exposure
    if exposure["assessment"] == "UNDEREXPOSED":
        brightness = round(0.04 + (80 - exposure["mean_brightness"]) / 1000, 3)
        gamma = round(0.85 + (exposure["mean_brightness"] / 200), 3)
        suggestions.append({
            "issue": f"Underexposed (mean brightness: {exposure['mean_brightness']:.0f}/255)",
            "fix": f"eq=brightness={brightness}:gamma={gamma}",
        })
    elif exposure["assessment"] == "OVEREXPOSED":
        brightness = round(-0.02 - (exposure["mean_brightness"] - 180) / 1000, 3)
        suggestions.append({
            "issue": f"Overexposed (mean brightness: {exposure['mean_brightness']:.0f}/255)",
            "fix": f"eq=brightness={brightness}:contrast=0.95",
        })

    # Skin saturation
    if skin and skin["s_mean"] < 60:
        suggestions.append({
            "issue": f"Low skin saturation ({skin['s_mean']:.0f}/255)",
            "fix": "eq=saturation=1.25",
        })
    elif skin and skin["s_mean"] > 160:
        suggestions.append({
            "issue": f"Over-saturated skin ({skin['s_mean']:.0f}/255)",
            "fix": "eq=saturation=0.85",
        })

    # Shadow clipping
    if exposure["dark_clipping_pct"] > 5:
        suggestions.append({
            "issue": f"Shadow clipping ({exposure['dark_clipping_pct']:.1f}% pure black)",
            "fix": "colorlevels=rimin=0.03:gimin=0.03:bimin=0.03",
        })

    # Highlight clipping
    if exposure["bright_clipping_pct"] > 3:
        suggestions.append({
            "issue": f"Highlight clipping ({exposure['bright_clipping_pct']:.1f}% pure white)",
            "fix": "colorlevels=romax=0.95:gomax=0.95:bomax=0.95",
        })

    return suggestions


def main():
    parser = argparse.ArgumentParser(description="Analyze video color balance and suggest FFmpeg corrections.")
    parser.add_argument("video", help="Path to the video file")
    parser.add_argument("--frames", type=int, default=5, help="Number of frames to sample (default: 5)")
    args = parser.parse_args()

    if not os.path.isfile(args.video):
        print(f"ERROR: File not found: {args.video}")
        sys.exit(1)

    print(f"\n🎨 Analyzing: {args.video}")
    print(f"   Sampling {args.frames} frames...\n")

    frames = sample_frames(args.video, args.frames)

    # Aggregate analysis across frames
    all_wb = []
    all_skin = []
    all_exposure = []

    for i, frame in enumerate(frames):
        wb = analyze_white_balance(frame)
        all_wb.append(wb)

        mask = detect_skin_mask(frame)
        skin = analyze_skin_tones(frame, mask)
        if skin:
            all_skin.append(skin)

        exp = analyze_exposure(frame)
        all_exposure.append(exp)

    # Average results
    avg_wb = {
        "r_avg": np.mean([w["r_avg"] for w in all_wb]),
        "g_avg": np.mean([w["g_avg"] for w in all_wb]),
        "b_avg": np.mean([w["b_avg"] for w in all_wb]),
        "gain_r": np.mean([w["gain_r"] for w in all_wb]),
        "gain_g": np.mean([w["gain_g"] for w in all_wb]),
        "gain_b": np.mean([w["gain_b"] for w in all_wb]),
        "dominant_cast": max(set(w["dominant_cast"] for w in all_wb), key=lambda x: sum(1 for w in all_wb if w["dominant_cast"] == x)),
    }

    avg_skin = None
    if all_skin:
        avg_skin = {
            "h_mean": np.mean([s["h_mean"] for s in all_skin]),
            "s_mean": np.mean([s["s_mean"] for s in all_skin]),
            "v_mean": np.mean([s["v_mean"] for s in all_skin]),
            "h_std": np.mean([s["h_std"] for s in all_skin]),
            "s_std": np.mean([s["s_std"] for s in all_skin]),
            "v_std": np.mean([s["v_std"] for s in all_skin]),
            "pixel_count": int(np.mean([s["pixel_count"] for s in all_skin])),
            "frame_coverage_pct": np.mean([s["frame_coverage_pct"] for s in all_skin]),
        }

    avg_exposure = {
        "mean_brightness": np.mean([e["mean_brightness"] for e in all_exposure]),
        "std_brightness": np.mean([e["std_brightness"] for e in all_exposure]),
        "dark_clipping_pct": np.mean([e["dark_clipping_pct"] for e in all_exposure]),
        "bright_clipping_pct": np.mean([e["bright_clipping_pct"] for e in all_exposure]),
        "assessment": max(set(e["assessment"] for e in all_exposure), key=lambda x: sum(1 for e in all_exposure if e["assessment"] == x)),
    }

    # Print report
    print("=" * 60)
    print("  COLOR ANALYSIS REPORT")
    print("=" * 60)

    print(f"\n📊 White Balance (averaged over {len(frames)} frames)")
    print(f"   R avg: {avg_wb['r_avg']:.1f}  G avg: {avg_wb['g_avg']:.1f}  B avg: {avg_wb['b_avg']:.1f}")
    print(f"   Gains needed → R: {avg_wb['gain_r']:.3f}  G: {avg_wb['gain_g']:.3f}  B: {avg_wb['gain_b']:.3f}")
    print(f"   Dominant cast: {avg_wb['dominant_cast']}")

    print(f"\n💡 Exposure")
    print(f"   Mean brightness: {avg_exposure['mean_brightness']:.0f}/255")
    print(f"   Contrast (std):  {avg_exposure['std_brightness']:.0f}")
    print(f"   Dark clipping:   {avg_exposure['dark_clipping_pct']:.1f}%")
    print(f"   Bright clipping: {avg_exposure['bright_clipping_pct']:.1f}%")
    print(f"   Assessment:      {avg_exposure['assessment']}")

    if avg_skin:
        print(f"\n🧑 Skin Tone Analysis")
        print(f"   Hue:        {avg_skin['h_mean']:.0f}° (std: {avg_skin['h_std']:.1f})")
        print(f"   Saturation: {avg_skin['s_mean']:.0f}/255 (std: {avg_skin['s_std']:.1f})")
        print(f"   Value:      {avg_skin['v_mean']:.0f}/255 (std: {avg_skin['v_std']:.1f})")
        print(f"   Coverage:   {avg_skin['frame_coverage_pct']:.1f}% of frame")
    else:
        print(f"\n🧑 Skin Tone: No skin detected in sampled frames")

    # Suggestions
    suggestions = suggest_corrections(avg_wb, avg_skin, avg_exposure)

    print(f"\n🔧 Suggested FFmpeg Corrections")
    if not suggestions:
        print("   ✅ Video looks well-balanced! Standard pipeline should work fine.")
        print(f"\n   Recommended command:")
        print(f"   ./color-grading/preprocess.sh {args.video}")
    else:
        for s in suggestions:
            print(f"\n   ⚠️  {s['issue']}")
            print(f"      Fix: -vf \"{s['fix']}\"")
            if "or" in s:
                print(f"      Or:  {s['or']}")

        # Build combined command
        all_fixes = ",".join(s["fix"] for s in suggestions)
        print(f"\n   Combined fix command:")
        print(f"   ffmpeg -i {args.video} -vf \"{all_fixes}\" -c:v libx264 -crf 18 -c:a copy output.mp4")

    print(f"\n   Full preprocessing pipeline:")
    print(f"   ./color-grading/preprocess.sh {args.video}")

    print()


if __name__ == "__main__":
    main()
