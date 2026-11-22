from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

os.environ["ANTI_FRAUD_QWEN_ENABLED"] = "1"

from app.core.config import DATA_DIR, settings  # noqa: E402
from app.services.model_inference_service import generate_qwen_advice  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate offline Qwen feedback for training/question bank demos.")
    parser.add_argument("--questions", type=Path, default=DATA_DIR / "training_questions.json")
    parser.add_argument("--output", type=Path, default=settings.resource_root / "processed" / "qwen_feedback" / "training_feedback.json")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    questions = json.loads(args.questions.read_text(encoding="utf-8"))[: args.limit]
    rows = []
    for item in questions:
        prompt_text = item.get("scenario") or item.get("question") or json.dumps(item, ensure_ascii=False)
        analysis = {
            "risk_level": "训练复盘",
            "scam_type": item.get("type", "反诈训练"),
            "evidence": item.get("risk_points", []) or [item.get("explanation", "")],
        }
        result = generate_qwen_advice(prompt_text, analysis)
        rows.append(
            {
                "id": item.get("id"),
                "input": prompt_text,
                "status": result.get("status"),
                "detail": result.get("detail", ""),
                "feedback": result.get("text", ""),
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "count": len(rows)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
