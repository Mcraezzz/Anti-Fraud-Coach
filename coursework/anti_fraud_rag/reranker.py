from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from sentence_transformers import CrossEncoder

from .config import AppConfig


class BgeReranker:
    def __init__(self, config: AppConfig) -> None:
        self.model_path = config.reranker_path
        self.device = resolve_torch_device(config.bge_device)
        self.max_length = config.reranker_max_length
        self._model: CrossEncoder | None = None

    def _load(self) -> CrossEncoder:
        if self._model is None:
            if not Path(self.model_path).exists():
                raise FileNotFoundError(f"Reranker model path not found: {self.model_path}")
            self._model = CrossEncoder(
                str(self.model_path),
                device=self.device,
                max_length=self.max_length,
            )
        return self._model

    def score(self, query: str, passages: list[str]) -> np.ndarray:
        if not passages:
            return np.array([], dtype=np.float32)
        model = self._load()
        pairs = [(query, passage) for passage in passages]
        scores = model.predict(pairs)
        return normalize_reranker_scores(np.asarray(scores, dtype=np.float32))


def normalize_reranker_scores(scores: np.ndarray) -> np.ndarray:
    if scores.size == 0:
        return scores.astype(np.float32)
    if float(scores.min()) >= 0.0 and float(scores.max()) <= 1.0:
        return np.clip(scores, 0.0, 1.0).astype(np.float32)
    scores = 1.0 / (1.0 + np.exp(-scores))
    return np.clip(scores, 0.0, 1.0).astype(np.float32)


def resolve_torch_device(device: str) -> str:
    if device == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda" and not torch.cuda.is_available():
        return "cpu"
    return device
