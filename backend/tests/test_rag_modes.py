"""The lightweight mode must not initialize optional ML runtimes."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.rag_service import Reranker, settings


@pytest.mark.parametrize("enabled", [False, True])
def test_reranker_respects_semantic_mode(monkeypatch, enabled):
    loaded = []
    model = object()

    def load_model(*args, **kwargs):
        loaded.append((args, kwargs))
        return model

    monkeypatch.setattr(settings, "semantic_rag_enabled", enabled)
    monkeypatch.setattr(Path, "exists", lambda _: True)
    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(CrossEncoder=load_model))
    backend = Reranker()
    assert backend.available is enabled
    assert len(loaded) == int(enabled)
    if enabled:
        assert loaded[0][1]["local_files_only"] is True
    else:
        assert "disabled" in backend.error
