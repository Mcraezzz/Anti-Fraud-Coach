from __future__ import annotations

import json
import re
from typing import Any

from .config import AppConfig
from .data_loader import load_knowledge_corpus
from .entity_extraction import EntityExtraction, extract_entities
from .preprocessing import preprocess_media_text
from .qwen_client import QwenClient
from .retriever import LocalRagIndex
from .risk_features import RiskFeatures, extract_risk_features
from .utils import detect_language


class AntiFraudRagEngine:
    def __init__(self, config: AppConfig, index: LocalRagIndex) -> None:
        self.config = config
        self.index = index

    @classmethod
    def load(cls, config: AppConfig) -> "AntiFraudRagEngine":
        if not (config.index_dir / "bm25.joblib").exists():
            items, iocs = load_knowledge_corpus(config)
            index = LocalRagIndex.build(items, iocs, config)
            index.save(config.index_dir)
        else:
            index = LocalRagIndex.load(config.index_dir, config)
        return cls(config, index)

    def analyze(
        self,
        text: str,
        top_k: int = 6,
        mock: bool = False,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        preprocessed = preprocess_media_text(text)
        analysis_text = preprocessed.normalized_text
        language = detect_language(analysis_text)
        risk_features = extract_risk_features(analysis_text, language)
        exact_matches = self.index.exact_ioc_matches(analysis_text)
        evidence = self.index.retrieve(
            analysis_text,
            top_k=top_k,
            risk_features=risk_features,
            exact_matches=exact_matches,
        )
        entity_extraction = extract_entities(analysis_text, evidence)

        if mock or not (api_key or self.config.qwen_api_key):
            analysis = self._mock_analysis(
                analysis_text,
                language,
                evidence,
                exact_matches,
                risk_features,
                entity_extraction,
            )
            raw = "mock"
        else:
            prompt = build_prompt(
                analysis_text,
                language,
                evidence,
                exact_matches,
                risk_features,
                entity_extraction,
                preprocessed.to_dict(),
                self.config,
            )
            try:
                client = QwenClient(self.config, api_key=api_key)
                raw = client.complete(prompt)
                analysis = parse_json_response(raw)
            except Exception as exc:
                analysis = self._mock_analysis(
                    analysis_text,
                    language,
                    evidence,
                    exact_matches,
                    risk_features,
                    entity_extraction,
                )
                analysis["api_error"] = f"{type(exc).__name__}: {exc}"
                raw = "api_error_fallback"

        analysis = ensure_analysis_schema(
            analysis,
            language=language,
            risk_features=risk_features,
            entity_extraction=entity_extraction,
            evidence=evidence,
            exact_matches=exact_matches,
            config=self.config,
        )

        return {
            "input_text": text,
            "preprocessing": preprocessed.to_dict(),
            "detected_language": language,
            "entity_extraction": entity_extraction.to_dict(),
            "risk_features": risk_features.to_dict(),
            "analysis": analysis,
            "retrieved_evidence": evidence,
            "exact_ioc_matches": exact_matches,
            "raw_model_output": raw,
        }

    def _mock_analysis(
        self,
        text: str,
        language: str,
        evidence: list[dict],
        exact_matches: list[dict],
        risk_features: RiskFeatures,
        entity_extraction: EntityExtraction,
    ) -> dict[str, Any]:
        risk_score = heuristic_risk_score(risk_features, evidence, exact_matches)
        risk_level = risk_level_from_score(risk_score)
        fraud_type = infer_fraud_type(risk_features, evidence)
        signals = build_risk_signal_list(risk_features, exact_matches)
        return {
            "schema_version": "1.1",
            "detected_language": language,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "fraud_type": fraud_type,
            "risk_features": risk_features.to_dict(),
            "risk_signals": signals,
            "entity_extraction": entity_extraction.to_dict(),
            "event_subjects": entity_extraction.subjects() or infer_event_subjects(text, evidence),
            "reasoning": (
                "Mock mode combines the independent risk-feature extractor, exact URL/domain "
                "indicator matches, and the top retrieved RAG evidence."
            ),
            "evidence_summary": evidence_fusion_summary(evidence),
            "natural_language_report": build_mock_report(risk_level, fraud_type, signals),
            "anti_fraud_suggestion": (
                "Do not click unknown links, do not share passwords or verification codes, "
                "and verify requests through official university, bank, or platform channels."
            ),
            "compliance_rewrite": (
                "Please verify this request through the official campus system or a trusted "
                "contact channel before providing any personal, account, or payment information."
            ),
            "training_question": {
                "question": "Which signal is the strongest indicator of possible fraud?",
                "reference_answer": "Requests for credentials, verification codes, payment, or urgent action through an unknown link.",
            },
            "compliance_reminder": (
                "This result is educational risk guidance and should not replace official "
                "police, bank, university, or legal verification."
            ),
        }


def build_prompt(
    text: str,
    language: str,
    evidence: list[dict],
    exact_matches: list[dict],
    risk_features: RiskFeatures,
    entity_extraction: EntityExtraction,
    preprocessing: dict[str, Any],
    config: AppConfig,
) -> list[dict[str, str]]:
    evidence_block = json.dumps(evidence, ensure_ascii=False, indent=2)
    ioc_block = json.dumps(exact_matches, ensure_ascii=False, indent=2)
    risk_block = json.dumps(risk_features.to_dict(), ensure_ascii=False, indent=2)
    entity_block = json.dumps(entity_extraction.to_dict(), ensure_ascii=False, indent=2)
    preprocessing_block = json.dumps(preprocessing, ensure_ascii=False, indent=2)
    fusion_block = json.dumps(
        {
            "formula": "final_score = alpha*bm25_score + beta*dense_score + gamma*url_match_score + delta*risk_keyword_score, then optional BGE reranking",
            "weights": fusion_weights(config),
            "top_evidence_scores": evidence_fusion_summary(evidence),
        },
        ensure_ascii=False,
        indent=2,
    )
    system = (
        "You are a bilingual anti-fraud media safety assistant for college students. "
        "Analyze Chinese, English, or mixed-language content. Use retrieved evidence and "
        "risk features, but do not invent facts. Return only valid JSON."
    )
    user = f"""
Task: Identify fraud risk in the user's media content and generate a structured safety report.

Language policy:
- If the input is Chinese, write natural_language_report, anti_fraud_suggestion, compliance_rewrite, and training_question in Chinese.
- If the input is English, write them in English.
- If the input is mixed, use concise bilingual Chinese-English wording.

Input language: {language}

User content:
{text}

Text preprocessing result:
{preprocessing_block}

Independent risk feature extraction:
{risk_block}

Entity extraction / sender identity clues:
{entity_block}

Exact URL/domain indicator matches:
{ioc_block}

Evidence fusion configuration:
{fusion_block}

Retrieved RAG evidence:
{evidence_block}

Return only one JSON object with this schema:
{{
  "schema_version": "1.1",
  "detected_language": "zh | en | mixed | unknown",
  "risk_level": "High | Medium | Low",
  "risk_score": 0.0,
  "fraud_type": "short bilingual type name",
  "risk_features": {{"copy_or_summarize": "the extracted risk features"}},
  "entity_extraction": {{"copy_or_summarize": "sender identity, contact, URL, organization, and role clues"}},
  "risk_signals": ["specific signal grounded in input or evidence"],
  "event_subjects": ["people, organizations, URLs, accounts, or roles mentioned"],
  "reasoning": "brief evidence-grounded explanation",
  "evidence_summary": [
    {{"rank": 1, "title": "evidence title", "why_relevant": "brief reason"}}
  ],
  "evidence_fusion": {{
    "formula": "final_score = alpha*bm25 + beta*dense + gamma*url_match + delta*risk_keyword + optional rerank",
    "weights": {{"alpha_bm25": 0.35, "beta_dense": 0.35, "gamma_url_match": 0.15, "delta_risk_keyword": 0.15, "reranker_weight": 0.30}},
    "top_evidence_scores": []
  }},
  "natural_language_report": "student-facing explanation",
  "anti_fraud_suggestion": "actionable advice",
  "compliance_rewrite": "safer rewrite of the suspicious content or a safe response template",
  "training_question": {{"question": "one quiz question", "reference_answer": "short answer"}},
  "compliance_reminder": "privacy, verification, and non-legal-advice reminder"
}}
"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def parse_json_response(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    match = re.search(r"(\{.*\})", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    return {
        "detected_language": "unknown",
        "risk_level": "Unknown",
        "fraud_type": "Unknown",
        "risk_signals": [],
        "reasoning": raw,
        "anti_fraud_suggestion": "Please verify through official channels.",
        "training_question": "What evidence would you check before trusting this message?",
        "compliance_reminder": "This is educational guidance, not legal or financial advice.",
    }


def ensure_analysis_schema(
    analysis: dict[str, Any],
    language: str,
    risk_features: RiskFeatures,
    entity_extraction: EntityExtraction,
    evidence: list[dict],
    exact_matches: list[dict],
    config: AppConfig,
) -> dict[str, Any]:
    if not isinstance(analysis, dict):
        analysis = {}

    fallback_score = heuristic_risk_score(risk_features, evidence, exact_matches)
    risk_score = coerce_float(analysis.get("risk_score"), fallback_score)
    risk_score = round(max(0.0, min(risk_score, 1.0)), 4)
    risk_level = normalize_risk_level(analysis.get("risk_level")) or risk_level_from_score(risk_score)
    signals = ensure_list(analysis.get("risk_signals")) or build_risk_signal_list(risk_features, exact_matches)
    subjects = ensure_list(analysis.get("event_subjects")) or entity_extraction.subjects() or infer_event_subjects("", evidence)
    evidence_scores = evidence_fusion_summary(evidence)

    normalized = {
        "schema_version": str(analysis.get("schema_version") or "1.1"),
        "detected_language": str(analysis.get("detected_language") or language),
        "risk_level": risk_level,
        "risk_score": risk_score,
        "fraud_type": str(analysis.get("fraud_type") or infer_fraud_type(risk_features, evidence)),
        "risk_features": analysis.get("risk_features") or risk_features.to_dict(),
        "entity_extraction": analysis.get("entity_extraction") or entity_extraction.to_dict(),
        "risk_signals": signals,
        "event_subjects": subjects,
        "reasoning": str(
            analysis.get("reasoning")
            or "Risk judgment is based on extracted features, exact IOC matches, and retrieved evidence."
        ),
        "evidence_summary": analysis.get("evidence_summary") or evidence_scores,
        "evidence_fusion": analysis.get("evidence_fusion")
        or {
            "formula": "final_score = alpha*bm25_score + beta*dense_score + gamma*url_match_score + delta*risk_keyword_score, then optional BGE reranking",
            "weights": fusion_weights(config),
            "top_evidence_scores": evidence_scores,
        },
        "natural_language_report": str(
            analysis.get("natural_language_report")
            or build_mock_report(risk_level, infer_fraud_type(risk_features, evidence), signals)
        ),
        "anti_fraud_suggestion": str(
            analysis.get("anti_fraud_suggestion")
            or "Do not click unknown links or disclose credentials, verification codes, bank-card details, or payment information."
        ),
        "compliance_rewrite": str(
            analysis.get("compliance_rewrite")
            or "Please verify this request through official channels before taking any action."
        ),
        "training_question": analysis.get("training_question")
        or {
            "question": "What evidence should a student verify before trusting this message?",
            "reference_answer": "The sender identity, official channel, link/domain, and any request for credentials or payment.",
        },
        "compliance_reminder": str(
            analysis.get("compliance_reminder")
            or "This result is educational guidance, not legal or financial advice."
        ),
        "evaluation_labels": {
            "has_url": bool(risk_features.urls),
            "has_domain": bool(risk_features.domains),
            "has_exact_ioc_match": bool(exact_matches),
            "matched_feature_categories": risk_features.matched_categories,
            "entity_subject_count": len(entity_extraction.subjects()),
            "retrieved_evidence_count": len(evidence),
        },
    }

    for key, value in analysis.items():
        if key not in normalized:
            normalized[key] = value
    return normalized


def heuristic_risk_score(
    risk_features: RiskFeatures,
    evidence: list[dict],
    exact_matches: list[dict],
) -> float:
    feature_score = risk_features.risk_keyword_score * 0.68
    ioc_score = 0.24 if exact_matches else 0.0
    high_evidence = any(item.get("metadata", {}).get("risk_level") == "High" for item in evidence[:3])
    campus_evidence = any(item.get("source") == "campus_rules" for item in evidence[:3])
    evidence_score = 0.08 if high_evidence or campus_evidence else 0.0
    return round(min(feature_score + ioc_score + evidence_score, 1.0), 4)


def risk_level_from_score(score: float) -> str:
    if score >= 0.7:
        return "High"
    if score >= 0.35:
        return "Medium"
    return "Low"


def normalize_risk_level(value: Any) -> str | None:
    if not value:
        return None
    text = str(value).strip().lower()
    if text.startswith("high"):
        return "High"
    if text.startswith("medium") or text.startswith("moderate"):
        return "Medium"
    if text.startswith("low"):
        return "Low"
    return None


def infer_fraud_type(risk_features: RiskFeatures, evidence: list[dict]) -> str:
    category_labels = {
        "credential_request": "Credential phishing / account takeover",
        "financial_info": "Financial information theft",
        "upfront_payment": "Upfront-fee scam",
        "urgency_pressure": "Urgency-pressure phishing",
        "impersonation": "Impersonation fraud",
        "job_or_internship": "Job or internship scam",
        "campus_context": "Campus-themed social engineering",
        "refund_or_reward": "Refund or reward scam",
        "investment_or_loan": "Investment or loan scam",
    }
    labels = [category_labels.get(category, category) for category in risk_features.matched_categories[:2]]
    if labels:
        return " + ".join(labels)
    if evidence:
        return str(evidence[0].get("title") or "Unknown fraud pattern")
    return "Unknown fraud pattern"


def build_risk_signal_list(risk_features: RiskFeatures, exact_matches: list[dict]) -> list[str]:
    signals: list[str] = []
    for category, hits in risk_features.category_hits.items():
        sample = ", ".join(hits[:3])
        signals.append(f"{category}: {sample}")
    for url in risk_features.urls[:3]:
        signals.append(f"URL detected: {url}")
    for match in exact_matches:
        signals.append(f"Exact IOC match: {match.get('value')}")
    return signals[:10]


def infer_event_subjects(text: str, evidence: list[dict]) -> list[str]:
    subjects: list[str] = []
    for url in re.findall(r"https?://[^\s]+", text):
        subjects.append(url.rstrip(".,;:!?)]}"))
    for item in evidence[:2]:
        title = item.get("title")
        if title:
            subjects.append(str(title))
    return dedupe(subjects)[:8]


def build_mock_report(risk_level: str, fraud_type: str, signals: list[str]) -> str:
    signal_text = "; ".join(signals[:3]) if signals else "no strong keyword signal"
    return (
        f"Risk level: {risk_level}. Main pattern: {fraud_type}. "
        f"Key signals: {signal_text}. Verify through official channels before responding."
    )


def evidence_fusion_summary(evidence: list[dict]) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for item in evidence:
        summary.append(
            {
                "rank": item.get("rank"),
                "id": item.get("id"),
                "title": item.get("title"),
                "source": item.get("source"),
                "final_score": round(float(item.get("score", 0.0)), 4),
                "fusion_score": round(float(item.get("fusion_score", 0.0)), 4),
                "reranker_score": round(float(item.get("reranker_score", 0.0)), 4),
                "bm25_score": round(float(item.get("bm25_score", 0.0)), 4),
                "dense_score": round(float(item.get("dense_score", 0.0)), 4),
                "url_match_score": round(float(item.get("url_match_score", 0.0)), 4),
                "risk_keyword_score": round(float(item.get("risk_keyword_score", 0.0)), 4),
            }
        )
    return summary


def fusion_weights(config: AppConfig) -> dict[str, float]:
    return {
        "alpha_bm25": config.fusion_alpha,
        "beta_dense": config.fusion_beta,
        "gamma_url_match": config.fusion_gamma,
        "delta_risk_keyword": config.fusion_delta,
        "reranker_weight": config.reranker_weight if config.use_reranker else 0.0,
    }


def ensure_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def coerce_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result
