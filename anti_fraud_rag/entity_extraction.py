from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from .utils import extract_domains, extract_urls


ROLE_PATTERNS = {
    "campus_office": [
        r"school office",
        r"university office",
        r"student affairs",
        r"financial aid",
        r"\bIT support\b",
        r"\b教务处\b",
        r"\b学生处\b",
        r"\b资助中心\b",
        r"\b学校\b",
        r"\b学院\b",
    ],
    "platform_or_bank": [
        r"\bbank\b",
        r"\bpaypal\b",
        r"\bwestpac\b",
        r"\bmailbox\b",
        r"\baccount\b",
        r"\b银行\b",
        r"\b客服\b",
        r"\b邮箱\b",
        r"\b账号\b",
    ],
    "job_or_hr": [
        r"\bHR\b",
        r"\bhuman resources\b",
        r"\brecruiter\b",
        r"\binternship\b",
        r"\bonboarding\b",
        r"\b招聘\b",
        r"\b实习\b",
        r"\b录用\b",
        r"\b兼职\b",
    ],
    "authority": [
        r"\bpolice\b",
        r"\bcourt\b",
        r"\btax\b",
        r"\b公安\b",
        r"\b警方\b",
        r"\b法院\b",
        r"\b税务\b",
    ],
}


@dataclass
class EntityExtraction:
    urls: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    email_addresses: list[str] = field(default_factory=list)
    phone_numbers: list[str] = field(default_factory=list)
    money_mentions: list[str] = field(default_factory=list)
    sender_identity_clues: list[str] = field(default_factory=list)
    role_clues: list[str] = field(default_factory=list)
    organizations_or_services: list[str] = field(default_factory=list)
    evidence_subjects: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def subjects(self) -> list[str]:
        values = []
        values.extend(self.sender_identity_clues)
        values.extend(self.organizations_or_services)
        values.extend(self.urls)
        values.extend(self.domains)
        values.extend(self.evidence_subjects)
        return dedupe_preserve_order(values)


def extract_entities(text: str, evidence: list[dict] | None = None) -> EntityExtraction:
    raw = text or ""
    urls = extract_urls(raw)
    domains = extract_domains(raw)
    emails = sorted(set(re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", raw)))
    phones = sorted(set(re.findall(r"(?<!\d)(?:\+?\d[\d\s-]{6,}\d)(?!\d)", raw)))
    money = extract_money_mentions(raw)
    role_clues, sender_clues = extract_role_and_sender_clues(raw)
    organizations = extract_organization_like_terms(raw)
    evidence_subjects = extract_evidence_subjects(evidence or [])

    return EntityExtraction(
        urls=urls,
        domains=domains,
        email_addresses=emails,
        phone_numbers=phones,
        money_mentions=money,
        sender_identity_clues=sender_clues,
        role_clues=role_clues,
        organizations_or_services=organizations,
        evidence_subjects=evidence_subjects,
    )


def extract_role_and_sender_clues(text: str) -> tuple[list[str], list[str]]:
    role_clues: list[str] = []
    sender_clues: list[str] = []
    for role, patterns in ROLE_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                clue = match.group(0)
                role_clues.append(role)
                sender_clues.append(clue)
    return dedupe_preserve_order(role_clues), dedupe_preserve_order(sender_clues)


def extract_organization_like_terms(text: str) -> list[str]:
    patterns = [
        r"\b[A-Z][A-Za-z0-9&.\- ]{1,40}\b(?:University|College|Bank|Support|Office|Center|Centre|HR|PayPal|Westpac)\b",
        r"\b(?:PayPal|Westpac|Microsoft|Google|Apple|Alipay|WeChat|Bank of China|ICBC)\b",
        r"[\u4e00-\u9fff]{2,12}(?:大学|学院|银行|客服|资助中心|教务处|学生处|派出所|公安|法院)",
    ]
    values: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            value = match.group(0).strip()
            if value.lower().startswith(("your ", "the ", "a ", "an ")):
                continue
            values.append(value)
    return dedupe_preserve_order(values)[:12]


def extract_evidence_subjects(evidence: list[dict]) -> list[str]:
    subjects: list[str] = []
    for item in evidence[:3]:
        title = item.get("title")
        source = item.get("source")
        if title:
            subjects.append(str(title))
        if source:
            subjects.append(str(source))
    return dedupe_preserve_order(subjects)[:8]


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


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result
