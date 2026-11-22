from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

os.environ["ANTI_FRAUD_QWEN_ENABLED"] = "1"

from app.core.config import settings  # noqa: E402
from app.services.model_inference_service import generate_qwen_advice  # noqa: E402


def main() -> None:
    started = time.time()
    sample = "有人自称平台客服，说我的账户冻结，需要打开链接并提供验证码。"
    analysis = {
        "risk_level": "高风险",
        "scam_type": "冒充客服",
        "evidence": ["身份伪装：平台客服", "隐私索取：验证码", "可疑链接：陌生链接"],
    }
    result = generate_qwen_advice(sample, analysis)
    status = {
        "enabled_for_this_process": True,
        "model": str(settings.qwen_model_path),
        "elapsed_seconds": round(time.time() - started, 2),
        "result_status": result.get("status"),
        "detail": result.get("detail", ""),
        "preview": result.get("text", "")[:300],
    }
    output = settings.qwen_model_path / "prewarm_status.json"
    output.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
