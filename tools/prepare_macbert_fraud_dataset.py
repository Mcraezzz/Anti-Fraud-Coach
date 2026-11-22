from __future__ import annotations

import argparse
import json
import random
import re
import zipfile
from collections import Counter
from pathlib import Path
from typing import Iterable

import pandas as pd


LABELS = {"normal": 0, "fraud": 1}
DEFAULT_RESOURCE_ROOT = Path(r"D:\CARIC模型&数据集")
REASON_RE = re.compile(r'"reason"\s*:\s*"([^"]+)"')


def clean_text(value: object, max_chars: int = 512) -> str:
    text = str(value or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def iter_chifraud(resource_root: Path, max_per_label: int) -> Iterable[dict[str, object]]:
    dataset_dir = resource_root / "datasets" / "ChiFraud" / "dataset"
    files = ["ChiFraud_train.csv", "ChiFraud_t2022.csv", "ChiFraud_t2023.csv"]
    counts: Counter[str] = Counter()

    for filename in files:
        path = dataset_dir / filename
        if not path.exists():
            continue
        chunks = pd.read_csv(
            path,
            sep="\t",
            encoding="utf-8",
            header=None,
            names=["label", "text"],
            chunksize=5000,
            on_bad_lines="skip",
        )
        for chunk in chunks:
            for row in chunk.itertuples(index=False):
                try:
                    original_label = int(row.label)
                except (TypeError, ValueError):
                    continue
                label = "normal" if original_label == 0 else "fraud"
                if counts[label] >= max_per_label:
                    continue
                text = clean_text(row.text)
                if len(text) < 8:
                    continue
                counts[label] += 1
                yield {
                    "text": text,
                    "label": label,
                    "label_id": LABELS[label],
                    "source": f"ChiFraud/{filename}",
                    "original_label": original_label,
                }
            if all(counts[label] >= max_per_label for label in LABELS):
                return


def _extract_reason(content: str) -> str:
    match = REASON_RE.search(content)
    if match:
        return clean_text(match.group(1))
    content = re.sub(r"```(?:json)?|</?think>|</?answer>|<audio>", " ", content)
    return clean_text(content)


def iter_teleantifraud(resource_root: Path, max_per_label: int) -> Iterable[dict[str, object]]:
    zip_path = resource_root / "datasets" / "JimmyMa99_TeleAntiFraud" / "sft.zip"
    if not zip_path.exists():
        return

    counts: Counter[str] = Counter()
    with zipfile.ZipFile(zip_path) as archive:
        with archive.open("sft/train.jsonl") as handle:
            for raw_line in handle:
                item = json.loads(raw_line.decode("utf-8"))
                answer = str(item.get("answers", "")).lower()
                if answer not in LABELS:
                    continue
                if counts[answer] >= max_per_label:
                    continue
                assistant_texts = [
                    msg.get("content", "")
                    for msg in item.get("messages", [])
                    if msg.get("role") == "assistant"
                ]
                if not assistant_texts:
                    continue
                text = _extract_reason(" ".join(assistant_texts))
                if len(text) < 8:
                    continue
                counts[answer] += 1
                yield {
                    "text": text,
                    "label": answer,
                    "label_id": LABELS[answer],
                    "source": "TeleAntiFraud/sft/train.jsonl:assistant_reason",
                    "original_label": answer,
                }
                if all(counts[label] >= max_per_label for label in LABELS):
                    return


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def stratified_split(rows: list[dict[str, object]], seed: int) -> dict[str, list[dict[str, object]]]:
    rng = random.Random(seed)
    by_label: dict[str, list[dict[str, object]]] = {label: [] for label in LABELS}
    for row in rows:
        by_label[str(row["label"])].append(row)

    splits = {"train": [], "dev": [], "test": []}
    for label_rows in by_label.values():
        rng.shuffle(label_rows)
        n = len(label_rows)
        n_test = max(1, int(n * 0.1))
        n_dev = max(1, int(n * 0.1))
        splits["test"].extend(label_rows[:n_test])
        splits["dev"].extend(label_rows[n_test : n_test + n_dev])
        splits["train"].extend(label_rows[n_test + n_dev :])
    for split_rows in splits.values():
        rng.shuffle(split_rows)
    return splits


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a binary Chinese fraud text dataset for MacBERT fine-tuning.")
    parser.add_argument("--resource-root", type=Path, default=DEFAULT_RESOURCE_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_RESOURCE_ROOT / "processed" / "macbert_fraud_text")
    parser.add_argument("--max-per-source-label", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rows = []
    rows.extend(iter_chifraud(args.resource_root, args.max_per_source_label))
    rows.extend(iter_teleantifraud(args.resource_root, args.max_per_source_label))

    deduped = {f"{row['label']}::{row['text']}": row for row in rows}
    rows = list(deduped.values())
    if not rows:
        raise SystemExit("No training rows were extracted. Check dataset paths.")

    splits = stratified_split(rows, args.seed)
    for split, split_rows in splits.items():
        write_jsonl(args.output_dir / f"{split}.jsonl", split_rows)

    manifest = {
        "task": "binary_fraud_text_classification",
        "labels": LABELS,
        "source_counts": Counter(str(row["source"]) for row in rows),
        "label_counts": Counter(str(row["label"]) for row in rows),
        "split_counts": {split: Counter(str(row["label"]) for row in split_rows) for split, split_rows in splits.items()},
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
