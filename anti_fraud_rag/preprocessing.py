from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from .utils import normalize_text


@dataclass
class PreprocessedInput:
    raw_text: str
    normalized_text: str
    text_sources: list[str] = field(default_factory=list)
    removed_control_chars: int = 0
    whitespace_collapsed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def preprocess_media_text(text: str, source: str = "user_text") -> PreprocessedInput:
    raw = text or ""
    without_controls, removed = remove_control_characters(raw)
    normalized = normalize_text(without_controls)
    return PreprocessedInput(
        raw_text=raw,
        normalized_text=normalized,
        text_sources=[source] if normalized else [],
        removed_control_chars=removed,
        whitespace_collapsed=without_controls != normalized,
    )


def build_analysis_input(input_text: str, ocr_results: list[Any]) -> PreprocessedInput:
    parts: list[str] = []
    sources: list[str] = []

    typed = preprocess_media_text(input_text, source="typed_text")
    if typed.normalized_text:
        parts.append(typed.normalized_text)
        sources.extend(typed.text_sources)

    removed_controls = typed.removed_control_chars
    whitespace_collapsed = typed.whitespace_collapsed

    for result in ocr_results or []:
        text = str(getattr(result, "text", "") or "")
        image_name = str(getattr(result, "image_name", "uploaded_image") or "uploaded_image")
        processed = preprocess_media_text(text, source=f"image_ocr:{image_name}")
        removed_controls += processed.removed_control_chars
        whitespace_collapsed = whitespace_collapsed or processed.whitespace_collapsed
        if processed.normalized_text:
            parts.append(f"[Image OCR: {image_name}]\n{processed.normalized_text}")
            sources.extend(processed.text_sources)

    combined = "\n\n".join(parts).strip()
    normalized = normalize_text_preserve_blocks(combined)
    return PreprocessedInput(
        raw_text=combined,
        normalized_text=normalized,
        text_sources=dedupe_preserve_order(sources),
        removed_control_chars=removed_controls,
        whitespace_collapsed=whitespace_collapsed or combined != normalized,
    )


def normalize_text_preserve_blocks(text: str) -> str:
    text = re.sub(r"[ \t\r\f\v]+", " ", text or "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_control_characters(text: str) -> tuple[str, int]:
    cleaned_chars: list[str] = []
    removed = 0
    for char in text or "":
        if char in "\n\t\r":
            cleaned_chars.append(char)
        elif ord(char) < 32:
            removed += 1
        else:
            cleaned_chars.append(char)
    return "".join(cleaned_chars), removed


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result
