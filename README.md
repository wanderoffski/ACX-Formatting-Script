# ACX Audiobook Batch Mastering Script

This project provides a batch-processing script that converts a folder of raw audiobook recordings into **ACX-compliant MP3 files** with minimal manual work.

It’s ideal if you record/edit in tools like **Audacity** but don’t want to hand-tweak every single file to meet ACX technical standards.

---

## Features

Given a folder of chapter/section recordings, the script will:

- 📂 **Treat each file as one chapter/section**
- 🎧 **Create separate files** for:
  - Opening Credits  
  - Closing Credits
- 📏 **Normalize loudness** to ACX specs:
  - RMS between **−23 dB and −18 dB**
  - Peak level **≤ −3 dB**
- 🔇 Enforce a **noise floor ≤ −60 dB RMS**
- 🤫 Manage **room tone**:
  - 1–5 seconds at the start of each file
  - 1–5 seconds at the end of each file
  - Trim any head/tail silence > 5 seconds
- 🔁 **Split long files**:
  - Any file > **120 minutes** is automatically split into multiple parts
- 🔊 Use a **consistent channel format**:
  - All mono *or* all stereo (configurable, but consistent across the project)
- 💾 Export all audio as:
  - **MP3**, **CBR**
  - **192 kbps or higher**
  - **44.1 kHz** sample rate

The script also generates a **retail sample** file by taking up to the first **5 minutes** of the audiobook’s beginning and processing it with the same standards.

> ⚠️ **Note:** This tool focuses on the *technical* side (levels, noise, encoding, structure).  
> You are still responsible for content-related requirements like human narration and proper credits.

---

## ACX Requirements Implemented

### 1. File Structure & Naming

The script enforces a clean, ACX-friendly file layout:

- **One chapter/section per file**
- **Separate files** for:
  - `00_Opening_Credits.mp3`
  - `99_Closing_Credits.mp3` (or similarly named)
- **Simple filenames** using only:
  - Letters (`A–Z`, `a–z`)
  - Numbers (`0–9`)
  - Underscores (`_`)
- Example naming scheme:
  - `00_Opening_Credits.mp3`
  - `01_Prologue.mp3`
  - `02_Chapter_01.mp3`
  - `03_Chapter_02.mp3`
- **Auto-splitting long chapters**:
  - Any file longer than **120 minutes** is split into:
    - `05_Chapter_03_Part1.mp3`
    - `06_Chapter_03_Part2.mp3`
    - etc.

---

### 2. Audio Consistency & Quality

To match ACX’s technical standards, the script:

- 🔊 Sets all files to the **same channel format**:
  - Either all mono **or** all stereo
- 📉 Normalizes **RMS loudness** to:
  - Between **−23 dB** and **−18 dB**
- 🚫 Limits **peak level** to:
  - **≤ −3 dB** (prevents clipping/distortion)
- 🔕 Keeps **noise floor**:
  - At or below **−60 dB RMS**
- 😌 Handles **room tone**:
  - Ensures **1–5 seconds** of clean room tone at the start and end
  - Trims excess silence beyond 5 seconds
- 🧼 Optionally applies basic cleanup:
  - Light de-click/de-pop or noise reduction, where configured

---

### 3. Encoding & Export Settings

All final files are exported as:

- **Format:** MP3
- **Bitrate:** Constant Bit Rate (**CBR**), **192 kbps or higher**
- **Sample rate:** **44.1 kHz**

This matches ACX’s requirement for consistent encoding so they can re-encode for distribution without errors.

---

### 4. Retail Sample Generation

The script can automatically create an ACX-ready **retail sample**:

- Takes up to the **first 5 minutes** of the audiobook’s beginning
- Applies the **same processing**:
  - RMS, peak, noise floor, room tone, encoding
- Outputs a separate MP3 ready to upload as the **retail sample**

> 📝 Content note: If the opening of your book is explicit or not suitable as a sample, you should manually choose a different clean section. The script only automates cutting and processing.

---

## What You Still Do Manually

This script **does not** replace the creative and legal parts of audiobook production. You are still responsible for:

- 🎙️ Recording **human narration**  
  (ACX does not allow unauthorized AI/TTS voices)
- 🗣️ Writing and recording **opening credits**:
  - Must include: **title, author(s), narrator(s)**
- 🗣️ Writing and recording **closing credits**:
  - Should clearly indicate finality, e.g.:  
    > “You have been listening to *[Title]* by *[Author]*, narrated by *[Narrator]*. The End.”
- ✅ Ensuring your selected **retail sample**:
  - Is **≤ 5 minutes**
  - Contains **no explicit content** (no graphic violence, no pornography)

Once your raw files are recorded and roughly edited, you point this script at your input folder — it handles the repetitive **technical compliance** work across the entire audiobook in one pass.



=========================================================================================================
ACX Formatting Script
=========================================================================================================

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
