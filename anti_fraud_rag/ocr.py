from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import AppConfig


@dataclass
class OcrLine:
    text: str
    confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OcrResult:
    image_name: str
    text: str
    lines: list[OcrLine]
    engine: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_name": self.image_name,
            "text": self.text,
            "lines": [line.to_dict() for line in self.lines],
            "engine": self.engine,
            "error": self.error,
        }


class ImageTextExtractor:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._ocr: Any | None = None
        self._engine = "PaddleOCR"

    def extract(self, image_path: Path, image_name: str | None = None) -> OcrResult:
        display_name = image_name or image_path.name
        if not self.config.use_ocr:
            return OcrResult(display_name, "", [], self._engine, "OCR is disabled by USE_OCR=false.")

        try:
            ocr = self._load_paddleocr()
            raw = run_paddleocr_prediction(ocr, image_path)
            lines = parse_ocr_lines(raw)
            text = "\n".join(line.text for line in lines if line.text.strip())
            return OcrResult(display_name, text, lines, self._engine)
        except Exception as exc:
            return OcrResult(display_name, "", [], self._engine, f"{type(exc).__name__}: {exc}")

    def _load_paddleocr(self) -> Any:
        if self._ocr is not None:
            return self._ocr

        os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise RuntimeError(
                "PaddleOCR runtime is not installed. Install paddleocr and paddlepaddle to enable image OCR."
            ) from exc

        self._ocr = build_paddleocr(PaddleOCR, self.config)
        return self._ocr


def build_paddleocr(paddleocr_cls: Any, config: AppConfig) -> Any:
    model_root = config.ocr_model_root / "official_models"
    det_dir = model_root / "PP-OCRv5_mobile_det"
    rec_dir = model_root / "PP-OCRv5_mobile_rec"
    cls_dir = model_root / "PP-LCNet_x1_0_textline_ori"

    attempts = [
        {
            "lang": config.ocr_lang,
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
        },
        {
            "lang": config.ocr_lang,
            "text_detection_model_name": "PP-OCRv5_mobile_det",
            "text_detection_model_dir": str(det_dir),
            "text_recognition_model_name": "PP-OCRv5_mobile_rec",
            "text_recognition_model_dir": str(rec_dir),
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
        },
        {
            "lang": config.ocr_lang,
            "det_model_dir": str(det_dir),
            "rec_model_dir": str(rec_dir),
            "cls_model_dir": str(cls_dir),
            "use_angle_cls": True,
            "use_gpu": False,
            "show_log": False,
        },
        {"lang": config.ocr_lang, "use_angle_cls": True},
        {"lang": config.ocr_lang},
    ]

    last_error: Exception | None = None
    for kwargs in attempts:
        try:
            return paddleocr_cls(**kwargs)
        except TypeError as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error
    return paddleocr_cls()


def run_paddleocr_prediction(ocr: Any, image_path: Path) -> Any:
    if hasattr(ocr, "predict"):
        try:
            return ocr.predict(input=str(image_path))
        except TypeError:
            return ocr.predict(str(image_path))
    if hasattr(ocr, "ocr"):
        try:
            return ocr.ocr(str(image_path), cls=True)
        except TypeError:
            return ocr.ocr(str(image_path))
    raise RuntimeError("Unsupported PaddleOCR object: no ocr() or predict() method found.")


def parse_ocr_lines(raw: Any) -> list[OcrLine]:
    lines: list[OcrLine] = []
    seen: set[tuple[str, float | None]] = set()

    def add_line(text: Any, confidence: Any = None) -> None:
        normalized = str(text).strip()
        if not normalized:
            return
        score = coerce_confidence(confidence)
        key = (normalized, score)
        if key in seen:
            return
        seen.add(key)
        lines.append(OcrLine(normalized, score))

    def walk(obj: Any) -> None:
        if obj is None:
            return

        if hasattr(obj, "json") and callable(obj.json):
            try:
                walk(obj.json)
                return
            except Exception:
                pass

        if hasattr(obj, "to_dict") and callable(obj.to_dict):
            try:
                walk(obj.to_dict())
                return
            except Exception:
                pass

        if isinstance(obj, dict):
            rec_texts = obj.get("rec_texts") or obj.get("texts")
            if isinstance(rec_texts, list):
                rec_scores = obj.get("rec_scores") or obj.get("scores") or []
                for idx, text in enumerate(rec_texts):
                    score = rec_scores[idx] if idx < len(rec_scores) else None
                    add_line(text, score)
                return
            for text_key in ("text", "transcription", "label"):
                if text_key in obj and isinstance(obj[text_key], str):
                    add_line(obj[text_key], obj.get("score") or obj.get("confidence"))
                    return
            for value in obj.values():
                walk(value)
            return

        if isinstance(obj, (list, tuple)):
            if looks_like_v2_line(obj):
                text, score = obj[1][0], obj[1][1] if len(obj[1]) > 1 else None
                add_line(text, score)
                return
            if len(obj) >= 2 and isinstance(obj[0], str) and isinstance(obj[1], (int, float)):
                add_line(obj[0], obj[1])
                return
            for value in obj:
                walk(value)

    walk(raw)
    return lines


def looks_like_v2_line(obj: Any) -> bool:
    return (
        isinstance(obj, (list, tuple))
        and len(obj) >= 2
        and isinstance(obj[1], (list, tuple))
        and len(obj[1]) >= 1
        and isinstance(obj[1][0], str)
    )


def coerce_confidence(value: Any) -> float | None:
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None
