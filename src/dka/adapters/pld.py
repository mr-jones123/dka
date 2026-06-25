from __future__ import annotations

import csv
import re
import shutil
from pathlib import Path

import yaml

from dka.core import DEFAULT_CONFIG

LOG_ROW = re.compile(r'^(?P<wav>\S+\.wav)\s+"[^"]+"\s+"(?P<text>.*)"\s*$')
META_ROW = re.compile(r'^(?P<key>\w+)\s*=\s+"?(?P<value>.*?)"?\s*$')


def import_pld(source: Path, target: Path, limit: int | None = None) -> int:
    audio_dir = target / "raw" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []

    for log_path in sorted(source.glob("*/*.log")):
        meta = _read_meta(log_path)
        speaker_id = meta.get("SpeakerID") or log_path.parent.name
        for wav_name, text in _read_rows(log_path):
            wav_path = log_path.parent / wav_name
            if not wav_path.exists():
                continue
            sample_id = wav_path.stem
            out_name = f"{sample_id}.wav"
            shutil.copyfile(wav_path, audio_dir / out_name)
            rows.append(
                {
                    "id": sample_id,
                    "audio_path": f"raw/audio/{out_name}",
                    "text": text,
                    "language": "ceb",
                    "speaker_id": speaker_id,
                    "gender": meta.get("SpeakerGender", ""),
                    "age_group": meta.get("SpeakerAge", ""),
                    "region": meta.get("SpeakerDialect", ""),
                    "domain": "pld",
                    "license": "CC-BY-NC-4.0",
                    "source": "UP-DSP-PLD",
                }
            )
            if limit and len(rows) >= limit:
                _write_dataset(target, rows)
                return len(rows)

    _write_dataset(target, rows)
    return len(rows)


def _write_dataset(target: Path, rows: list[dict[str, str]]) -> None:
    (target / "raw").mkdir(parents=True, exist_ok=True)
    config = DEFAULT_CONFIG | {
        "name": target.name,
        "description": "Cebuano subset imported from UP-DSP-PLD",
        "language": "ceb",
    }
    (target / "dka.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False), encoding="utf-8"
    )
    with (target / "raw" / "metadata.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys())
            if rows
            else ["id", "audio_path", "text", "language"],
        )
        writer.writeheader()
        writer.writerows(rows)


def _read_meta(log_path: Path) -> dict[str, str]:
    meta = {}
    for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = META_ROW.match(line.strip())
        if match:
            meta[match.group("key")] = match.group("value")
    return meta


def _read_rows(log_path: Path) -> list[tuple[str, str]]:
    rows = []
    for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = LOG_ROW.match(line.strip())
        if match:
            rows.append((match.group("wav"), match.group("text").strip()))
    return rows
