from __future__ import annotations

import os
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = BACKEND_ROOT / "app"
DATA_DIR = APP_DIR / "data"


class Settings:
    app_name = "Anti-Fraud Coach API"
    resource_root = Path(os.getenv("ANTI_FRAUD_RESOURCE_ROOT", r"D:\CARIC模型&数据集"))
    auth_secret = os.getenv("ANTI_FRAUD_AUTH_SECRET", "anti-fraud-coach-local-demo-secret")
    cors_origins = ["*"]
    semantic_rag_enabled = os.getenv("ANTI_FRAUD_SEMANTIC_RAG", "1") != "0"
    rag_index_backend = os.getenv("ANTI_FRAUD_RAG_INDEX_BACKEND", "auto").lower()
    rag_top_k = int(os.getenv("ANTI_FRAUD_RAG_TOP_K", "4"))
    rag_candidate_k = int(os.getenv("ANTI_FRAUD_RAG_CANDIDATE_K", "8"))
    url_classifier_enabled = os.getenv("ANTI_FRAUD_URL_CLASSIFIER", "1") != "0"
    url_classifier_model_name = os.getenv("ANTI_FRAUD_URL_CLASSIFIER_MODEL", "decision_tree_current.pkl")
    url_classifier_scaler_name = os.getenv("ANTI_FRAUD_URL_CLASSIFIER_SCALER", "scaler_current.pkl")
    url_classifier_label_encoder_name = os.getenv("ANTI_FRAUD_URL_CLASSIFIER_LABEL_ENCODER", "label_encoder_current.pkl")
    macbert_enabled = os.getenv("ANTI_FRAUD_MACBERT_ENABLED", "1") != "0"
    macbert_fraud_classifier_enabled = os.getenv("ANTI_FRAUD_MACBERT_FRAUD_CLASSIFIER", "1") != "0"
    ocr_preload = os.getenv("ANTI_FRAUD_OCR_PRELOAD", "1") == "1"
    ocr_fast_analysis = os.getenv("ANTI_FRAUD_OCR_FAST_ANALYSIS", "1") == "1"
    qwen_enabled = os.getenv("ANTI_FRAUD_QWEN_ENABLED", "0") == "1"
    qwen_preload = os.getenv("ANTI_FRAUD_QWEN_PRELOAD", "0") == "1"
    qwen_max_new_tokens = int(os.getenv("ANTI_FRAUD_QWEN_MAX_NEW_TOKENS", "180"))

    @property
    def model_root(self) -> Path:
        return self.resource_root / "models"

    @property
    def dataset_root(self) -> Path:
        return self.resource_root / "datasets"

    @property
    def rag_embedding_model_path(self) -> Path:
        return self.model_root / "BAAI_bge-m3"

    @property
    def rag_reranker_model_path(self) -> Path:
        return self.model_root / "BAAI_bge-reranker-v2-m3"

    @property
    def macbert_model_path(self) -> Path:
        return self.model_root / "hfl_chinese-macbert-base"

    @property
    def macbert_fraud_model_path(self) -> Path:
        preferred = self.model_root / "hfl_chinese-macbert-fraud-finetuned-v2"
        if preferred.exists():
            return preferred
        return self.model_root / "hfl_chinese-macbert-fraud-finetuned"

    @property
    def qwen_model_path(self) -> Path:
        return self.model_root / "Qwen_Qwen3-4B-Instruct-2507"

    @property
    def url_classifier_model_path(self) -> Path:
        return self.model_root / "khagu_malicious-url-detection-models"

    @property
    def phishing_url_bert_model_path(self) -> Path:
        return self.model_root / "ealvaradob_bert-phishing-url"


settings = Settings()
