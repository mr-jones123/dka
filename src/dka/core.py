from __future__ import annotations

import csv
import json
import random
import re
import shutil
import subprocess
import unicodedata
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG: dict[str, Any] = {
    "name": "bisaya-speech-demo",
    "description": "Speech dataset prepared with dka",
    "language": "ceb",
    "license": "CC-BY-NC-4.0",
    "input": {"metadata": "raw/metadata.csv", "audio_dir": "raw/audio"},
    "audio": {
        "sample_rate": 16000,
        "mono": True,
        "format": "wav",
        "min_duration_sec": 0.5,
        "max_duration_sec": 20,
    },
    "text": {
        "lowercase": True,
        "trim_whitespace": True,
        "remove_extra_spaces": True,
        "strip_accents": True,
        "hyphens_to_spaces": True,
    },
    "quality": {
        "flag_empty_text": True,
        "flag_long_audio": True,
        "flag_short_audio": True,
        "flag_duplicate_text": True,
    },
    "splits": {
        "strategy": "speaker",
        "train": 0.8,
        "dev": 0.1,
        "test": 0.1,
        "seed": 42,
    },
    "output": {
        "processed_dir": "processed",
        "reports_dir": "reports",
        "splits_dir": "splits",
        "dataset_card": "dataset_card.md",
    },
}

REQUIRED_COLUMNS = {"id", "audio_path", "text", "language"}
SUPPORTED_AUDIO = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}


@dataclass
class BuildResult:
    rows: list[dict[str, Any]]
    flags: dict[str, int]
    stats: dict[str, Any]


def init_project(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "raw" / "audio").mkdir(parents=True, exist_ok=True)
    (path / "raw" / "metadata.csv").write_text(
        "id,audio_path,text,language,speaker_id,domain,license\n", encoding="utf-8"
    )
    (path / "dka.yaml").write_text(
        yaml.safe_dump(DEFAULT_CONFIG, sort_keys=False), encoding="utf-8"
    )


def load_config(root: Path) -> dict[str, Any]:
    config_path = root / "dka.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"missing {config_path}")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return _merge(DEFAULT_CONFIG, config)


def read_metadata(root: Path, config: dict[str, Any]) -> list[dict[str, str]]:
    path = root / config["input"]["metadata"]
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return []
    missing = REQUIRED_COLUMNS - set(rows[0])
    if missing:
        raise ValueError(f"metadata missing columns: {', '.join(sorted(missing))}")
    return rows


def build(root: Path) -> BuildResult:
    config = load_config(root)
    rows = read_metadata(root, config)
    out_dir = root / config["output"]["processed_dir"]
    audio_out = out_dir / "audio"
    audio_out.mkdir(parents=True, exist_ok=True)

    seen_text: set[str] = set()
    processed: list[dict[str, Any]] = []
    flag_counts: dict[str, int] = {}

    for row in rows:
        items = expand_srt_row(root, config, audio_out, row)
        for item, flags in items:
            target_path = root / item["audio_path"]
            duration, sample_rate = _wav_info(target_path)
            if duration is None:
                flags.append("audio_unreadable")
                duration = 0.0
            min_d = config["audio"]["min_duration_sec"]
            max_d = config["audio"]["max_duration_sec"]
            if duration and duration < min_d:
                flags.append("short_audio")
            if duration and duration > max_d:
                flags.append("long_audio")

            normalized = normalize_text(item.get("text", ""), config)
            if not normalized:
                flags.append("empty_text")
            if normalized in seen_text:
                flags.append("duplicate_text")
            seen_text.add(normalized)

            for flag in flags:
                flag_counts[flag] = flag_counts.get(flag, 0) + 1

            item.update(
                {
                    "normalized_text": normalized,
                    "duration_sec": round(duration or 0, 3),
                    "sample_rate": sample_rate or "",
                    "quality_flags": json.dumps(flags),
                }
            )
            processed.append(item)

    write_csv(out_dir / "metadata.csv", processed)
    split_rows(root, config, processed)
    stats = write_reports(root, config, processed, flag_counts)
    write_dataset_card(root, config, stats)
    return BuildResult(processed, flag_counts, stats)


def validate(root: Path) -> tuple[list[dict[str, str]], dict[str, int]]:
    config = load_config(root)
    rows = read_metadata(root, config)
    flags: dict[str, int] = {}
    for row in rows:
        audio = root / row["audio_path"]
        if not audio.exists():
            flags["missing_audio"] = flags.get("missing_audio", 0) + 1
        elif audio.suffix.lower() not in SUPPORTED_AUDIO:
            flags["unsupported_audio_format"] = (
                flags.get("unsupported_audio_format", 0) + 1
            )
        if not row.get("text", "").strip():
            flags["empty_text"] = flags.get("empty_text", 0) + 1
    return rows, flags


def split_rows(root: Path, config: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    split_config = config["splits"]
    rng = random.Random(split_config.get("seed", 42))
    groups: dict[str, list[dict[str, Any]]] = {}
    use_speaker = split_config.get("strategy") == "speaker" and any(
        r.get("speaker_id") for r in rows
    )
    if use_speaker:
        for row in rows:
            groups.setdefault(row.get("speaker_id") or row["id"], []).append(row)
        units = list(groups.values())
        rng.shuffle(units)
        ordered = [row for group in units for row in group]
    else:
        ordered = rows[:]
        rng.shuffle(ordered)

    n = len(ordered)
    train_end = int(n * float(split_config["train"]))
    dev_end = train_end + int(n * float(split_config["dev"]))
    splits = {
        "train": ordered[:train_end],
        "dev": ordered[train_end:dev_end],
        "test": ordered[dev_end:],
    }
    split_dir = root / config["output"]["splits_dir"]
    split_dir.mkdir(parents=True, exist_ok=True)
    for name, split in splits.items():
        for row in split:
            row["split"] = name
        write_csv(split_dir / f"{name}.csv", split)


def write_reports(
    root: Path,
    config: dict[str, Any],
    rows: list[dict[str, Any]],
    flags: dict[str, int],
) -> dict[str, Any]:
    report_dir = root / config["output"]["reports_dir"]
    report_dir.mkdir(parents=True, exist_ok=True)
    total_sec = sum(float(r.get("duration_sec") or 0) for r in rows)
    stats = {
        "name": config["name"],
        "total_samples": len(rows),
        "total_hours": round(total_sec / 3600, 4),
        "languages": _counts(rows, "language"),
        "speakers": len({r.get("speaker_id") for r in rows if r.get("speaker_id")}),
        "flagged_samples": sum(
            1 for r in rows if json.loads(r.get("quality_flags", "[]"))
        ),
        "flags": flags,
    }
    (report_dir / "quality_report.json").write_text(
        json.dumps(stats, indent=2), encoding="utf-8"
    )
    md = [
        f"# {config['name']} quality report",
        "",
        f"Samples: {stats['total_samples']}",
        f"Hours: {stats['total_hours']}",
        f"Flagged samples: {stats['flagged_samples']}",
    ]
    if flags:
        md += ["", "## Flags"] + [f"- {k}: {v}" for k, v in sorted(flags.items())]
    (report_dir / "quality_report.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8"
    )
    return stats


def write_dataset_card(
    root: Path, config: dict[str, Any], stats: dict[str, Any]
) -> None:
    text = f"""# {config["name"]}

{config.get("description", "")}

## Language

{config.get("language")}

## License

{config.get("license")}

## Dataset stats

- Samples: {stats["total_samples"]}
- Hours: {stats["total_hours"]}
- Speakers: {stats["speakers"]}
- Flagged samples: {stats["flagged_samples"]}

## Prototype note

Prepared with dka. Verify consent, license, and speaker metadata before publishing.
"""
    (root / config["output"]["dataset_card"]).write_text(text, encoding="utf-8")


def expand_srt_row(
    root: Path, config: dict[str, Any], audio_out: Path, row: dict[str, str]
) -> list[tuple[dict[str, Any], list[str]]]:
    transcript = row.get("transcript_path")
    if transcript and transcript.endswith(".srt"):
        segments = parse_srt(root / transcript)
        items = []
        for index, start, end, text in segments:
            item = dict(row)
            item["id"] = f"{row['id']}_{index:04d}"
            item["text"] = text
            target = audio_out / f"{item['id']}.wav"
            flags = []
            if not cut_audio(
                root / row["audio_path"],
                target,
                start,
                end,
                int(config["audio"]["sample_rate"]),
            ):
                flags.append("audio_segment_failed")
            item["audio_path"] = (
                str(target.relative_to(root)) if target.exists() else row["audio_path"]
            )
            items.append((item, flags))
        return items

    item = dict(row)
    flags: list[str] = []
    audio_path = root / item["audio_path"]
    target = audio_out / f"{item['id']}.wav"
    if audio_path.exists() and audio_path.suffix.lower() in SUPPORTED_AUDIO:
        if not convert_audio(audio_path, target, int(config["audio"]["sample_rate"])):
            flags.append("audio_convert_failed")
    elif audio_path.exists():
        flags.append("unsupported_audio_format")
    item["audio_path"] = (
        str(target.relative_to(root)) if target.exists() else item["audio_path"]
    )
    return [(item, flags)]


def parse_srt(path: Path) -> list[tuple[int, float, float, str]]:
    blocks = re.split(r"\n\s*\n", path.read_text(encoding="utf-8").strip())
    segments = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        start_raw, end_raw = [part.strip() for part in lines[1].split("-->", 1)]
        text = " ".join(lines[2:])
        segments.append((int(lines[0]), srt_time(start_raw), srt_time(end_raw), text))
    return segments


def srt_time(value: str) -> float:
    hours, minutes, rest = value.replace(",", ".").split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(rest)


def cut_audio(
    source: Path, target: Path, start: float, end: float, sample_rate: int
) -> bool:
    if not shutil.which("ffmpeg") or not source.exists():
        return False
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-ss",
        str(start),
        "-to",
        str(end),
        "-i",
        str(source),
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        str(target),
    ]
    return subprocess.run(cmd, check=False).returncode == 0


def convert_audio(source: Path, target: Path, sample_rate: int) -> bool:
    if source.suffix.lower() == ".wav":
        duration, rate = _wav_info(source)
        if duration is not None and rate == sample_rate:
            shutil.copyfile(source, target)
            return True
    if not shutil.which("ffmpeg"):
        return False
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        str(target),
    ]
    return subprocess.run(cmd, check=False).returncode == 0


def normalize_text(text: str, config: dict[str, Any]) -> str:
    out = text.strip() if config["text"].get("trim_whitespace") else text
    if config["text"].get("strip_accents"):
        out = "".join(
            char
            for char in unicodedata.normalize("NFKD", out)
            if not unicodedata.combining(char)
        )
    if config["text"].get("hyphens_to_spaces"):
        out = re.sub(r"[-‐‑‒–—]+", " ", out)
    if config["text"].get("lowercase"):
        out = out.lower()
    if config["text"].get("remove_extra_spaces"):
        out = re.sub(r"\s+", " ", out)
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _wav_info(path: Path) -> tuple[float | None, int | None]:
    if not path.exists() or path.suffix.lower() != ".wav":
        return None, None
    try:
        with wave.open(str(path), "rb") as audio:
            frames = audio.getnframes()
            rate = audio.getframerate()
            return frames / float(rate), rate
    except wave.Error:
        return None, None


def _counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(key) or "unknown"
        counts[value] = counts.get(value, 0) + 1
    return counts


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged
