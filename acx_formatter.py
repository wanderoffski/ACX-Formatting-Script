#!/usr/bin/env python3
"""
ACX audiobook helper: batch-process raw chapter audio into ACX-compliant MP3s.

Depends on ffmpeg + ffprobe being installed and discoverable on PATH.
"""

from __future__ import annotations

import argparse
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Sequence


DEFAULT_BITRATE = "256k"  # CBR
DEFAULT_ROOM_TONE = 2.0  # seconds (between 1 and 5)
DEFAULT_MAX_MINUTES = 120
DEFAULT_OVERLAP = 1.0  # seconds of continuity overlap at split points
SUPPORTED_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".aiff", ".aif"}


def run(cmd: Sequence[str], *, quiet: bool = False) -> None:
    """Run a command, raising on error."""
    if not quiet:
        print(" ".join(cmd))
    subprocess.run(cmd, check=True)


def which_or_die(binary: str) -> None:
    if shutil.which(binary) is None:
        sys.exit(f"Missing required tool: {binary}. Install ffmpeg + ffprobe and retry.")


def ffprobe_duration(path: Path) -> float:
    """Return duration in seconds."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
        text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(f"Could not parse duration for {path}") from exc


def safe_slug(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", Path(name).stem)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "Section"


def detect_opening(files: List[Path]) -> Optional[Path]:
    for f in files:
        if re.search(r"(opening|intro)", f.name, re.IGNORECASE):
            return f
    return None


def detect_closing(files: List[Path]) -> Optional[Path]:
    for f in files:
        if re.search(r"(closing|outro|credits)", f.name, re.IGNORECASE):
            return f
    return None


def gather_inputs(input_dir: Path) -> List[Path]:
    files = [p for p in sorted(input_dir.iterdir()) if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS]
    if not files:
        sys.exit("No audio files found in input directory.")
    return files


def build_filter_chain() -> str:
    # Mild cleaning + loudness conditioning to hit ACX RMS/peak guidance.
    filters = [
        "highpass=f=80",
        "lowpass=f=12000",
        "adeclick",
        "afftdn=nf=-35",
        "acompressor=threshold=-18dB:ratio=2:attack=5:release=250",
        "loudnorm=I=-20:LRA=11:TP=-3.0",
        "alimiter=limit=0.7",  # approx -3 dB ceiling (linear scale in ffmpeg 7.x)
        "silenceremove=start_periods=1:start_threshold=-50dB:start_duration=0:stop_periods=-1:stop_threshold=-50dB:stop_duration=0",
    ]
    return ",".join(filters)


def add_room_tone(source: Path, dest: Path, channels: int, tone_seconds: float) -> None:
    # Add tone_seconds at head + tail (kept under 5s by validation at parse time).
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-t",
            f"{tone_seconds}",
            "-i",
            f"anullsrc=r=44100:cl={'mono' if channels == 1 else 'stereo'}",
            "-i",
            str(source),
            "-filter_complex",
            f"[0:a][1:a]concat=n=2:v=0:a=1,apad=pad_dur={tone_seconds}",
            "-c:a",
            "pcm_s16le",
            str(dest),
        ],
        quiet=True,
    )


def encode_mp3(src: Path, dest: Path, channels: int, bitrate: str) -> None:
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-ar",
            "44100",
            "-ac",
            str(channels),
            "-c:a",
            "libmp3lame",
            "-b:a",
            bitrate,
            "-compression_level",
            "0",
            "-write_xing",
            "0",
            "-id3v2_version",
            "3",
            "-map_metadata",
            "0",
            str(dest),
        ],
        quiet=True,
    )


def process_file(
    src: Path,
    *,
    title: str,
    index: int,
    out_dir: Path,
    channels: int,
    bitrate: str,
    max_seconds: float,
    overlap: float,
    room_tone: float,
    pad_width: int,
) -> List[Path]:
    outputs: List[Path] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        cleaned = tmpdir_path / "clean.wav"
        padded = tmpdir_path / "padded.wav"

        # Clean, denoise, normalize, and set format.
        run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(src),
                "-ac",
                str(channels),
                "-ar",
                "44100",
                "-af",
                build_filter_chain(),
                "-c:a",
                "pcm_s16le",
                str(cleaned),
            ],
            quiet=True,
        )

        add_room_tone(cleaned, padded, channels, room_tone)

        duration = ffprobe_duration(padded)
        step = max_seconds - overlap
        parts = int(math.ceil(max(duration - overlap, 0) / step))

        for part_idx in range(parts):
            start = part_idx * step
            remaining = duration - start
            part_length = min(max_seconds, remaining)
            part_suffix = ""
            numbered_index = index + len(outputs)
            if parts > 1:
                part_suffix = f"_Part{part_idx + 1:02d}"
            dest_name = f"{numbered_index:0{pad_width}d}_{title}{part_suffix}.mp3"
            dest_path = out_dir / dest_name

            run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    f"{start}",
                    "-t",
                    f"{part_length}",
                    "-i",
                    str(padded),
                    "-ac",
                    str(channels),
                    "-ar",
                    "44100",
                    "-c:a",
                    "libmp3lame",
                    "-b:a",
                    bitrate,
                    "-compression_level",
                    "0",
                    "-write_xing",
                    "0",
                    "-id3v2_version",
                    "3",
                    "-map_metadata",
                    "0",
                    str(dest_path),
                ],
                quiet=True,
            )
            outputs.append(dest_path)
    return outputs


def create_sample(first_output: Path, out_dir: Path, channels: int, bitrate: str, room_tone: float) -> Path:
    sample_path = out_dir / "Retail_Sample.mp3"
    run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{room_tone}",
            "-t",
            "300",
            "-i",
            str(first_output),
            "-ac",
            str(channels),
            "-ar",
            "44100",
            "-c:a",
            "libmp3lame",
            "-b:a",
            bitrate,
            "-compression_level",
            "0",
            "-write_xing",
            "0",
            "-id3v2_version",
            "3",
            "-map_metadata",
            "0",
            str(sample_path),
        ],
        quiet=True,
    )
    return sample_path


def compute_pad_width(num_items: int) -> int:
    return max(2, len(str(num_items + 2)))  # pad generously so late splits stay aligned


def main() -> None:
    parser = argparse.ArgumentParser(description="ACX batch formatter (ffmpeg-based).")
    parser.add_argument("--input-dir", required=True, type=Path, help="Directory with raw chapter/credits audio.")
    parser.add_argument("--output-dir", default=Path("output"), type=Path, help="Destination for processed MP3s.")
    parser.add_argument("--channels", choices=["mono", "stereo"], default="mono", help="Uniform channel layout.")
    parser.add_argument("--bitrate", default=DEFAULT_BITRATE, help="MP3 CBR bitrate (e.g. 192k, 256k, 320k).")
    parser.add_argument(
        "--room-tone",
        type=float,
        default=DEFAULT_ROOM_TONE,
        help="Seconds of clean tone to add to head + tail (1-5).",
    )
    parser.add_argument(
        "--max-minutes",
        type=float,
        default=DEFAULT_MAX_MINUTES,
        help="Max length for a single file before splitting (minutes).",
    )
    parser.add_argument(
        "--overlap",
        type=float,
        default=DEFAULT_OVERLAP,
        help="Seconds of overlap to keep at split boundaries for continuity.",
    )
    parser.add_argument("--opening", type=Path, help="Explicit path for opening credits.")
    parser.add_argument("--closing", type=Path, help="Explicit path for closing credits.")
    args = parser.parse_args()

    if not (1 <= args.room_tone <= 5):
        sys.exit("room-tone must be between 1 and 5 seconds.")
    if args.max_minutes <= 0:
        sys.exit("max-minutes must be positive.")
    channels = 1 if args.channels == "mono" else 2

    which_or_die("ffmpeg")
    which_or_die("ffprobe")

    input_dir: Path = args.input_dir
    out_dir: Path = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    files = gather_inputs(input_dir)

    opening = args.opening or detect_opening(files)
    closing = args.closing or detect_closing(files)

    chapters = [f for f in files if f not in {opening, closing}]

    ordered: List[tuple[str, Path]] = []
    if opening:
        ordered.append(("Opening_Credits", opening))
    ordered.extend([(safe_slug(ch.name), ch) for ch in chapters])
    if closing:
        ordered.append(("Closing_Credits", closing))

    pad_width = compute_pad_width(len(ordered))

    index = 1
    first_output: Optional[Path] = None
    produced: List[Path] = []
    for title, src in ordered:
        outs = process_file(
            src,
            title=safe_slug(title),
            index=index,
            out_dir=out_dir,
            channels=channels,
            bitrate=args.bitrate,
            max_seconds=args.max_minutes * 60,
            overlap=args.overlap,
            room_tone=args.room_tone,
            pad_width=pad_width,
        )
        if not first_output and outs:
            first_output = outs[0]
        index += len(outs)
        produced.extend(outs)

    sample_path: Optional[Path] = None
    if first_output:
        sample_path = create_sample(first_output, out_dir, channels, args.bitrate, args.room_tone)

    print("\nDone.")
    print(f"Created {len(produced)} section file(s) in {out_dir}")
    for p in produced:
        print(f" - {p}")
    if sample_path:
        print(f"Retail sample: {sample_path}")


if __name__ == "__main__":
    main()
