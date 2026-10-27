#!/usr/bin/env bash
# =============================================================================
# preprocess.sh — Video preprocessing pipeline for the video toolkit
#
# Auto white balance → Denoise → Color correct → Cinematic LUT → Sharpen
#
# Usage:
#   ./color-grading/preprocess.sh [options] <file_or_directory>
#
# Options:
#   --lut <path.cube>       Use a specific .cube LUT file
#   --lut-intensity <0-1>   LUT blend intensity (default: 0.6)
#   --no-lut                Skip LUT application
#   --no-denoise            Skip denoising
#   --no-sharpen            Skip sharpening
#   --no-awb                Skip auto white balance
#   --preset <name>         Use a named preset from presets/ (ignores other flags)
#   --suffix <text>         Output file suffix (default: _graded)
#   --outdir <path>         Output directory (default: next to source)
#   --dry-run               Show the FFmpeg command without running it
#   -h, --help              Show this help
#
# Examples:
#   ./color-grading/preprocess.sh take01.mov
#   ./color-grading/preprocess.sh --lut luts/clean-neutral.cube footage/
#   ./color-grading/preprocess.sh --no-lut --no-sharpen take01.mov
#   ./color-grading/preprocess.sh --preset standard take01.mov
# =============================================================================

set -euo pipefail

# ─── Defaults ────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DEFAULT_LUT="$SCRIPT_DIR/luts/soft.cube"
LUT_INTENSITY=0.6
SUFFIX="_graded"
OUTDIR=""
DRY_RUN=false

# Feature toggles
DO_AWB=true
DO_DENOISE=true
DO_LUT=true
DO_SHARPEN=true
USE_PRESET="standard"   # default: gentle grade, no auto white balance

# ─── FFmpeg tuning parameters ────────────────────────────────────────────────

AWB_FILTER="grayworld,format=yuv420p"

# Denoising: hqdn3d — spatial:spatial_chroma:temporal:temporal_chroma
DENOISE_FILTER="hqdn3d=4:3:6:4.5"

# Exposure + Color
# brightness: slight lift for indoor scenes
# contrast: adds depth
# saturation: enriches skin tones
# gamma: brightens midtones (face exposure)
EQ_FILTER="eq=brightness=0.02:contrast=1.10:saturation=1.15:gamma=0.95"

# Sharpening: unsharp — luma_x:luma_y:luma_amount:chroma_x:chroma_y:chroma_amount
SHARPEN_FILTER="unsharp=5:5:0.8:5:5:0.0"

# Encoding
ENCODER="libx264"
CRF=18
PRESET="slow"
PIX_FMT="yuv420p"

# ─── Functions ───────────────────────────────────────────────────────────────

usage() {
    sed -n '/^# Usage:/,/^# =====/p' "$0" | sed 's/^# //' | sed 's/^#//' | head -n -1
    exit 0
}

log() {
    echo "  [preprocess] $*"
}

error() {
    echo "  [preprocess] ERROR: $*" >&2
    exit 1
}

check_deps() {
    if ! command -v ffmpeg &>/dev/null; then
        error "ffmpeg not found. Install with: brew install ffmpeg"
    fi
}

build_filter_chain() {
    local lut_file="$1"
    local filters=()

    # Step 1: Auto White Balance
    if $DO_AWB; then
        filters+=("$AWB_FILTER")
    fi

    # Step 2: Denoise
    if $DO_DENOISE; then
        filters+=("$DENOISE_FILTER")
    fi

    # Step 3: Exposure + Color correction (always applied)
    filters+=("$EQ_FILTER")

    # Step 4: Cinematic LUT (blended at specified intensity)
    if $DO_LUT && [[ -f "$lut_file" ]]; then
        if (( $(echo "$LUT_INTENSITY >= 1.0" | bc -l) )); then
            # Full intensity — simple lut3d
            filters+=("lut3d=$lut_file")
        else
            # Blended — split, apply LUT, blend back
            # We need to build this as a complex filtergraph instead
            :  # handled below
        fi
    fi

    # Step 5: Sharpen
    if $DO_SHARPEN; then
        filters+=("$SHARPEN_FILTER")
    fi

    # Join filters
    local IFS=','
    echo "${filters[*]}"
}

process_file() {
    local input="$1"
    local filename
    filename="$(basename "$input")"
    local name="${filename%.*}"
    local ext="${filename##*.}"

    # Determine output path
    local output
    if [[ -n "$OUTDIR" ]]; then
        mkdir -p "$OUTDIR"
        output="$OUTDIR/${name}${SUFFIX}.mp4"
    else
        output="$(dirname "$input")/${name}${SUFFIX}.mp4"
    fi

    # Skip if already processed
    if [[ -f "$output" ]]; then
        log "Skipping (already exists): $output"
        return
    fi

    log "Processing: $input"

    # Determine LUT file
    local lut_file="$DEFAULT_LUT"

    # If using a preset, just use the preset filter chain
    if [[ -n "$USE_PRESET" ]]; then
        local preset_file="$SCRIPT_DIR/presets/${USE_PRESET}.txt"
        if [[ ! -f "$preset_file" ]]; then
            error "Preset not found: $preset_file"
        fi
        local preset_chain
        preset_chain="$(grep -v '^#' "$preset_file" | grep -v '^$' | tr -d '\n')"

        local cmd=(ffmpeg -i "$input" -vf "$preset_chain" -c:v "$ENCODER" -preset "$PRESET" -crf "$CRF" -pix_fmt "$PIX_FMT" -c:a copy -y "$output")
        if $DRY_RUN; then
            log "DRY RUN: ${cmd[*]}"
            return
        fi
        "${cmd[@]}"
        log "Done → $output"
        return
    fi

    # Build the filter chain
    if $DO_LUT && [[ -f "$lut_file" ]] && (( $(echo "$LUT_INTENSITY < 1.0" | bc -l) )); then
        # Complex filtergraph for blended LUT
        local pre_filters=()
        local post_filters=()

        if $DO_AWB; then pre_filters+=("$AWB_FILTER"); fi
        if $DO_DENOISE; then pre_filters+=("$DENOISE_FILTER"); fi
        pre_filters+=("$EQ_FILTER")

        if $DO_SHARPEN; then post_filters+=("$SHARPEN_FILTER"); fi

        local pre_chain=""
        if [[ ${#pre_filters[@]} -gt 0 ]]; then
            local IFS=','
            pre_chain="${pre_filters[*]},"
        fi

        local post_chain=""
        if [[ ${#post_filters[@]} -gt 0 ]]; then
            local IFS=','
            post_chain=",${post_filters[*]}"
        fi

        local complex_filter="${pre_chain}split[a][b];[b]lut3d=$lut_file[c];[a][c]blend=all_opacity=$LUT_INTENSITY${post_chain}"

        local cmd=(ffmpeg -i "$input" -filter_complex "$complex_filter" -c:v "$ENCODER" -preset "$PRESET" -crf "$CRF" -pix_fmt "$PIX_FMT" -c:a copy -y "$output")
        if $DRY_RUN; then
            log "DRY RUN: ${cmd[*]}"
            return
        fi
        "${cmd[@]}"
    else
        # Simple filtergraph
        local filter_chain
        filter_chain="$(build_filter_chain "$lut_file")"

        local cmd=(ffmpeg -i "$input" -vf "$filter_chain" -c:v "$ENCODER" -preset "$PRESET" -crf "$CRF" -pix_fmt "$PIX_FMT" -c:a copy -y "$output")
        if $DRY_RUN; then
            log "DRY RUN: ${cmd[*]}"
            return
        fi
        "${cmd[@]}"
    fi

    log "Done → $output"
}

# ─── Argument parsing ────────────────────────────────────────────────────────

POSITIONAL=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --lut)
            DEFAULT_LUT="$2"
            shift 2
            ;;
        --lut-intensity)
            LUT_INTENSITY="$2"
            shift 2
            ;;
        --no-lut)
            DO_LUT=false
            shift
            ;;
        --no-denoise)
            DO_DENOISE=false
            shift
            ;;
        --no-sharpen)
            DO_SHARPEN=false
            shift
            ;;
        --no-awb)
            DO_AWB=false
            shift
            ;;
        --preset)
            USE_PRESET="$2"
            shift 2
            ;;
        --suffix)
            SUFFIX="$2"
            shift 2
            ;;
        --outdir)
            OUTDIR="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        -*)
            error "Unknown option: $1"
            ;;
        *)
            POSITIONAL+=("$1")
            shift
            ;;
    esac
done

set -- "${POSITIONAL[@]}"

if [[ $# -eq 0 ]]; then
    echo "Usage: $0 [options] <file_or_directory>"
    echo "Run $0 --help for details."
    exit 1
fi

# ─── Main ────────────────────────────────────────────────────────────────────

check_deps

TARGET="$1"

if [[ -d "$TARGET" ]]; then
    # Process all video files in directory
    log "Processing directory: $TARGET"
    count=0
    while IFS= read -r -d '' file; do
        process_file "$file"
        ((count++))
    done < <(find "$TARGET" -maxdepth 1 -type f \( -iname "*.mov" -o -iname "*.mp4" -o -iname "*.mkv" -o -iname "*.avi" -o -iname "*.webm" \) -print0 | sort -z)

    if [[ $count -eq 0 ]]; then
        log "No video files found in $TARGET"
    else
        log "Processed $count file(s)"
    fi
elif [[ -f "$TARGET" ]]; then
    process_file "$TARGET"
else
    error "Not found: $TARGET"
fi
