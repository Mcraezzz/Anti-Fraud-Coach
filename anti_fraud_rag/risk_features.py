from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from .utils import extract_domains, extract_urls


FEATURE_PATTERNS = {
    "credential_request": [
        "验证码",
        "短信验证码",
        "密码",
        "登录二维码",
        "账号密码",
        "verification code",
        "sms code",
        "password",
        "login code",
        "credentials",
        "security question",
    ],
    "financial_info": [
        "银行卡",
        "支付密码",
        "信用卡",
        "收款码",
        "bank card",
        "credit card",
        "banking details",
        "payment password",
        "direct deposit",
    ],
    "upfront_payment": [
        "保证金",
        "押金",
        "垫付",
        "培训费",
        "认证费",
        "手续费",
        "deposit",
        "upfront",
        "training fee",
        "verification fee",
        "handling fee",
        "service fee",
    ],
    "urgency_pressure": [
        "今晚",
        "立即",
        "马上",
        "逾期",
        "紧急",
        "urgent",
        "immediately",
        "within 24 hours",
        "suspended",
        "deadline",
    ],
    "impersonation": [
        "学校资助中心",
        "辅导员",
        "老师",
        "客服",
        "HR",
        "police",
        "court",
        "customer service",
        "human resources",
        "university office",
    ],
    "job_or_internship": [
        "实习",
        "兼职",
        "录用",
        "内推",
        "招聘",
        "internship",
        "job offer",
        "part-time",
        "onboarding",
        "remote job",
    ],
    "campus_context": [
        "学校",
        "校园",
        "学生",
        "学号",
        "奖学金",
        "助学金",
        "校园卡",
        "university",
        "student",
        "campus",
        "scholarship",
        "grant",
        "mailbox",
    ],
    "refund_or_reward": [
        "退款",
        "退费",
        "补贴",
        "中奖",
        "理赔",
        "refund",
        "compensation",
        "subsidy",
        "reward",
        "winner",
    ],
    "investment_or_loan": [
        "贷款",
        "投资",
        "返利",
        "提现",
        "虚拟货币",
        "loan",
        "investment",
        "crypto",
        "withdrawal",
        "high return",
    ],
}


WEIGHTS = {
    "credential_request": 0.18,
    "financial_info": 0.16,
    "upfront_payment": 0.16,
    "urgency_pressure": 0.12,
    "impersonation": 0.12,
    "job_or_internship": 0.08,
    "campus_context": 0.06,
    "refund_or_reward": 0.06,
    "investment_or_loan": 0.06,
}


@dataclass
class RiskFeatures:
    detected_language: str
    urls: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    phone_numbers: list[str] = field(default_factory=list)
    money_mentions: list[str] = field(default_factory=list)
    matched_categories: list[str] = field(default_factory=list)
    matched_terms: list[str] = field(default_factory=list)
    category_hits: dict[str, list[str]] = field(default_factory=dict)
    risk_keyword_score: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def extract_risk_features(text: str, detected_language: str) -> RiskFeatures:
    raw = text or ""
    lower = raw.lower()
    urls = extract_urls(raw)
    domains = extract_domains(raw)
    phone_numbers = sorted(set(re.findall(r"(?<!\d)(?:\+?\d[\d\s-]{6,}\d)(?!\d)", raw)))
    money_mentions = extract_money_mentions(raw)

    category_hits: dict[str, list[str]] = {}
    matched_terms: list[str] = []
    score = 0.0
    for category, terms in FEATURE_PATTERNS.items():
        hits = []
        for term in terms:
            haystack = lower if term.isascii() else raw
            needle = term.lower() if term.isascii() else term
            if needle in haystack:
                hits.append(term)
        if hits:
            category_hits[category] = hits
            matched_terms.extend(hits)
            score += WEIGHTS.get(category, 0.05)

    if urls or domains:
        score += 0.12
    if phone_numbers:
        score += 0.06
    if money_mentions:
        score += 0.08

    return RiskFeatures(
        detected_language=detected_language,
        urls=urls,
        domains=domains,
        phone_numbers=phone_numbers,
        money_mentions=money_mentions,
        matched_categories=sorted(category_hits.keys()),
        matched_terms=dedupe_preserve_order(matched_terms),
        category_hits=category_hits,
        risk_keyword_score=round(min(score, 1.0), 4),
    )


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def extract_money_mentions(text: str) -> list[str]:
    patterns = [
        r"(?:￥|¥|\$|€)\s?\d+(?:\.\d+)?",
        r"(?:rmb|usd|eur)\s?\d+(?:\.\d+)?",
        r"\d+(?:\.\d+)?\s?(?:元|块|人民币|rmb|usd|eur|dollars?|yuan)",
    ]
    mentions: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            mentions.append(match.group(0).strip())
    return sorted(set(mentions))
