# Color Grading Pipeline

This directory contains everything for automatic video preprocessing before editing.

## Directory layout

```
color-grading/
├── README.md            ← this file
├── preprocess.sh        ← main preprocessing script
├── analyze-color.py     ← Python auto-white-balance analyzer
├── luts/                ← .cube LUT files
│   ├── clean-neutral.cube
│   └── soft.cube
└── presets/             ← named FFmpeg filter chains
    └── standard.txt
```

## Quick start

```bash
# Default preset: gentle grade, no auto white balance, downscale to <=1080p
./color-grading/preprocess.sh --preset standard footage/take01.mov

# Preprocess a single clip (auto white balance + denoise + LUT + sharpen)
./color-grading/preprocess.sh footage/take01.mov

# Preprocess all clips in a video folder
./color-grading/preprocess.sh footage/

# Use a specific LUT
./color-grading/preprocess.sh --lut color-grading/luts/clean-neutral.cube take01.mov

# Skip LUT, only auto-correct and denoise
./color-grading/preprocess.sh --no-lut take01.mov

# Analyze a clip's color balance (requires Python + OpenCV)
python3 color-grading/analyze-color.py footage/take01.mov
```

## What the preprocessing does

The pipeline runs **five steps** in order:

| Step | FFmpeg Filter | Purpose |
|------|--------------|---------|
| 1. Auto white balance | `grayworld` | Neutralizes color casts from mixed lighting |
| 2. Denoise | `hqdn3d` | Removes phone sensor noise |
| 3. Exposure + color | `eq` + `colorbalance` | Lifts shadows, boosts skin saturation |
| 4. Cinematic LUT | `lut3d` | Applies a `.cube` look-up table at 60% intensity |
| 5. Sharpen | `unsharp` | Recovers detail from soft phone footage |

## Generated LUTs

`python3 color-grading/make-luts.py` writes `soft.cube`, `clean-neutral.cube` and `moody-teal-orange.cube` (no downloads).

## Adding custom LUTs

1. Download `.cube` files from:
   - [Luttie](https://luttie.app) — free cinematic + vlogging packs
   - [FilterGrade](https://filtergrade.com) — curated 8-packs
   - [Editor Hub](https://editor-hub.com) — 50 free LUTs with preview
2. Drop the `.cube` file into `color-grading/luts/`
3. Set it as default in `preprocess.sh` (`DEFAULT_LUT=`) or pass via `--lut`

## LUT intensity

For talking head videos, LUTs are blended at **60% intensity** by default to preserve natural skin tones. Change this with `--lut-intensity 0.7` (range 0.0–1.0).

## Requirements

- **FFmpeg**
- **Python 3 + OpenCV** (optional, for `analyze-color.py`)
  ```bash
  pip install opencv-python numpy
  ```
