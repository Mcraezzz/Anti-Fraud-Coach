from __future__ import annotations

import os
import time
from functools import lru_cache
from pathlib import Path

from app.core.config import settings
from app.services.model_inference_service import get_model_inference_status
from app.services.ocr_service import get_ocr_status


MODEL_DIRS = {
    "文本分类基座": "hfl_chinese-macbert-base",
    "MacBERT 反诈微调模型": "hfl_chinese-macbert-fraud-finetuned-v2",
    "RAG 向量模型": "BAAI_bge-m3",
    "RAG 重排模型": "BAAI_bge-reranker-v2-m3",
    "Qwen 向量模型": "Qwen_Qwen3-Embedding-0.6B",
    "Qwen 生成模型": "Qwen_Qwen3-4B-Instruct-2507",
    "恶意 URL 检测参考": "khagu_malicious-url-detection-models",
    "钓鱼 URL BERT 参考": "ealvaradob_bert-phishing-url",
}

DATASET_DIRS = {
    "电话反诈音频文本数据集": "JimmyMa99_TeleAntiFraud",
    "中文欺诈文本数据集": "ChiFraud",
    "中文安全评测补充集": "zjunlp_ChineseHarm-bench",
}


@lru_cache(maxsize=64)
def _dir_size_cached(path_text: str) -> int:
    path = Path(path_text)
    if not path.exists():
        return 0
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


def _dir_size(path: Path) -> int:
    return _dir_size_cached(str(path))


def _resource_entry(label: str, path: Path, include_size: bool = False) -> dict[str, object]:
    exists = path.exists()
    size = _dir_size(path) if include_size and exists else None
    return {
        "label": label,
        "path": str(path),
        "exists": exists,
        "size_gb": round(size / 1024 / 1024 / 1024, 2) if size is not None else None,
        "size_label": f"{round(size / 1024 / 1024 / 1024, 2)}GB" if size is not None else ("已就绪" if exists else "缺失"),
    }


def get_resource_status() -> dict[str, object]:
    started = time.perf_counter()
    models = [_resource_entry(label, settings.model_root / dirname) for label, dirname in MODEL_DIRS.items()]
    datasets = [_resource_entry(label, settings.dataset_root / dirname) for label, dirname in DATASET_DIRS.items()]
    paddleocr_cache = Path(os.getenv("ANTI_FRAUD_PADDLE_OCR_CACHE", r"D:\CARIC_PaddleOCR_cache"))
    return {
        "resource_root": str(settings.resource_root),
        "models": models,
        "datasets": datasets,
        "mode": "rule + semantic RAG + optional local model inference",
        "rag": {
            "embedding_model": str(settings.rag_embedding_model_path),
            "reranker_model": str(settings.rag_reranker_model_path),
            "index_backend": settings.rag_index_backend,
        },
        "ocr": get_ocr_status(),
        "paddleocr_cache": _resource_entry("PaddleOCR 运行缓存", paddleocr_cache),
        "model_inference": get_model_inference_status(),
        "size_cache": {
            "enabled": True,
            "items": _dir_size_cached.cache_info().currsize,
            "mode": "fast_exists_check",
        },
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
    }
