from __future__ import annotations

import re
import os
import tempfile
import hashlib
import copy
import io
import importlib.util
import time
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from app.core.config import settings

PADDLE_OCR_STORAGE = settings.model_root / "PaddleOCR"
PADDLE_OCR_CACHE = Path(os.getenv("ANTI_FRAUD_PADDLE_OCR_CACHE", r"D:\CARIC_PaddleOCR_cache"))
try:
    PADDLE_OCR_STORAGE.mkdir(parents=True, exist_ok=True)
    PADDLE_OCR_CACHE.mkdir(parents=True, exist_ok=True)
except OSError:
    PADDLE_OCR_CACHE = PADDLE_OCR_STORAGE
os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(PADDLE_OCR_CACHE))
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_enable_pir_api", "0")
os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "0")
os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("MKL_NUM_THREADS", "4")

OCR_MAX_WIDTH = int(os.getenv("ANTI_FRAUD_OCR_MAX_WIDTH", "1080"))
OCR_MAX_HEIGHT = int(os.getenv("ANTI_FRAUD_OCR_MAX_HEIGHT", "1920"))
OCR_CACHE_SIZE = int(os.getenv("ANTI_FRAUD_OCR_CACHE_SIZE", "24"))
OCR_USE_ANGLE_CLS = os.getenv("ANTI_FRAUD_OCR_USE_ANGLE_CLS", "0") == "1"
OCR_DET_MODEL = os.getenv("ANTI_FRAUD_OCR_DET_MODEL", "PP-OCRv5_mobile_det")
OCR_REC_MODEL = os.getenv("ANTI_FRAUD_OCR_REC_MODEL", "PP-OCRv5_mobile_rec")
OCR_DET_LIMIT_SIDE_LEN = int(os.getenv("ANTI_FRAUD_OCR_DET_LIMIT_SIDE_LEN", "960"))
OCR_REC_BATCH_SIZE = int(os.getenv("ANTI_FRAUD_OCR_REC_BATCH_SIZE", "8"))
_OCR_RESULT_CACHE: OrderedDict[str, dict[str, Any]] = OrderedDict()

TIMESTAMP_RE = re.compile(
    r"^(?:\d{1,2}:\d{2}|(?:上午|下午|晚上|凌晨)?\s*\d{1,2}:\d{2}|"
    r"(?:今天|昨天|前天)|\d{4}[/-]\d{1,2}[/-]\d{1,2})$"
)


SENSITIVE_PATTERNS = [
    ("verification_code", re.compile(r"(?P<prefix>验证码|校验码|动态码|短信码|登录码)(?:[:：\s]*)(?P<value>\d{4,8})")),
    ("phone", re.compile(r"(?<!\d)(?:\+?86[-\s]?)?(1[3-9]\d{9})(?!\d)")),
    ("id_card", re.compile(r"(?<!\d)(\d{6}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])(?!\d)")),
    ("bank_card", re.compile(r"(?<!\d)(\d{4}[-\s]?\d{4}[-\s]?\d{4}(?:[-\s]?\d{1,7})?)(?!\d)")),
    ("email", re.compile(r"([a-zA-Z0-9_.+-]{2,})@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")),
    ("password_hint", re.compile(r"(?P<prefix>密码|支付密码|银行卡密码|登录密码)(?:[:：\s]*)(?P<value>[A-Za-z0-9_@#.$%^-]{4,})")),
]


@dataclass
class OcrRegion:
    index: int
    text: str
    confidence: float
    box: list[list[float]]

    @property
    def bbox(self) -> dict[str, float]:
        xs = [point[0] for point in self.box]
        ys = [point[1] for point in self.box]
        return {
            "x_min": min(xs),
            "y_min": min(ys),
            "x_max": max(xs),
            "y_max": max(ys),
        }

    @property
    def center_x(self) -> float:
        bbox = self.bbox
        return (bbox["x_min"] + bbox["x_max"]) / 2

    @property
    def center_y(self) -> float:
        bbox = self.bbox
        return (bbox["y_min"] + bbox["y_max"]) / 2


def _mask_value(kind: str, value: str, prefix: str = "") -> str:
    compact = re.sub(r"[-\s]", "", value)
    if kind == "verification_code":
        return f"{prefix} ******"
    if kind == "phone":
        return f"{compact[:3]}****{compact[-4:]}"
    if kind == "id_card":
        return f"{compact[:6]}********{compact[-4:]}"
    if kind == "bank_card":
        return f"{compact[:4]} **** **** {compact[-4:]}"
    if kind == "email":
        name, domain = value.split("@", 1)
        return f"{name[:2]}***@{domain}"
    if kind == "password_hint":
        return f"{prefix} ******"
    return "***"


def mask_sensitive_text(text: str) -> tuple[str, list[dict[str, Any]]]:
    entities: list[dict[str, Any]] = []
    replacements: list[tuple[int, int, str, str]] = []

    for kind, pattern in SENSITIVE_PATTERNS:
        for match in pattern.finditer(text):
            if any(not (match.end() <= start or match.start() >= end) for start, end, _, _ in replacements):
                continue
            if kind in {"verification_code", "password_hint"}:
                prefix = match.group("prefix")
                value = match.group("value")
                masked = _mask_value(kind, value, prefix)
                start, end = match.span()
            elif kind == "email":
                value = match.group(0)
                masked = _mask_value(kind, value)
                start, end = match.span()
            else:
                value = match.group(1)
                masked = _mask_value(kind, value)
                start, end = match.span(1)
            replacements.append((start, end, masked, kind))

    if not replacements:
        return text, []

    replacements.sort(key=lambda item: item[0])
    chunks: list[str] = []
    cursor = 0
    offset = 0
    for start, end, masked, kind in replacements:
        chunks.append(text[cursor:start])
        chunks.append(masked)
        entities.append(
            {
                "type": kind,
                "start": start + offset,
                "end": start + offset + len(masked),
                "masked_value": masked,
            }
        )
        offset += len(masked) - (end - start)
        cursor = end
    chunks.append(text[cursor:])
    return "".join(chunks), entities


def _normalize_box(box: Any) -> list[list[float]]:
    if box is None:
        return [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]
    to_list = getattr(box, "tolist", None)
    points = to_list() if callable(to_list) else box
    try:
        if len(points) == 0:
            return [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]
    except TypeError:
        return [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]
    return [[float(point[0]), float(point[1])] for point in points]


def _result_dict(result: Any) -> dict[str, Any] | None:
    if isinstance(result, dict):
        nested = result.get("res")
        return nested if isinstance(nested, dict) else result

    res = getattr(result, "res", None)
    if isinstance(res, dict):
        return res

    to_dict = getattr(result, "to_dict", None)
    if callable(to_dict):
        try:
            data = to_dict()
        except Exception:
            return None
        if isinstance(data, dict):
            nested = data.get("res")
            return nested if isinstance(nested, dict) else data
    return None


def _first_present(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is None:
            continue
        try:
            if len(value) == 0:
                continue
        except TypeError:
            pass
        return value
    return []


def _rows_to_regions(rows: list[Any]) -> list[OcrRegion]:
    regions: list[OcrRegion] = []

    for row in rows:
        parsed = _parse_ocr_line(row)
        if not parsed:
            continue
        box, text, confidence = parsed
        if not text.strip():
            continue
        regions.append(
            OcrRegion(
                index=len(regions),
                text=text.strip(),
                confidence=float(confidence),
                box=_normalize_box(box),
            )
        )
    return regions


def _parse_paddle_result(result: Any) -> list[OcrRegion]:
    result_data = _result_dict(result)
    if result_data is not None:
        texts = _first_present(result_data, "rec_texts", "texts")
        scores = _first_present(result_data, "rec_scores", "scores")
        boxes = _first_present(result_data, "rec_polys", "dt_polys", "boxes")
        rows = [
            (
                boxes[index] if index < len(boxes) else [],
                (text, scores[index] if index < len(scores) else 0.0),
            )
            for index, text in enumerate(texts)
        ]
        return _rows_to_regions(rows)

    if isinstance(result, list):
        if result and isinstance(result[0], list) and result[0] and _looks_like_ocr_line(result[0][0]):
            return _rows_to_regions(result[0])
        if result and _looks_like_ocr_line(result[0]):
            return _rows_to_regions(result)

        regions: list[OcrRegion] = []
        for page_result in result:
            for region in _parse_paddle_result(page_result):
                region.index = len(regions)
                regions.append(region)
        return regions

    return []


def _looks_like_ocr_line(value: Any) -> bool:
    return isinstance(value, (list, tuple)) and len(value) >= 2


def _parse_ocr_line(row: Any) -> tuple[Any, str, float] | None:
    if not isinstance(row, (list, tuple)) or len(row) < 2:
        return None
    box = row[0]
    payload = row[1]
    if isinstance(payload, (list, tuple)) and payload:
        text = str(payload[0])
        confidence = float(payload[1]) if len(payload) > 1 else 0.0
        return box, text, confidence
    if isinstance(payload, str):
        confidence = float(row[2]) if len(row) > 2 and isinstance(row[2], (int, float)) else 0.0
        return box, payload, confidence
    return None


@lru_cache(maxsize=1)
def _paddle_ocr() -> Any:
    from paddleocr import PaddleOCR

    init_attempts = [
        {
            "lang": "ch",
            "ocr_version": "PP-OCRv5",
            "text_detection_model_name": OCR_DET_MODEL,
            "text_recognition_model_name": OCR_REC_MODEL,
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": OCR_USE_ANGLE_CLS,
            "text_det_limit_side_len": OCR_DET_LIMIT_SIDE_LEN,
            "text_det_limit_type": "max",
            "text_recognition_batch_size": OCR_REC_BATCH_SIZE,
        },
        {"use_angle_cls": OCR_USE_ANGLE_CLS, "lang": "ch", "show_log": False},
        {"use_angle_cls": OCR_USE_ANGLE_CLS, "lang": "ch"},
    ]
    last_error: Exception | None = None
    for kwargs in init_attempts:
        try:
            return PaddleOCR(**kwargs)
        except Exception as exc:
            last_error = exc
    if last_error:
        raise last_error
    return PaddleOCR(lang="ch")


def _run_paddle_ocr(image_path: Path) -> Any:
    engine = _paddle_ocr()
    ocr_method = getattr(engine, "ocr", None)
    if callable(ocr_method):
        try:
            return ocr_method(str(image_path), cls=OCR_USE_ANGLE_CLS)
        except TypeError:
            return ocr_method(str(image_path))

    predict_method = getattr(engine, "predict", None)
    if callable(predict_method):
        try:
            return predict_method(input=str(image_path))
        except TypeError:
            return predict_method(str(image_path))

    raise RuntimeError("PaddleOCR engine does not expose ocr() or predict().")


def preload_ocr_engine() -> dict[str, Any]:
    started = time.perf_counter()
    engine = _paddle_ocr()
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        image_path = Path(tmp.name)
    try:
        Image.new("RGB", (320, 120), "white").save(image_path, format="JPEG", quality=85)
        try:
            _run_paddle_ocr(image_path)
        except Exception:
            pass
    finally:
        image_path.unlink(missing_ok=True)
    return {
        "status": "ok",
        "loaded": True,
        "engine": engine.__class__.__name__,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
    }


@lru_cache(maxsize=1)
def ocr_available() -> bool:
    return importlib.util.find_spec("paddleocr") is not None and importlib.util.find_spec("paddle") is not None


def get_ocr_status() -> dict[str, Any]:
    return {
        "available": ocr_available(),
        "engine": "PaddleOCR",
        "cache_dir": str(PADDLE_OCR_CACHE),
        "storage_dir": str(PADDLE_OCR_STORAGE),
        "image_max_width": OCR_MAX_WIDTH,
        "image_max_height": OCR_MAX_HEIGHT,
        "result_cache_size": OCR_CACHE_SIZE,
        "angle_cls_enabled": OCR_USE_ANGLE_CLS,
        "det_model": OCR_DET_MODEL,
        "rec_model": OCR_REC_MODEL,
        "det_limit_side_len": OCR_DET_LIMIT_SIDE_LEN,
        "preload_enabled": settings.ocr_preload,
        "loaded": _paddle_ocr.cache_info().currsize > 0,
        "features": ["text_regions", "timeline_restore", "sensitive_masking"],
    }


def _cache_get(cache_key: str) -> dict[str, Any] | None:
    cached = _OCR_RESULT_CACHE.get(cache_key)
    if cached is None:
        return None
    _OCR_RESULT_CACHE.move_to_end(cache_key)
    return copy.deepcopy(cached)


def _cache_set(cache_key: str, value: dict[str, Any]) -> None:
    if OCR_CACHE_SIZE <= 0:
        return
    _OCR_RESULT_CACHE[cache_key] = copy.deepcopy(value)
    _OCR_RESULT_CACHE.move_to_end(cache_key)
    while len(_OCR_RESULT_CACHE) > OCR_CACHE_SIZE:
        _OCR_RESULT_CACHE.popitem(last=False)


def _write_optimized_image(image_bytes: bytes, image_path: Path) -> dict[str, int]:
    with Image.open(io.BytesIO(image_bytes)) as image:
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")
        original_width, original_height = image.size
        scale = min(1.0, OCR_MAX_WIDTH / max(original_width, 1), OCR_MAX_HEIGHT / max(original_height, 1))
        if scale < 1.0:
            target_size = (
                max(1, int(original_width * scale)),
                max(1, int(original_height * scale)),
            )
            image = image.resize(target_size, Image.Resampling.LANCZOS)
        width, height = image.size
        image.save(image_path, format="JPEG", quality=88)
        return {
            "width": width,
            "height": height,
            "original_width": original_width,
            "original_height": original_height,
        }


def extract_regions_from_image(image_bytes: bytes) -> tuple[list[OcrRegion], dict[str, int]]:
    if not ocr_available():
        raise RuntimeError("PaddleOCR is not installed. Run: python -m pip install paddleocr paddlepaddle")

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        image_path = Path(tmp.name)

    try:
        image_size = _write_optimized_image(image_bytes, image_path)
        result = _run_paddle_ocr(image_path)
        return _parse_paddle_result(result), image_size
    finally:
        image_path.unlink(missing_ok=True)


def _guess_speaker(region: OcrRegion, image_width: int) -> str:
    if image_width <= 0:
        return "unknown"
    ratio = region.center_x / image_width
    if ratio < 0.42:
        return "other"
    if ratio > 0.58:
        return "self"
    return "system"


def restore_chat_timeline(regions: list[OcrRegion], image_size: dict[str, int]) -> list[dict[str, Any]]:
    if not regions:
        return []

    width = image_size.get("width", 0)
    height = max(image_size.get("height", 0), 1)
    sorted_regions = sorted(regions, key=lambda item: (item.bbox["y_min"], item.bbox["x_min"]))
    max_gap = max(24.0, height * 0.028)
    messages: list[dict[str, Any]] = []
    current_timestamp = ""

    for region in sorted_regions:
        text = region.text.strip()
        if not text:
            continue
        if TIMESTAMP_RE.match(text):
            current_timestamp = text
            continue

        speaker = _guess_speaker(region, width)
        bbox = region.bbox
        if (
            messages
            and messages[-1]["speaker"] == speaker
            and bbox["y_min"] - messages[-1]["bbox"]["y_max"] <= max_gap
        ):
            messages[-1]["text"] = f"{messages[-1]['text']} {text}"
            messages[-1]["region_indices"].append(region.index)
            messages[-1]["confidence"] = round((messages[-1]["confidence"] + region.confidence) / 2, 4)
            messages[-1]["bbox"]["x_min"] = min(messages[-1]["bbox"]["x_min"], bbox["x_min"])
            messages[-1]["bbox"]["y_min"] = min(messages[-1]["bbox"]["y_min"], bbox["y_min"])
            messages[-1]["bbox"]["x_max"] = max(messages[-1]["bbox"]["x_max"], bbox["x_max"])
            messages[-1]["bbox"]["y_max"] = max(messages[-1]["bbox"]["y_max"], bbox["y_max"])
            continue

        messages.append(
            {
                "order": len(messages) + 1,
                "speaker": speaker,
                "timestamp": current_timestamp,
                "text": text,
                "confidence": round(region.confidence, 4),
                "bbox": bbox.copy(),
                "region_indices": [region.index],
            }
        )

    for message in messages:
        masked, entities = mask_sensitive_text(message["text"])
        message["text"] = masked
        message["sensitive_entities"] = entities
    return messages


def process_chat_screenshot(image_bytes: bytes) -> dict[str, Any]:
    started = time.perf_counter()
    cache_key = f"{hashlib.sha256(image_bytes).hexdigest()}:{OCR_MAX_WIDTH}x{OCR_MAX_HEIGHT}:angle={int(OCR_USE_ANGLE_CLS)}"
    cached = _cache_get(cache_key)
    if cached is not None:
        cached["cache_hit"] = True
        cached["processing_ms"] = 0
        return cached

    regions, image_size = extract_regions_from_image(image_bytes)
    messages = restore_chat_timeline(regions, image_size)
    if messages:
        sanitized_text = "\n".join(message["text"] for message in messages)
        entities: list[dict[str, Any]] = []
        cursor = 0
        for message in messages:
            for entity in message.get("sensitive_entities", []):
                adjusted = entity.copy()
                adjusted["start"] += cursor
                adjusted["end"] += cursor
                entities.append(adjusted)
            cursor += len(message["text"]) + 1
    else:
        raw_text = "\n".join(region.text for region in regions)
        sanitized_text, entities = mask_sensitive_text(raw_text)

    sanitized_regions = []
    for region in regions:
        masked_text, region_entities = mask_sensitive_text(region.text)
        sanitized_regions.append(
            {
                "index": region.index,
                "text": masked_text,
                "confidence": round(region.confidence, 4),
                "box": region.box,
                "bbox": region.bbox,
                "sensitive_entities": region_entities,
            }
        )

    result = {
        "ocr_available": True,
        "engine": "PaddleOCR",
        "image_size": image_size,
        "regions": sanitized_regions,
        "messages": messages,
        "sanitized_text": sanitized_text,
        "sensitive_entities": entities,
        "cache_hit": False,
        "processing_ms": round((time.perf_counter() - started) * 1000, 2),
    }
    _cache_set(cache_key, result)
    return result
