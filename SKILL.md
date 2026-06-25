---
name: dka
summary: Use dka to prepare Philippine speech datasets for ASR/TTS research.
---

# dka Skill

Use `dka` when a researcher has speech audio and transcripts and needs a model-ready dataset package.

## What dka does

`dka` standardizes a dataset folder, converts supported audio to mono 16kHz WAV with ffmpeg, validates audio/transcript rows, normalizes transcript text, creates train/dev/test splits, writes quality reports, and generates a dataset card.

It does not collect speech, train a model, or claim generated samples are real recordings.

## Expected input

```text
dataset/
  dka.yaml
  raw/
    audio/*.{wav,mp3,m4a,flac,ogg}
    metadata.csv
```

Minimum metadata columns:

```csv
id,audio_path,text,language
```

Prefer adding:

```csv
speaker_id,domain,license,region,source
```

## Commands

Create a dataset folder:

```bash
uv run dka init path/to/dataset
```

Validate raw files:

```bash
uv run dka validate path/to/dataset
```

Build processed outputs from an existing dka dataset:

```bash
uv run dka build path/to/dataset
```

Build directly from UP-DSP-PLD and export Hugging Face CSVs:

```bash
uv run dka build path/to/PLD/CEB --preset pld --out datasets/pld-ceb-small --limit 500 --hf
```

Export Hugging Face CSVs for Whisper-style ASR training:

```bash
uv run dka export path/to/dataset --format hf
```

## Agent workflow

1. Inspect `dka.yaml` and `raw/metadata.csv`.
2. Run `uv run dka validate DATASET`.
3. Fix missing files or required columns.
4. Run `uv run dka build DATASET`.
5. Read `reports/quality_report.md`.
6. Tell the user the sample count, total hours, flags, and generated files.

## Safety

- Do not publish datasets unless consent and license are clear.
- Do not remove flagged samples silently. Report them.
- Do not claim a dataset is representative without speaker/domain stats.
- Keep generated/synthetic audio labeled separately from real speech.
