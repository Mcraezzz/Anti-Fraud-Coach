from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import faiss
import jieba
import joblib
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from .config import AppConfig
from .reranker import BgeReranker
from .risk_features import RiskFeatures
from .schemas import IocStore, KnowledgeItem
from .utils import compact, extract_domains, extract_urls, normalize_text


class BM25Index:
    def __init__(self, tokenized_docs: list[list[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.doc_len = np.array([len(doc) for doc in tokenized_docs], dtype=np.float32)
        self.avgdl = float(self.doc_len.mean()) if len(self.doc_len) else 0.0
        self.doc_freqs: list[Counter[str]] = [Counter(doc) for doc in tokenized_docs]
        document_frequency: Counter[str] = Counter()
        for freqs in self.doc_freqs:
            document_frequency.update(freqs.keys())
        total_docs = max(len(tokenized_docs), 1)
        self.idf = {
            token: math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
            for token, df in document_frequency.items()
        }

    def get_scores(self, query_tokens: list[str]) -> np.ndarray:
        scores = np.zeros(len(self.doc_freqs), dtype=np.float32)
        if not query_tokens or self.avgdl <= 0:
            return scores
        query_terms = set(query_tokens)
        for i, freqs in enumerate(self.doc_freqs):
            doc_score = 0.0
            dl = self.doc_len[i]
            for token in query_terms:
                tf = freqs.get(token, 0)
                if not tf:
                    continue
                idf = self.idf.get(token, 0.0)
                denom = tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                doc_score += idf * (tf * (self.k1 + 1) / denom)
            scores[i] = doc_score
        return scores


class BgeM3Embedder:
    def __init__(
        self,
        model_path: Path,
        batch_size: int = 8,
        max_seq_length: int = 512,
        device: str = "auto",
    ) -> None:
        self.model_path = model_path
        self.batch_size = batch_size
        self.max_seq_length = max_seq_length
        self.device = resolve_torch_device(device)
        self._model: SentenceTransformer | None = None

    def _load(self) -> SentenceTransformer:
        if self._model is None:
            if not self.model_path.exists():
                raise FileNotFoundError(f"BGE-M3 model path not found: {self.model_path}")
            self._model = SentenceTransformer(str(self.model_path), device=self.device)
            self._model.max_seq_length = self.max_seq_length
        return self._model

    def encode(self, texts: list[str], show_progress_bar: bool = False) -> np.ndarray:
        model = self._load()
        embeddings = model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=show_progress_bar,
        )
        return np.asarray(embeddings, dtype=np.float32)


class LocalRagIndex:
    def __init__(
        self,
        items: list[KnowledgeItem],
        bm25: BM25Index,
        iocs: IocStore,
        config: AppConfig,
        faiss_index=None,
        dense_item_indices: list[int] | None = None,
    ) -> None:
        self.items = items
        self.bm25 = bm25
        self.iocs = iocs
        self.config = config
        self.faiss_index = faiss_index
        self.dense_item_indices = dense_item_indices or []
        self._embedder: BgeM3Embedder | None = None
        self._reranker: BgeReranker | None = None

    @classmethod
    def build(
        cls,
        items: list[KnowledgeItem],
        iocs: IocStore,
        config: AppConfig,
        build_dense: bool = True,
        dense_limit: int | None = None,
    ) -> "LocalRagIndex":
        documents = [document_for_retrieval(item) for item in items]
        bm25 = BM25Index([tokenize_for_bm25(doc) for doc in documents])
        faiss_index = None
        dense_item_indices: list[int] = []

        if build_dense and items:
            limit = dense_limit if dense_limit is not None else config.dense_limit
            dense_item_indices = select_dense_item_indices(items, limit)
            dense_docs = [documents[i] for i in dense_item_indices]
            embedder = BgeM3Embedder(
                config.bge_m3_path,
                batch_size=config.dense_batch_size,
                max_seq_length=config.dense_max_seq_length,
                device=config.bge_device,
            )
            embeddings = embedder.encode(dense_docs, show_progress_bar=True)
            faiss_index = faiss.IndexFlatIP(embeddings.shape[1])
            faiss_index.add(embeddings)

        return cls(
            items=items,
            bm25=bm25,
            iocs=iocs,
            config=config,
            faiss_index=faiss_index,
            dense_item_indices=dense_item_indices,
        )

    @classmethod
    def load(cls, index_dir: Path, config: AppConfig) -> "LocalRagIndex":
        items = []
        with (index_dir / "items.jsonl").open("r", encoding="utf-8") as handle:
            for line in handle:
                items.append(KnowledgeItem.from_dict(json.loads(line)))
        bm25 = joblib.load(index_dir / "bm25.joblib")
        iocs = IocStore()
        domains_path = index_dir / "ioc_domains.txt"
        urls_path = index_dir / "ioc_urls.txt"
        if domains_path.exists():
            iocs.domains = {x.strip() for x in domains_path.read_text(encoding="utf-8").splitlines() if x.strip()}
        if urls_path.exists():
            iocs.urls = {x.strip() for x in urls_path.read_text(encoding="utf-8").splitlines() if x.strip()}

        faiss_index = None
        dense_item_indices: list[int] = []
        faiss_path = index_dir / "faiss_bge_m3.index"
        dense_map_path = index_dir / "dense_item_indices.json"
        if faiss_path.exists() and dense_map_path.exists():
            faiss_index = faiss.read_index(str(faiss_path))
            dense_item_indices = json.loads(dense_map_path.read_text(encoding="utf-8"))

        return cls(
            items=items,
            bm25=bm25,
            iocs=iocs,
            config=config,
            faiss_index=faiss_index,
            dense_item_indices=dense_item_indices,
        )

    def save(self, index_dir: Path) -> None:
        index_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.bm25, index_dir / "bm25.joblib")
        with (index_dir / "items.jsonl").open("w", encoding="utf-8") as handle:
            for item in self.items:
                handle.write(json.dumps(item.to_dict(), ensure_ascii=False) + "\n")
        (index_dir / "ioc_domains.txt").write_text("\n".join(sorted(self.iocs.domains)), encoding="utf-8")
        (index_dir / "ioc_urls.txt").write_text("\n".join(sorted(self.iocs.urls)), encoding="utf-8")

        if self.faiss_index is not None and self.dense_item_indices:
            faiss.write_index(self.faiss_index, str(index_dir / "faiss_bge_m3.index"))
            (index_dir / "dense_item_indices.json").write_text(
                json.dumps(self.dense_item_indices, ensure_ascii=False),
                encoding="utf-8",
            )

        manifest = {
            "retriever": "BAAI/bge-m3 + BM25 + FAISS",
            "items": len(self.items),
            "dense_items": len(self.dense_item_indices),
            "bge_m3_path": str(self.config.bge_m3_path),
            "dense_max_seq_length": self.config.dense_max_seq_length,
            "dense_batch_size": self.config.dense_batch_size,
            "bge_device": resolve_torch_device(self.config.bge_device),
            "reranker": str(self.config.reranker_path),
            "use_reranker": self.config.use_reranker,
            "fusion_formula": "alpha*bm25 + beta*dense + gamma*url_match + delta*risk_keyword",
            "deduplication": "explicit evidence dedup by item id and normalized title/text fingerprint before final top-k output",
            "fusion_weights": {
                "alpha_bm25": self.config.fusion_alpha,
                "beta_dense": self.config.fusion_beta,
                "gamma_url_match": self.config.fusion_gamma,
                "delta_risk_keyword": self.config.fusion_delta,
            },
        }
        (index_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    def retrieve(
        self,
        query: str,
        top_k: int = 6,
        risk_features: RiskFeatures | None = None,
        exact_matches: list[dict[str, str]] | None = None,
    ) -> list[dict]:
        exact_matches = exact_matches or []
        bm25_scores = self.bm25.get_scores(tokenize_for_bm25(query))
        dense_scores = np.zeros(len(self.items), dtype=np.float32)

        if self.faiss_index is not None and self.dense_item_indices:
            try:
                embedder = self._get_embedder()
                query_embedding = embedder.encode([normalize_text(query)], show_progress_bar=False)
                search_k = min(max(top_k * 8, 30), len(self.dense_item_indices))
                scores, dense_positions = self.faiss_index.search(query_embedding, search_k)
                for score, dense_position in zip(scores[0], dense_positions[0]):
                    if dense_position < 0:
                        continue
                    item_index = self.dense_item_indices[int(dense_position)]
                    dense_scores[item_index] = max(float(score), dense_scores[item_index])
            except Exception:
                dense_scores = np.zeros(len(self.items), dtype=np.float32)

        bm25_norm = normalize_scores(bm25_scores)
        dense_norm = normalize_scores(dense_scores)
        url_match_scores = url_match_component(self.items, exact_matches)
        risk_keyword_scores = risk_keyword_component(self.items, risk_features)
        fusion_scores = (
            self.config.fusion_alpha * bm25_norm
            + self.config.fusion_beta * dense_norm
            + self.config.fusion_gamma * url_match_scores
            + self.config.fusion_delta * risk_keyword_scores
            + retrieval_boosts(self.items)
        )

        candidate_count = min(max(top_k * 4, self.config.reranker_top_n, top_k), len(self.items))
        candidate_indices = fusion_scores.argsort()[::-1][:candidate_count]
        final_scores = fusion_scores.copy()
        reranker_scores = np.zeros(len(self.items), dtype=np.float32)

        if self.config.use_reranker and candidate_count:
            try:
                reranker = self._get_reranker()
                passages = [document_for_retrieval(self.items[int(idx)]) for idx in candidate_indices]
                candidate_rerank_scores = reranker.score(query, passages)
                for idx, rerank_score in zip(candidate_indices, candidate_rerank_scores):
                    reranker_scores[int(idx)] = float(rerank_score)
                fusion_candidate_norm = normalize_scores(fusion_scores[candidate_indices])
                combined = (
                    (1.0 - self.config.reranker_weight) * fusion_candidate_norm
                    + self.config.reranker_weight * candidate_rerank_scores
                )
                for idx, combined_score in zip(candidate_indices, combined):
                    final_scores[int(idx)] = float(combined_score)
            except Exception:
                reranker_scores = np.zeros(len(self.items), dtype=np.float32)

        output_pool_size = min(max(top_k * 4, top_k), len(self.items))
        top_indices = final_scores.argsort()[::-1][:output_pool_size]

        candidate_results = []
        for rank, idx in enumerate(top_indices, 1):
            item = self.items[int(idx)]
            candidate_results.append(
                {
                    "rank": rank,
                    "score": float(final_scores[idx]),
                    "fusion_score": float(fusion_scores[idx]),
                    "reranker_score": float(reranker_scores[idx]),
                    "bm25_score": float(bm25_scores[idx]),
                    "dense_score": float(dense_scores[idx]),
                    "url_match_score": float(url_match_scores[idx]),
                    "risk_keyword_score": float(risk_keyword_scores[idx]),
                    "id": item.id,
                    "source": item.source,
                    "title": item.title,
                    "text": compact(item.text, 900),
                    "metadata": {
                        **item.metadata,
                        "language": item.language,
                        "category": item.category,
                        "risk_level": item.risk_level,
                    },
                }
            )
        return deduplicate_evidence_results(candidate_results, top_k=top_k)

    def exact_ioc_matches(self, text: str) -> list[dict[str, str]]:
        matches: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for url in extract_urls(text):
            normalized = normalize_url_indicator(url)
            if normalized in self.iocs.urls:
                key = ("url", normalized)
                if key not in seen:
                    matches.append({"type": "url", "value": url, "match": normalized})
                    seen.add(key)
        for domain in extract_domains(text):
            normalized = normalize_domain_indicator(domain)
            if normalized in self.iocs.domains:
                key = ("domain", normalized)
                if key not in seen:
                    matches.append({"type": "domain", "value": domain, "match": normalized})
                    seen.add(key)
        return matches

    def _get_embedder(self) -> BgeM3Embedder:
        if self._embedder is None:
            self._embedder = BgeM3Embedder(
                self.config.bge_m3_path,
                batch_size=self.config.dense_batch_size,
                max_seq_length=self.config.dense_max_seq_length,
                device=self.config.bge_device,
            )
        return self._embedder

    def _get_reranker(self) -> BgeReranker:
        if self._reranker is None:
            self._reranker = BgeReranker(self.config)
        return self._reranker


def document_for_retrieval(item: KnowledgeItem) -> str:
    return "\n".join(
        [
            item.title,
            item.source,
            item.language,
            item.category,
            item.risk_level,
            item.text,
        ]
    )


def resolve_torch_device(device: str) -> str:
    if device == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda" and not torch.cuda.is_available():
        return "cpu"
    return device


def tokenize_for_bm25(text: str) -> list[str]:
    text = normalize_text(text).lower()
    tokens: list[str] = []
    tokens.extend(re.findall(r"[a-z0-9][a-z0-9._:/-]{1,}", text))
    for match in re.finditer(r"[\u4e00-\u9fff]+", text):
        tokens.extend(token for token in jieba.cut(match.group(0)) if len(token.strip()) > 1)
    return tokens


def select_dense_item_indices(items: list[KnowledgeItem], limit: int) -> list[int]:
    if limit <= 0 or limit >= len(items):
        return list(range(len(items)))
    priority_sources = {"campus_rules", "email_safety_triage", "discord_phishing", "sms_mms", "ChiFraud"}
    scored = []
    for idx, item in enumerate(items):
        score = 0
        if item.source == "campus_rules":
            score += 100
        if item.risk_level == "High":
            score += 20
        if item.source in priority_sources:
            score += 5
        scored.append((score, idx))
    return [idx for _, idx in sorted(scored, reverse=True)[:limit]]


def normalize_scores(scores: np.ndarray) -> np.ndarray:
    if scores.size == 0:
        return scores
    max_score = float(scores.max())
    min_score = float(scores.min())
    if max_score <= min_score:
        return np.zeros_like(scores, dtype=np.float32)
    return ((scores - min_score) / (max_score - min_score)).astype(np.float32)


def retrieval_boosts(items: list[KnowledgeItem]) -> np.ndarray:
    boosts = np.zeros(len(items), dtype=np.float32)
    for idx, item in enumerate(items):
        if item.source == "campus_rules":
            boosts[idx] += 0.07
        if item.risk_level == "High":
            boosts[idx] += 0.04
    return boosts


def deduplicate_evidence_results(results: list[dict], top_k: int) -> list[dict]:
    deduped: list[dict] = []
    seen_ids: set[str] = set()
    seen_fingerprints: set[str] = set()

    for item in sorted(results, key=lambda value: float(value.get("score", 0.0)), reverse=True):
        item_id = str(item.get("id") or "")
        fingerprint = evidence_fingerprint(item)
        if item_id and item_id in seen_ids:
            continue
        if fingerprint and fingerprint in seen_fingerprints:
            continue
        if item_id:
            seen_ids.add(item_id)
        if fingerprint:
            seen_fingerprints.add(fingerprint)
        deduped.append(item)
        if len(deduped) >= top_k:
            break

    for rank, item in enumerate(deduped, 1):
        item["rank"] = rank
    return deduped


def evidence_fingerprint(item: dict) -> str:
    title = str(item.get("title") or "")
    text = str(item.get("text") or "")
    normalized = normalize_text(f"{title} {text}").lower()
    normalized = re.sub(r"https?://\S+", " <url> ", normalized)
    normalized = re.sub(r"\d+", " <num> ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized[:500]


def url_match_component(items: list[KnowledgeItem], exact_matches: list[dict[str, str]]) -> np.ndarray:
    scores = np.zeros(len(items), dtype=np.float32)
    if not exact_matches:
        return scores
    for idx, item in enumerate(items):
        text = f"{item.title} {item.category} {item.source} {item.text}".lower()
        if any(token in text for token in ["phish", "url", "link", "account", "钓鱼", "链接", "账号"]):
            scores[idx] = 1.0
        elif item.source in {"sms_mms", "email_safety_triage", "discord_phishing"}:
            scores[idx] = 0.85
        elif item.source == "campus_rules":
            scores[idx] = 0.65
        elif item.risk_level == "High":
            scores[idx] = 0.35
    return scores


def risk_keyword_component(items: list[KnowledgeItem], risk_features: RiskFeatures | None) -> np.ndarray:
    scores = np.zeros(len(items), dtype=np.float32)
    if not risk_features:
        return scores
    terms = [term.lower() for term in risk_features.matched_terms]
    categories = set(risk_features.matched_categories)
    base_score = risk_features.risk_keyword_score
    for idx, item in enumerate(items):
        document = document_for_retrieval(item).lower()
        direct_hits = sum(1 for term in terms if term and term in document)
        direct_score = min(direct_hits / 4.0, 1.0)
        category_score = category_alignment_score(document, categories)
        risk_level_score = 0.2 if item.risk_level == "High" else 0.0
        scores[idx] = min(0.45 * direct_score + 0.35 * category_score + 0.2 * base_score + risk_level_score, 1.0)
    return scores


def category_alignment_score(document: str, categories: set[str]) -> float:
    score = 0.0
    alignments = {
        "credential_request": ["验证码", "password", "credential", "sms code", "登录"],
        "financial_info": ["银行卡", "bank", "credit card", "payment"],
        "upfront_payment": ["保证金", "押金", "deposit", "training fee", "fee"],
        "urgency_pressure": ["紧急", "urgent", "suspended", "deadline"],
        "impersonation": ["冒充", "impersonation", "customer service", "hr", "老师", "客服"],
        "job_or_internship": ["实习", "兼职", "internship", "job", "hr"],
        "campus_context": ["校园", "学生", "university", "student", "scholarship"],
        "refund_or_reward": ["退款", "补贴", "refund", "reward", "compensation"],
        "investment_or_loan": ["贷款", "投资", "loan", "investment", "crypto"],
    }
    for category in categories:
        if any(token in document for token in alignments.get(category, [])):
            score += 0.25
    return min(score, 1.0)


def normalize_domain_indicator(value: str) -> str:
    value = value.strip().lower()
    if "://" not in value:
        value = "http://" + value
    parsed = urlparse(value)
    host = parsed.netloc or parsed.path.split("/")[0]
    return host.lstrip("www.").strip()


def normalize_url_indicator(value: str) -> str:
    value = value.strip().lower()
    if "://" not in value:
        value = "http://" + value
    parsed = urlparse(value)
    host = (parsed.netloc or "").lstrip("www.")
    path = parsed.path.rstrip("/")
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{host}{path}{query}" if host else ""
