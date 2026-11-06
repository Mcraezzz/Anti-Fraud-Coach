from __future__ import annotations

import csv
import json
from urllib.parse import urlparse
from collections import Counter, defaultdict
from pathlib import Path

from .config import AppConfig
from .schemas import IocStore, KnowledgeItem
from .utils import compact, normalize_text, read_jsonl


CHIFRAUD_LABELS = {
    "0": "Normal text",
    "1": "Gambling",
    "2": "Whoring",
    "3": "Fake Credentials",
    "4": "Fake Bank Card",
    "5": "Prohibited Drugs",
    "6": "Unauthorized Cash-Out",
    "7": "Unauthorized Certification",
    "8": "Fake SIM",
    "9": "Underground Loan",
    "10": "New Fraud Category",
}

SMS_LABELS = {
    "0": "Benign SMS/MMS",
    "1": "Malicious SMS/MMS",
    "benign": "Benign SMS/MMS",
    "ham": "Benign SMS/MMS",
    "normal": "Benign SMS/MMS",
    "malicious": "Malicious SMS/MMS",
    "smishing": "Smishing",
    "phishing": "Phishing",
}

DISCORD_LABELS = {
    "0": "Benign Discord message",
    "1": "Discord phishing or scam",
    "benign": "Benign Discord message",
    "phishing": "Discord phishing or scam",
    "scam": "Discord phishing or scam",
}


def load_knowledge_corpus(config: AppConfig) -> tuple[list[KnowledgeItem], IocStore]:
    items: list[KnowledgeItem] = []
    iocs = IocStore()
    root = config.datasets_dir

    items.extend(load_campus_rules(root))
    items.extend(load_chifraud(root, config.max_cases_per_source))
    items.extend(load_sms_mms(root, config.max_cases_per_source))
    items.extend(load_discord_phishing(root, config.max_cases_per_source))
    items.extend(load_email_triage(root, config.max_cases_per_source))

    load_iocs(root, iocs, config.max_iocs_per_source)
    return items, iocs


def load_campus_rules(root: Path) -> list[KnowledgeItem]:
    path = root / "campus_anti_fraud_bilingual_rules" / "campus_anti_fraud_rules_zh_en.jsonl"
    if not path.exists():
        return []
    items: list[KnowledgeItem] = []
    for obj in read_jsonl(path):
        text = "\n".join(
            [
                f"Category zh: {obj['category_zh']}",
                f"Category en: {obj['category_en']}",
                f"Scenario zh: {obj['scenario_zh']}",
                f"Scenario en: {obj['scenario_en']}",
                "Risk signals zh: " + "; ".join(obj["risk_signals_zh"]),
                "Risk signals en: " + "; ".join(obj["risk_signals_en"]),
                f"Suggestion zh: {obj['suggestion_zh']}",
                f"Suggestion en: {obj['suggestion_en']}",
                "Keywords zh: " + ", ".join(obj["keywords_zh"]),
                "Keywords en: " + ", ".join(obj["keywords_en"]),
            ]
        )
        items.append(
            KnowledgeItem(
                id=obj["id"],
                source="campus_rules",
                title=f"{obj['category_zh']} / {obj['category_en']}",
                text=text,
                language="mixed",
                category=obj["category_en"],
                risk_level=obj["risk_level"],
                metadata={
                    "category_zh": obj["category_zh"],
                    "category_en": obj["category_en"],
                    "risk_level": obj["risk_level"],
                },
            )
        )
    return items


def load_chifraud(root: Path, max_items: int) -> list[KnowledgeItem]:
    path = root / "ChiFraud" / "dataset" / "ChiFraud_train.csv"
    if not path.exists():
        return []
    per_label = max(20, max_items // 8)
    counts: Counter[str] = Counter()
    items: list[KnowledgeItem] = []
    with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
        header = handle.readline()
        for line in handle:
            if len(items) >= max_items:
                break
            line = line.strip()
            if not line or "\t" not in line:
                continue
            label, text = line.split("\t", 1)
            if label == "0" and counts[label] >= 80:
                continue
            if label != "0" and counts[label] >= per_label:
                continue
            text = compact(text, 700)
            label_name = CHIFRAUD_LABELS.get(label, f"Label {label}")
            items.append(
                KnowledgeItem(
                    id=f"chifraud-{len(items)+1:05d}",
                    source="ChiFraud",
                    title=f"Chinese fraud text case: {label_name}",
                    text=f"Input text: {text}\nGround-truth category: {label_name}",
                    language="zh",
                    category=label_name,
                    risk_level="Low" if label == "0" else "High",
                    metadata={"label_id": label, "label_name": label_name},
                )
            )
            counts[label] += 1
    return items


def load_sms_mms(root: Path, max_items: int) -> list[KnowledgeItem]:
    path = root / "hf_notd5a_malicious-benign-sms-mms-dataset" / "dataset_v3_for_deberta.csv"
    if not path.exists():
        return []
    items: list[KnowledgeItem] = []
    counts: defaultdict[str, int] = defaultdict(int)
    per_label = max(100, max_items // 2)
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            label = normalize_text(row.get("label", ""))
            if counts[label] >= per_label or len(items) >= max_items:
                continue
            msg = compact(row.get("message", ""), 650)
            if not msg:
                continue
            label_name = label_display_name(label, SMS_LABELS)
            risk = "High" if label_name != "Benign SMS/MMS" else "Low"
            items.append(
                KnowledgeItem(
                    id=f"sms-mms-{len(items)+1:05d}",
                    source="sms_mms",
                    title=f"SMS/MMS case: {label_name}",
                    text=f"Message: {msg}\nDataset label: {label_name}",
                    language="en",
                    category=label_name,
                    risk_level=risk,
                    metadata={
                        "label": label_name,
                        "raw_label": label,
                        "ai_generated": row.get("ai_generated"),
                        "has_url": row.get("has_url"),
                    },
                )
            )
            counts[label] += 1
    return items


def load_discord_phishing(root: Path, max_items: int) -> list[KnowledgeItem]:
    path = root / "hf_wangyuancheng_discord-phishing-scam-clean" / "discord-phishing-scam-detection.csv"
    if not path.exists():
        return []
    items: list[KnowledgeItem] = []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if len(items) >= max_items:
                break
            label = normalize_text(row.get("label", ""))
            msg = compact(row.get("msg_content", ""), 650)
            if not msg:
                continue
            label_name = label_display_name(label, DISCORD_LABELS)
            risk = "High" if "phish" in label_name.lower() or "scam" in label_name.lower() else "Low"
            items.append(
                KnowledgeItem(
                    id=f"discord-{len(items)+1:05d}",
                    source="discord_phishing",
                    title=f"Discord social case: {label_name}",
                    text=f"Message: {msg}\nDataset label: {label_name}",
                    language="en",
                    category=label_name,
                    risk_level=risk,
                    metadata={"label": label_name, "raw_label": label},
                )
            )
    return items


def load_email_triage(root: Path, max_items: int) -> list[KnowledgeItem]:
    path = root / "hf_weijianzhg_email-safety-triage-10k" / "data" / "email_safety_triage_10k.jsonl"
    if not path.exists():
        return []
    items: list[KnowledgeItem] = []
    for obj in read_jsonl(path):
        if len(items) >= max_items:
            break
        text = compact(json.dumps(obj, ensure_ascii=False), 900)
        label = infer_email_label(obj)
        risk = "High" if any(x in label.lower() for x in ["phish", "malicious", "spam", "scam"]) else "Medium"
        items.append(
            KnowledgeItem(
                id=f"email-triage-{len(items)+1:05d}",
                source="email_safety_triage",
                title=f"Email safety triage case: {label}",
                text=text,
                language="en",
                category=label,
                risk_level=risk,
                metadata={"label": label},
            )
        )
    return items


def infer_email_label(obj: dict) -> str:
    for key in ("label", "category", "verdict", "risk", "classification"):
        value = obj.get(key)
        if isinstance(value, str) and value:
            return value
    output = obj.get("output")
    if isinstance(output, str) and output.strip():
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            for key in ("risk", "triage", "priority", "classification", "label"):
                value = parsed.get(key)
                if isinstance(value, str) and value:
                    return value
    for value in obj.values():
        if isinstance(value, dict):
            nested = infer_email_label(value)
            if nested != "unknown":
                return nested
    return "unknown"


def load_iocs(root: Path, iocs: IocStore, max_per_source: int) -> None:
    sources = [
        (root / "github_Phishing-Database_Phishing.Database" / "phishing-domains-ACTIVE.txt", "domain"),
        (root / "github_Phishing-Database_Phishing.Database" / "phishing-links-ACTIVE.txt", "url"),
        (root / "hf_phishdestroy_destroylist" / "domains.csv", "domain"),
    ]
    for path, kind in sources:
        if not path.exists():
            continue
        count = 0
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if kind == "domain":
                    value = normalize_domain_ioc(line)
                    if value:
                        iocs.domains.add(value)
                else:
                    url_value = normalize_url_ioc(line)
                    domain_value = normalize_domain_ioc(line)
                    if url_value:
                        iocs.urls.add(url_value)
                    if domain_value:
                        iocs.domains.add(domain_value)
                    if not url_value and not domain_value:
                        continue
                count += 1
                if count >= max_per_source:
                    break

    scam_domains = root / "github_scamsniffer_scam-database" / "blacklist" / "domains.json"
    if scam_domains.exists():
        with scam_domains.open("r", encoding="utf-8", errors="replace") as handle:
            try:
                data = json.load(handle)
            except json.JSONDecodeError:
                data = []
        for value in data[:max_per_source]:
            normalized = normalize_domain_ioc(str(value))
            if normalized:
                iocs.domains.add(normalized)


def label_display_name(label: str, mapping: dict[str, str]) -> str:
    key = normalize_text(label).lower()
    return mapping.get(key, label or "unknown")


def normalize_domain_ioc(value: str) -> str:
    value = normalize_text(value).strip().strip(",")
    if not value or value.lower() in {"domain", "url"}:
        return ""
    if "://" not in value:
        value = "http://" + value
    parsed = urlparse(value)
    host = parsed.netloc or parsed.path.split("/")[0]
    return host.lower().lstrip("www.").strip()


def normalize_url_ioc(value: str) -> str:
    value = normalize_text(value).strip().strip(",")
    if not value or value.lower() in {"domain", "url"}:
        return ""
    if "://" not in value:
        value = "http://" + value
    parsed = urlparse(value)
    host = (parsed.netloc or "").lower().lstrip("www.")
    if not host:
        return ""
    path = parsed.path.rstrip("/")
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{host}{path}{query}"
