import argparse
import json
import sys

from anti_fraud_rag.config import AppConfig
from anti_fraud_rag.rag_engine import AntiFraudRagEngine


EXAMPLES = {
    "zh": "【学校资助中心】你已获得2026年度助学金补贴，请在今晚22点前点击 http://campus-grant.example.cn 填写身份证、银行卡和短信验证码，逾期视为放弃。",
    "en": "Your university mailbox quota is full. Verify your student account now at http://secure-campus-login.example.com or your email access will be suspended. Enter your password and SMS code.",
    "mixed": "Hi同学，我们是HR，远程实习已录用。Please pay a 299 RMB training deposit first, then we will send the onboarding materials.",
}


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser()
    parser.add_argument("--text", default=None, help="Input text to analyze.")
    parser.add_argument("--example", choices=sorted(EXAMPLES), default="zh")
    parser.add_argument("--mock", action="store_true", help="Run without Qwen API call.")
    parser.add_argument("--top-k", type=int, default=6)
    args = parser.parse_args()

    config = AppConfig.from_env()
    engine = AntiFraudRagEngine.load(config)
    text = args.text or EXAMPLES[args.example]
    result = engine.analyze(text, top_k=args.top_k, mock=args.mock)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
