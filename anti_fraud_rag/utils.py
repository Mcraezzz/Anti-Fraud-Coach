from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse


URL_RE = re.compile(r"https?://[^\s<>'\"，。；、)）]+", re.IGNORECASE)
DOMAIN_RE = re.compile(
    r"\b(?:[a-zA-Z0-9-]{1,63}\.)+(?:[a-zA-Z]{2,}|xn--[a-zA-Z0-9-]+)\b"
)


def read_jsonl(path: Path):
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text)).strip()
    return text


def strip_network_indicators(text: str) -> str:
    text = URL_RE.sub(" ", text or "")
    return DOMAIN_RE.sub(" ", text)


def detect_language(text: str) -> str:
    text = strip_network_indicators(text or "")
    chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
    english = len(re.findall(r"[A-Za-z]", text))
    if chinese and english:
        return "mixed"
    if chinese:
        return "zh"
    if english:
        return "en"
    return "unknown"


def extract_urls(text: str) -> list[str]:
    return [m.group(0).rstrip(".,;:!?") for m in URL_RE.finditer(text or "")]


def extract_domains(text: str) -> list[str]:
    domains: set[str] = set()
    for url in extract_urls(text):
        parsed = urlparse(url)
        if parsed.netloc:
            domains.add(parsed.netloc.lower().lstrip("www."))
    for match in DOMAIN_RE.finditer(text or ""):
        domains.add(match.group(0).lower().lstrip("www."))
    return sorted(domains)


def compact(text: str, limit: int = 900) -> str:
    text = normalize_text(text)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."
