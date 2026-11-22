from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import torch
from sklearn.metrics import accuracy_score, classification_report, f1_score
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer


DEFAULT_RESOURCE_ROOT = Path(r"D:\CARIC模型&数据集")
LABEL2ID = {"normal": 0, "fraud": 1}
ID2LABEL = {0: "normal", 1: "fraud"}


def read_jsonl(path: Path, limit: int = 0) -> list[dict[str, object]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            rows.append(json.loads(line))
            if limit and len(rows) >= limit:
                break
    return rows


class FraudTextDataset(Dataset):
    def __init__(self, rows: list[dict[str, object]], tokenizer, max_length: int):
        self.rows = rows
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        row = self.rows[index]
        encoded = self.tokenizer(
            str(row["text"]),
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )
        item = {key: value.squeeze(0) for key, value in encoded.items()}
        item["labels"] = torch.tensor(int(row["label_id"]), dtype=torch.long)
        return item


def set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def configure_trainable_layers(model, freeze_encoder: bool, unfreeze_last_n: int) -> None:
    if not freeze_encoder and unfreeze_last_n <= 0:
        return

    base_model = getattr(model, "base_model", None)
    if base_model is not None and (freeze_encoder or unfreeze_last_n > 0):
        for param in base_model.parameters():
            param.requires_grad = False

    if unfreeze_last_n > 0:
        encoder = getattr(base_model, "encoder", None)
        layers = getattr(encoder, "layer", None)
        if layers is not None:
            for layer in layers[-unfreeze_last_n:]:
                for param in layer.parameters():
                    param.requires_grad = True

    for param in model.classifier.parameters():
        param.requires_grad = True


def evaluate(model, loader: DataLoader, device: torch.device) -> dict[str, object]:
    model.eval()
    preds: list[int] = []
    labels: list[int] = []
    total_loss = 0.0
    with torch.no_grad():
        for batch in loader:
            batch = {key: value.to(device) for key, value in batch.items()}
            output = model(**batch)
            total_loss += float(output.loss.item())
            preds.extend(torch.argmax(output.logits, dim=-1).detach().cpu().tolist())
            labels.extend(batch["labels"].detach().cpu().tolist())

    report = classification_report(labels, preds, target_names=[ID2LABEL[0], ID2LABEL[1]], output_dict=True, zero_division=0)
    return {
        "loss": total_loss / max(1, len(loader)),
        "accuracy": accuracy_score(labels, preds),
        "macro_f1": f1_score(labels, preds, average="macro", zero_division=0),
        "report": report,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune local MacBERT for binary fraud text classification.")
    parser.add_argument("--resource-root", type=Path, default=DEFAULT_RESOURCE_ROOT)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_RESOURCE_ROOT / "processed" / "macbert_fraud_text")
    parser.add_argument("--base-model", type=Path, default=DEFAULT_RESOURCE_ROOT / "models" / "hfl_chinese-macbert-base")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_RESOURCE_ROOT / "models" / "hfl_chinese-macbert-fraud-finetuned-v2")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--max-length", type=int, default=192)
    parser.add_argument("--max-train-samples", type=int, default=0)
    parser.add_argument("--max-dev-samples", type=int, default=0)
    parser.add_argument("--max-steps", type=int, default=0)
    parser.add_argument("--freeze-encoder", action="store_true")
    parser.add_argument("--unfreeze-last-n", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    set_seed(args.seed)
    train_rows = read_jsonl(args.data_dir / "train.jsonl", args.max_train_samples)
    dev_rows = read_jsonl(args.data_dir / "dev.jsonl", args.max_dev_samples)
    if not train_rows or not dev_rows:
        raise SystemExit("Training data is empty. Run prepare_macbert_fraud_dataset.py first.")

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base_model,
        num_labels=2,
        label2id=LABEL2ID,
        id2label=ID2LABEL,
        local_files_only=True,
    )
    configure_trainable_layers(model, args.freeze_encoder, args.unfreeze_last_n)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    train_loader = DataLoader(FraudTextDataset(train_rows, tokenizer, args.max_length), batch_size=args.batch_size, shuffle=True)
    dev_loader = DataLoader(FraudTextDataset(dev_rows, tokenizer, args.max_length), batch_size=args.batch_size)

    optimizer = torch.optim.AdamW((param for param in model.parameters() if param.requires_grad), lr=args.lr)
    trainable = sum(param.numel() for param in model.parameters() if param.requires_grad)
    total = sum(param.numel() for param in model.parameters())

    global_step = 0
    history = []
    for epoch in range(args.epochs):
        model.train()
        running_loss = 0.0
        for batch in train_loader:
            batch = {key: value.to(device) for key, value in batch.items()}
            output = model(**batch)
            output.loss.backward()
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            running_loss += float(output.loss.item())
            global_step += 1
            if args.max_steps and global_step >= args.max_steps:
                break
        metrics = evaluate(model, dev_loader, device)
        metrics["epoch"] = epoch + 1
        metrics["train_loss"] = running_loss / max(1, min(len(train_loader), global_step))
        history.append(metrics)
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
        if args.max_steps and global_step >= args.max_steps:
            break

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    metadata = {
        "base_model": str(args.base_model),
        "labels": LABEL2ID,
        "device": str(device),
        "train_samples": len(train_rows),
        "dev_samples": len(dev_rows),
        "epochs": args.epochs,
        "global_step": global_step,
        "freeze_encoder": args.freeze_encoder,
        "unfreeze_last_n": args.unfreeze_last_n,
        "trainable_parameters": trainable,
        "total_parameters": total,
        "history": history,
    }
    (args.output_dir / "training_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"saved_to": str(args.output_dir), **metadata}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
