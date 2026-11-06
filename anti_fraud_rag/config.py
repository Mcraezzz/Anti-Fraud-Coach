from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    datasets_dir: Path
    models_dir: Path
    bge_m3_path: Path
    reranker_path: Path
    ocr_model_root: Path
    index_dir: Path
    qwen_model: str
    qwen_base_url: str
    qwen_timeout_seconds: float
    dense_batch_size: int
    dense_max_seq_length: int
    dense_limit: int
    bge_device: str
    use_reranker: bool
    reranker_top_n: int
    reranker_weight: float
    reranker_max_length: int
    fusion_alpha: float
    fusion_beta: float
    fusion_gamma: float
    fusion_delta: float
    use_ocr: bool
    ocr_lang: str
    max_cases_per_source: int = 1200
    max_iocs_per_source: int = 200000

    @classmethod
    def from_env(cls) -> "AppConfig":
        root = Path.cwd()
        datasets_dir = Path(os.getenv("DATASETS_DIR", r"D:\CARIC模型&数据集\datasets"))
        models_dir = Path(os.getenv("MODELS_DIR", r"D:\CARIC模型&数据集\models"))
        return cls(
            datasets_dir=datasets_dir,
            models_dir=models_dir,
            bge_m3_path=Path(os.getenv("BGE_M3_PATH", str(models_dir / "BAAI_bge-m3"))),
            reranker_path=Path(
                os.getenv("RERANKER_PATH", str(models_dir / "BAAI_bge-reranker-v2-m3"))
            ),
            ocr_model_root=Path(os.getenv("OCR_MODEL_ROOT", str(models_dir / "PaddleOCR"))),
            index_dir=Path(os.getenv("RAG_INDEX_DIR", str(root / "storage" / "rag_index"))),
            qwen_model=os.getenv("QWEN_MODEL", "qwen3.7-plus"),
            qwen_base_url=os.getenv(
                "DASHSCOPE_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
            qwen_timeout_seconds=float(os.getenv("QWEN_TIMEOUT_SECONDS", "30")),
            dense_batch_size=int(os.getenv("BGE_BATCH_SIZE", "8")),
            dense_max_seq_length=int(os.getenv("BGE_MAX_SEQ_LENGTH", "512")),
            dense_limit=int(os.getenv("BGE_DENSE_LIMIT", "0")),
            bge_device=os.getenv("BGE_DEVICE", "auto"),
            use_reranker=os.getenv("USE_RERANKER", "true").lower() in {"1", "true", "yes", "on"},
            reranker_top_n=int(os.getenv("RERANKER_TOP_N", "12")),
            reranker_weight=float(os.getenv("RERANKER_WEIGHT", "0.30")),
            reranker_max_length=int(os.getenv("RERANKER_MAX_LENGTH", "512")),
            fusion_alpha=float(os.getenv("FUSION_ALPHA", "0.35")),
            fusion_beta=float(os.getenv("FUSION_BETA", "0.35")),
            fusion_gamma=float(os.getenv("FUSION_GAMMA", "0.15")),
            fusion_delta=float(os.getenv("FUSION_DELTA", "0.15")),
            use_ocr=os.getenv("USE_OCR", "true").lower() in {"1", "true", "yes", "on"},
            ocr_lang=os.getenv("OCR_LANG", "ch"),
        )

    @property
    def qwen_api_key(self) -> str | None:
        return os.getenv("DASHSCOPE_API_KEY")
