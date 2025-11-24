ACX Formatting Script
=====================

Python + ffmpeg helper to batch-process raw audiobook chapter files into ACX-compliant MP3s (RMS/peak conditioned, cleaned, padded with room tone, encoded CBR) and generate a 5-minute retail sample.

Requirements
------------
- Python 3.8+
- `ffmpeg` and `ffprobe` available on `PATH`

Usage
-----
1) Put your raw audio (WAV/MP3/FLAC/M4A/AAC/AIFF) in a folder, including opening/closing credits.
2) From this directory, run:

```bash
python acx_formatter.py \
  --input-dir "/path/to/raw" \
  --output-dir "./output" \
  --channels mono \
  --bitrate 256k \
  --room-tone 2 \
  --max-minutes 120 \
  --overlap 1

Or on one line (to avoid shell newline issues):

```bash
python acx_formatter.py --input-dir "/path/to/raw" --output-dir "./output" --channels mono --bitrate 256k --room-tone 2 --max-minutes 120 --overlap 1
```

Key behaviors
-------------
- One output MP3 per section/chapter; optional splitting at 120 minutes with a 1s overlap and `_Part01` suffix.
- Opening/closing credits auto-detected by filename (`opening`/`intro`, `closing`/`outro`/`credits`) or provided via `--opening/--closing`.
- Uniform format: 44.1 kHz, mono (or stereo if chosen), CBR (≥192 kbps as configured).
- Processing chain: light de-click/denoise, high/low-pass, compression, loudness normalization toward -20 LUFS, limiter at -3 dB, silence trimmed then 1–5s of clean room tone added at head/tail (configurable).
- Filenames constrained to letters/numbers/underscores with sequential numbering (`01_Title.mp3`). Retail sample saved as `Retail_Sample.mp3` using the first processed section (after room tone) capped at 5:00.

Notes
-----
- The script copies input metadata tags into the outputs when present.
- If you prefer stereo, set `--channels stereo`.
- The noise reduction and loudness steps are conservative to avoid artifacts; you can tweak the filter chain in `build_filter_chain()` if needed.
