from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import classification_report
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.model_inference_service import URL_FEATURE_NAMES, extract_url_feature_dict  # noqa: E402


DEFAULT_RESOURCE_ROOT = Path(r"D:\CARIC模型&数据集")
LABEL_MAP = {0: "benign", 1: "defacement", 2: "malware", 3: "phishing"}


def ensure_dataset(dataset_dir: Path) -> None:
    required = [dataset_dir / "train.csv", dataset_dir / "val.csv", dataset_dir / "test.csv"]
    if all(path.exists() for path in required):
        return
    dataset_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "hf",
            "download",
            "bgspaditya/malicious-600k",
            "--type",
            "dataset",
            "--local-dir",
            str(dataset_dir),
            "--include",
            "*.csv",
        ],
        check=True,
    )


def read_split(path: Path, max_rows: int = 0) -> pd.DataFrame:
    df = pd.read_csv(path, nrows=max_rows or None)
    if "url" not in df.columns or "labels" not in df.columns:
        raise ValueError(f"{path} must contain url and labels columns")
    df = df[["url", "labels"]].dropna()
    df["label"] = df["labels"].astype(int).map(LABEL_MAP)
    return df[["url", "label"]].dropna()


def featurize(urls: pd.Series) -> pd.DataFrame:
    rows = []
    for url in urls.astype(str):
        features = extract_url_feature_dict(url)
        rows.append({name: features.get(name, 0) for name in URL_FEATURE_NAMES})
    return pd.DataFrame(rows, columns=URL_FEATURE_NAMES)


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrain the malicious URL classifier with the current sklearn/numpy runtime.")
    parser.add_argument("--resource-root", type=Path, default=DEFAULT_RESOURCE_ROOT)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_RESOURCE_ROOT / "datasets" / "bgspaditya_malicious-600k")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_RESOURCE_ROOT / "models" / "khagu_malicious-url-detection-models")
    parser.add_argument("--max-train-rows", type=int, default=120000)
    parser.add_argument("--max-test-rows", type=int, default=30000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    ensure_dataset(args.dataset_dir)
    train_df = read_split(args.dataset_dir / "train.csv", args.max_train_rows)
    test_df = read_split(args.dataset_dir / "test.csv", args.max_test_rows)

    x_train = featurize(train_df["url"])
    x_test = featurize(test_df["url"])
    encoder = LabelEncoder()
    y_train = encoder.fit_transform(train_df["label"])
    y_test = encoder.transform(test_df["label"])

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)

    model = DecisionTreeClassifier(random_state=args.seed, class_weight="balanced", min_samples_leaf=2)
    model.fit(x_train_scaled, y_train)

    preds = model.predict(x_test_scaled)
    report = classification_report(y_test, preds, target_names=encoder.classes_, output_dict=True, zero_division=0)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, args.output_dir / "decision_tree_current.pkl")
    joblib.dump(scaler, args.output_dir / "scaler_current.pkl")
    joblib.dump(encoder, args.output_dir / "label_encoder_current.pkl")

    manifest = {
        "dataset": "bgspaditya/malicious-600k",
        "label_map": LABEL_MAP,
        "feature_names": URL_FEATURE_NAMES,
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "model": "DecisionTreeClassifier",
        "model_file": "decision_tree_current.pkl",
        "scaler_file": "scaler_current.pkl",
        "label_encoder_file": "label_encoder_current.pkl",
        "classification_report": report,
    }
    (args.output_dir / "url_classifier_current_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
