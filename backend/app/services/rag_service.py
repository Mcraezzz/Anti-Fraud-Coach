from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from app.core.config import DATA_DIR, settings


KNOWLEDGE_FILE = DATA_DIR / "knowledge_base.json"
CASE_FILE = DATA_DIR / "fraud_cases.json"
VERSION_FILE = DATA_DIR / "knowledge_versions.json"
INDEX_DIR = DATA_DIR / "rag_index"


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _tokens(text: str) -> set[str]:
    lower = text.lower()
    words = set(re.findall(r"[a-zA-Z0-9_]{2,}", lower))
    chars = [char for char in lower if "\u4e00" <= char <= "\u9fff"]
    bigrams = {chars[i] + chars[i + 1] for i in range(len(chars) - 1)}
    trigrams = {chars[i] + chars[i + 1] + chars[i + 2] for i in range(len(chars) - 2)}
    return words | set(chars) | bigrams | trigrams


def _knowledge_checksum() -> str:
    hasher = hashlib.sha256()
    for path in (KNOWLEDGE_FILE, CASE_FILE, VERSION_FILE):
        if path.exists():
            hasher.update(path.read_bytes())
    return hasher.hexdigest()[:16]


def get_knowledge_version() -> dict[str, Any]:
    meta = _read_json(VERSION_FILE, {})
    return {
        "active_version": meta.get("active_version", "local-dev"),
        "released_at": meta.get("released_at", ""),
        "maintainer": meta.get("maintainer", "Anti-Fraud Coach 项目组"),
        "description": meta.get("description", "本地反诈知识库"),
        "checksum": _knowledge_checksum(),
        "changelog": meta.get("changelog", []),
    }


@dataclass(frozen=True)
class RagDocument:
    doc_id: str
    title: str
    category: str
    content: str
    keywords: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    source_type: str = "knowledge"
    source: str = "反诈知识库"
    version: str = ""
    updated_at: str = ""
    case_id: str = ""
    risk_points: list[str] = field(default_factory=list)
    handling: str = ""

    @property
    def text(self) -> str:
        parts = [
            self.title,
            self.category,
            " ".join(self.keywords),
            self.content,
            " ".join(self.risk_points),
            self.handling,
            " ".join(self.actions),
        ]
        return "。".join(part for part in parts if part)


def _slug(text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    ascii_part = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    return f"{ascii_part or 'doc'}_{digest}"


def _load_documents() -> list[RagDocument]:
    version = get_knowledge_version()
    active_version = version["active_version"]
    released_at = version["released_at"]
    docs: list[RagDocument] = []

    for index, item in enumerate(_read_json(KNOWLEDGE_FILE, []), start=1):
        doc_id = item.get("doc_id") or f"kb_{index:03d}_{_slug(item['title'])}"
        docs.append(
            RagDocument(
                doc_id=doc_id,
                title=item["title"],
                category=item["category"],
                content=item["content"],
                keywords=list(item.get("keywords", [])),
                actions=list(item.get("actions", [])),
                source_type="knowledge",
                source=item.get("source", "反诈知识库"),
                version=item.get("version", active_version),
                updated_at=item.get("updated_at", released_at),
            )
        )

    for item in _read_json(CASE_FILE, []):
        case_id = item["case_id"]
        risk_points = list(item.get("risk_points", []))
        handling = item.get("handling", "")
        docs.append(
            RagDocument(
                doc_id=f"case_{case_id}",
                title=item["title"],
                category=item["category"],
                content=item["scene"],
                keywords=risk_points,
                actions=[handling] if handling else [],
                source_type="case",
                source=item.get("source", "案例库"),
                version=item.get("version", active_version),
                updated_at=item.get("updated_at", released_at),
                case_id=case_id,
                risk_points=risk_points,
                handling=handling,
            )
        )
    return docs


def _lexical_score(question: str, doc: RagDocument) -> float:
    q = _tokens(question)
    d = _tokens(doc.text)
    if not q or not d:
        return 0.0
    overlap = len(q & d) / max(len(q), 1)
    keyword_bonus = sum(0.12 for keyword in doc.keywords if keyword and keyword in question)
    category_bonus = 0.15 if doc.category in question else 0.0
    title_bonus = 0.08 if any(token in _tokens(doc.title) for token in q) else 0.0
    return min(1.0, overlap + keyword_bonus + category_bonus + title_bonus)


class EmbeddingBackend:
    def __init__(self) -> None:
        self.model: Any | None = None
        self.name = "lexical"
        self.error = ""
        if not settings.semantic_rag_enabled:
            self.error = "semantic rag disabled by ANTI_FRAUD_SEMANTIC_RAG=0"
            return

        model_path = settings.rag_embedding_model_path
        if not model_path.exists():
            self.error = f"embedding model not found: {model_path}"
            return

        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(
                str(model_path),
                trust_remote_code=True,
                local_files_only=True,
            )
            self.name = "BGE-M3"
        except Exception as exc:  # pragma: no cover - depends on optional ML runtime
            self.model = None
            self.error = f"semantic embedding unavailable: {exc}"

    @property
    def available(self) -> bool:
        return self.model is not None

    def encode(self, texts: list[str]) -> np.ndarray | None:
        if not self.model:
            return None
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return np.asarray(embeddings, dtype="float32")


class VectorIndex:
    def __init__(self, docs: list[RagDocument], embeddings: np.ndarray | None) -> None:
        self.docs = docs
        self.embeddings = embeddings
        self.backend = "lexical"
        self.error = ""
        self._faiss_index: Any | None = None
        self._chroma_collection: Any | None = None

        if embeddings is None or len(docs) == 0:
            return

        requested = settings.rag_index_backend
        if requested in {"auto", "faiss"} and self._try_faiss(embeddings):
            return
        if requested in {"auto", "chroma"} and self._try_chroma(docs, embeddings):
            return

        self.backend = "numpy"
        self.error = self.error or "FAISS/Chroma unavailable; using in-memory numpy similarity"

    def _try_faiss(self, embeddings: np.ndarray) -> bool:
        try:
            import faiss

            dim = embeddings.shape[1]
            index = faiss.IndexFlatIP(dim)
            index.add(embeddings)
            self._faiss_index = index
            self.backend = "faiss"
            return True
        except Exception as exc:  # pragma: no cover - depends on optional ML runtime
            self.error = f"faiss unavailable: {exc}"
            return False

    def _try_chroma(self, docs: list[RagDocument], embeddings: np.ndarray) -> bool:
        try:
            import chromadb

            INDEX_DIR.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(INDEX_DIR / "chroma"))
            collection = client.get_or_create_collection("anti_fraud_knowledge")
            ids = [doc.doc_id for doc in docs]
            metadatas = [
                {
                    "title": doc.title,
                    "category": doc.category,
                    "source_type": doc.source_type,
                    "version": doc.version,
                }
                for doc in docs
            ]
            collection.upsert(
                ids=ids,
                embeddings=embeddings.tolist(),
                metadatas=metadatas,
                documents=[doc.text for doc in docs],
            )
            self._chroma_collection = collection
            self.backend = "chroma"
            return True
        except Exception as exc:  # pragma: no cover - depends on optional ML runtime
            self.error = f"chroma unavailable: {exc}"
            return False

    def search(self, query_embedding: np.ndarray | None, top_k: int) -> list[tuple[int, float]]:
        if query_embedding is None or self.embeddings is None:
            return []

        query = np.asarray(query_embedding, dtype="float32")
        if query.ndim == 1:
            query = query.reshape(1, -1)

        if self.backend == "faiss" and self._faiss_index is not None:
            scores, indices = self._faiss_index.search(query, min(top_k, len(self.docs)))
            return [(int(idx), float(score)) for idx, score in zip(indices[0], scores[0]) if idx >= 0]

        if self.backend == "chroma" and self._chroma_collection is not None:
            result = self._chroma_collection.query(
                query_embeddings=query.tolist(),
                n_results=min(top_k, len(self.docs)),
            )
            ids = result.get("ids", [[]])[0]
            distances = result.get("distances", [[]])[0]
            id_to_index = {doc.doc_id: index for index, doc in enumerate(self.docs)}
            hits = []
            for doc_id, distance in zip(ids, distances):
                if doc_id in id_to_index:
                    hits.append((id_to_index[doc_id], float(1.0 - distance)))
            return hits

        scores = np.dot(self.embeddings, query[0])
        order = np.argsort(-scores)[:top_k]
        return [(int(index), float(scores[index])) for index in order]


class Reranker:
    def __init__(self) -> None:
        self.model: Any | None = None
        self.name = "lexical-semantic"
        self.error = ""
        if not settings.semantic_rag_enabled:
            self.error = "semantic rag disabled by ANTI_FRAUD_SEMANTIC_RAG=0"
            return
        model_path = settings.rag_reranker_model_path
        if not model_path.exists():
            self.error = f"reranker model not found: {model_path}"
            return

        try:
            from sentence_transformers import CrossEncoder

            self.model = CrossEncoder(
                str(model_path),
                trust_remote_code=True,
                local_files_only=True,
            )
            self.name = "BGE-reranker-v2-m3"
        except Exception as exc:  # pragma: no cover - depends on optional ML runtime
            self.model = None
            self.error = f"reranker unavailable: {exc}"

    @property
    def available(self) -> bool:
        return self.model is not None

    def score(self, question: str, docs: list[RagDocument]) -> list[float] | None:
        if not self.model or not docs:
            return None
        pairs = [(question, doc.text) for doc in docs]
        scores = self.model.predict(pairs)
        return [float(score) for score in scores]


def _normalize_scores(scores: list[float]) -> list[float]:
    if not scores:
        return []
    low = min(scores)
    high = max(scores)
    if math.isclose(low, high):
        return [0.5 for _ in scores]
    return [(score - low) / (high - low) for score in scores]


class RagEngine:
    def __init__(self) -> None:
        self.docs = _load_documents()
        self.version = get_knowledge_version()
        self.embedding = EmbeddingBackend()
        self.embeddings = self.embedding.encode([doc.text for doc in self.docs])
        self.index = VectorIndex(self.docs, self.embeddings)
        self.reranker = Reranker()

    def retrieve(self, question: str, top_k: int | None = None) -> list[dict[str, Any]]:
        top_k = top_k or settings.rag_top_k
        candidate_k = max(settings.rag_candidate_k, top_k)
        query_embedding = self.embedding.encode([question]) if self.embedding.available else None
        if query_embedding is not None:
            query_embedding = query_embedding[0]

        candidates: dict[int, dict[str, Any]] = {}
        for index, semantic_score in self.index.search(query_embedding, candidate_k):
            candidates[index] = {
                "doc": self.docs[index],
                "semantic_score": max(0.0, semantic_score),
            }

        lexical_ranked = sorted(
            ((index, _lexical_score(question, doc)) for index, doc in enumerate(self.docs)),
            key=lambda item: item[1],
            reverse=True,
        )
        for index, lexical_score in lexical_ranked[:candidate_k]:
            if lexical_score <= 0:
                continue
            candidates.setdefault(index, {"doc": self.docs[index], "semantic_score": 0.0})
            candidates[index]["lexical_score"] = lexical_score

        docs = [item["doc"] for item in candidates.values()]
        rerank_scores = self.reranker.score(question, docs)
        rerank_norm = _normalize_scores(rerank_scores or [])

        results: list[dict[str, Any]] = []
        for pos, (index, item) in enumerate(candidates.items()):
            doc = item["doc"]
            lexical_score = item.get("lexical_score", _lexical_score(question, doc))
            semantic_score = item.get("semantic_score", 0.0)
            rerank_score = rerank_norm[pos] if rerank_norm else 0.0
            if self.reranker.available:
                score = 0.68 * rerank_score + 0.22 * semantic_score + 0.10 * lexical_score
            elif self.embedding.available:
                score = 0.62 * semantic_score + 0.38 * lexical_score
            else:
                score = lexical_score
            matched_keywords = [keyword for keyword in doc.keywords if keyword and keyword in question]
            results.append(
                {
                    "doc": doc,
                    "score": round(float(score), 4),
                    "semantic_score": round(float(semantic_score), 4),
                    "lexical_score": round(float(lexical_score), 4),
                    "rerank_score": round(float(rerank_score), 4),
                    "matched_keywords": matched_keywords,
                }
            )

        ranked = sorted(results, key=lambda item: item["score"], reverse=True)
        return [item for item in ranked[:top_k] if item["score"] > 0]

    @property
    def retrieval_method(self) -> str:
        parts = []
        if self.embedding.available:
            parts.append("BGE-M3")
            parts.append(self.index.backend)
        else:
            parts.append("lexical")
        if self.reranker.available:
            parts.append("reranker")
        return "+".join(parts)

    def status(self) -> dict[str, Any]:
        return {
            "knowledge_version": self.version,
            "document_count": len([doc for doc in self.docs if doc.source_type == "knowledge"]),
            "case_count": len([doc for doc in self.docs if doc.source_type == "case"]),
            "embedding": {
                "enabled": settings.semantic_rag_enabled,
                "available": self.embedding.available,
                "model": str(settings.rag_embedding_model_path),
                "backend": self.embedding.name,
                "error": self.embedding.error,
            },
            "index": {
                "backend": self.index.backend,
                "requested_backend": settings.rag_index_backend,
                "path": str(INDEX_DIR),
                "error": self.index.error,
            },
            "reranker": {
                "available": self.reranker.available,
                "model": str(settings.rag_reranker_model_path),
                "backend": self.reranker.name,
                "error": self.reranker.error,
            },
            "retrieval_method": self.retrieval_method,
        }


@lru_cache(maxsize=1)
def _engine() -> RagEngine:
    return RagEngine()


def preload_rag_engine() -> dict[str, Any]:
    engine = _engine()
    engine.retrieve("兼职保证金 风险识别", top_k=1)
    status = engine.status()
    return {
        "status": "ok",
        "loaded": True,
        "retrieval_method": status["retrieval_method"],
        "knowledge_version": status["knowledge_version"],
    }


def reset_rag_cache() -> None:
    _engine.cache_clear()


def _reference_payload(item: dict[str, Any]) -> dict[str, Any]:
    doc: RagDocument = item["doc"]
    return {
        "doc_id": doc.doc_id,
        "title": doc.title,
        "category": doc.category,
        "score": item["score"],
        "content": doc.content,
        "source_type": doc.source_type,
        "source": doc.source,
        "version": doc.version,
        "updated_at": doc.updated_at,
        "matched_keywords": item["matched_keywords"],
        "semantic_score": item["semantic_score"],
        "lexical_score": item["lexical_score"],
        "rerank_score": item["rerank_score"],
    }


def _case_payload(doc: RagDocument, score: float | None = None) -> dict[str, Any]:
    return {
        "case_id": doc.case_id,
        "title": doc.title,
        "category": doc.category,
        "scene": doc.content,
        "risk_points": doc.risk_points,
        "handling": doc.handling,
        "source": doc.source,
        "version": doc.version,
        "score": score,
    }


def retrieve(question: str, top_k: int = 4) -> list[dict[str, Any]]:
    return [_reference_payload(item) for item in _engine().retrieve(question, top_k)]


def get_rag_status() -> dict[str, Any]:
    return _engine().status()


def rebuild_rag_index() -> dict[str, Any]:
    reset_rag_cache()
    return get_rag_status()


def answer_question(question: str) -> dict[str, Any]:
    engine = _engine()
    refs = engine.retrieve(question)
    version = engine.version
    if not refs:
        return {
            "answer": "没有检索到足够相关的知识条目。建议先不要转账、不要透露验证码或密码，并通过官方渠道或学校安全部门核实。",
            "references": [],
            "case_citations": [],
            "knowledge_version": version,
            "retrieval_method": engine.retrieval_method,
        }

    first_doc: RagDocument = refs[0]["doc"]
    actions: list[str] = []
    for item in refs:
        for action in item["doc"].actions:
            if action and action not in actions:
                actions.append(action)

    case_docs = [
        item["doc"]
        for item in refs
        if item["doc"].source_type == "case" and item["doc"].category == first_doc.category
    ]
    if not case_docs:
        case_docs = [
            doc
            for doc in engine.docs
            if doc.source_type == "case" and doc.category == first_doc.category
        ][:2]

    action_text = "；".join(actions[:4]) if actions else "暂停操作并通过官方渠道核实"
    case_text = ""
    if case_docs:
        case_titles = "、".join(f"“{doc.title}”" for doc in case_docs[:2])
        case_text = f" 可参考相似案例：{case_titles}。"

    answer = (
        f"初步判断：{first_doc.title}。{first_doc.content}{case_text}"
        f"建议你优先做到：{action_text}。"
    )

    return {
        "answer": answer,
        "references": [_reference_payload(item) for item in refs],
        "case_citations": [
            _case_payload(doc, next((item["score"] for item in refs if item["doc"].doc_id == doc.doc_id), None))
            for doc in case_docs[:3]
        ],
        "knowledge_version": version,
        "retrieval_method": engine.retrieval_method,
    }
