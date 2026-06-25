from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from dka.core import write_csv


def export_hf(root: Path) -> Path:
    out = root / "exports" / "hf"
    out.mkdir(parents=True, exist_ok=True)

    for split in ["train", "dev", "test"]:
        split_path = root / "splits" / f"{split}.csv"
        rows = _read_csv(split_path)
        exported = [_to_hf_row(root, row) for row in rows]
        write_csv(out / f"{split}.csv", exported)

    return out


def _to_hf_row(root: Path, row: dict[str, str]) -> dict[str, Any]:
    return {
        "audio": str((root / row["audio_path"]).resolve()),
        "sentence": row.get("normalized_text") or row.get("text", ""),
        "language": row.get("language", ""),
        "speaker_id": row.get("speaker_id", ""),
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
