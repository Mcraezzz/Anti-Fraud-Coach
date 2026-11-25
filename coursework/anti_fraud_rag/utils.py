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


def normalize_network_indicator(value: str, *, include_path: bool = False) -> str:
    """Normalize hosts consistently without changing case-sensitive URL paths."""
    value = normalize_text(value).strip(",")
    if not value or value.lower() in {"domain", "url"}:
        return ""
    try:
        parsed = urlparse(value if "://" in value else "http://" + value)
        host = (parsed.hostname or "").lower().removeprefix("www.").rstrip(".")
        if not host:
            return ""
        if not include_path:
            return host
        # Credentials are not part of the network destination; ports are.
        authority = f"[{host}]" if ":" in host else host
        if parsed.port is not None:
            authority += f":{parsed.port}"
        query = f"?{parsed.query}" if parsed.query else ""
        return f"{authority}{parsed.path.rstrip('/')}{query}"
    except ValueError:
        return ""


def extract_domains(text: str) -> list[str]:
    candidates = extract_urls(text)
    candidates.extend(match.group(0) for match in DOMAIN_RE.finditer(text or ""))
    return sorted({host for value in candidates if (host := normalize_network_indicator(value))})


def compact(text: str, limit: int = 900) -> str:
    text = normalize_text(text)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."
