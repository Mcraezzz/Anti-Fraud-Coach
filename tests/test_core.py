import json
import unittest

import numpy as np

from anti_fraud_rag.data_loader import (
    SMS_LABELS,
    infer_email_label,
    label_display_name,
    normalize_domain_ioc,
    normalize_url_ioc,
)
from anti_fraud_rag.entity_extraction import extract_entities
from anti_fraud_rag.ocr import parse_ocr_lines
from anti_fraud_rag.preprocessing import build_analysis_input, preprocess_media_text
from anti_fraud_rag.rag_engine import coerce_float, parse_json_response
from anti_fraud_rag.reranker import normalize_reranker_scores
from anti_fraud_rag.risk_features import extract_risk_features
from anti_fraud_rag.retriever import deduplicate_evidence_results, normalize_domain_indicator, normalize_url_indicator
from anti_fraud_rag.retriever import BM25Index, LocalRagIndex, tokenize_for_bm25
from anti_fraud_rag.schemas import IocStore
from anti_fraud_rag.utils import detect_language, extract_domains, extract_urls


class CoreBehaviorTests(unittest.TestCase):
    def test_language_detection_ignores_urls(self):
        text = "请点击 http://fake-campus.example.com 填写银行卡和验证码"
        self.assertEqual(detect_language(text), "zh")
        self.assertEqual(detect_language("Verify your student account now"), "en")
        self.assertEqual(detect_language("Hi同学, please verify now"), "mixed")

    def test_email_label_from_nested_output_json(self):
        obj = {
            "input": "Subject: verify your account",
            "output": json.dumps({"risk": "phishing", "triage": "ignore"}),
        }
        self.assertEqual(infer_email_label(obj), "phishing")

    def test_readable_sms_label(self):
        self.assertEqual(label_display_name("1", SMS_LABELS), "Malicious SMS/MMS")
        self.assertEqual(label_display_name("0", SMS_LABELS), "Benign SMS/MMS")

    def test_ioc_normalization_preserves_url_path(self):
        self.assertEqual(
            normalize_url_ioc("https://www.example.com/login?a=1"),
            "example.com/login?a=1",
        )
        self.assertEqual(normalize_domain_ioc("https://www.example.com/login"), "example.com")
        self.assertEqual(
            normalize_url_indicator("https://www.example.com/login?a=1"),
            "example.com/login?a=1",
        )
        self.assertEqual(normalize_domain_indicator("https://www.example.com/login"), "example.com")

    def test_ioc_hosts_do_not_lose_leading_w_characters(self):
        for host in ("wallet.example.com", "www2.example.com", "ww.example.com"):
            for normalize in (normalize_domain_ioc, normalize_domain_indicator):
                self.assertEqual(normalize(host), host)
            self.assertIn(host, extract_domains("https://" + host + "/Login"))
        self.assertEqual(normalize_domain_ioc("https://user@www.Example.com:8443/Login"), "example.com")

    def test_ioc_loader_and_query_preserve_url_case(self):
        value = "https://www.Example.com:8443/Login?Token=AbC"
        expected = "example.com:8443/Login?Token=AbC"
        self.assertEqual(normalize_url_ioc(value), expected)
        self.assertEqual(normalize_url_indicator(value), expected)
        self.assertNotEqual(normalize_url_indicator(value.lower()), expected)
        for normalize in (normalize_url_ioc, normalize_url_indicator):
            self.assertEqual(normalize(""), "")
            self.assertEqual(normalize("https://[invalid"), "")

    def test_exact_ioc_match_uses_same_normalization_as_ingestion(self):
        index = LocalRagIndex.__new__(LocalRagIndex)
        url = "https://wallet.example.com/Login?Token=AbC"
        index.iocs = IocStore(domains={normalize_domain_ioc(url)}, urls={normalize_url_ioc(url)})
        matches = index.exact_ioc_matches(url)
        self.assertEqual({item["type"] for item in matches}, {"url", "domain"})
        self.assertEqual([item["type"] for item in index.exact_ioc_matches(url.lower())], ["domain"])
        self.assertEqual(index.exact_ioc_matches("https://allet.example.com/Login?Token=AbC"), [])

    def test_ocr_parser_reads_result_objects_and_generators(self):
        class MethodResult:
            def json(self):
                return {"rec_texts": ["method"], "rec_scores": [0.8]}

        class PropertyResult:
            json = {"res": {"rec_texts": ["property"], "rec_scores": [0.9]}}

        class StringResult:
            json = '{"rec_texts": ["string"]}'

        lines = parse_ocr_lines(iter([MethodResult(), PropertyResult(), StringResult()]))
        self.assertEqual([line.text for line in lines], ["method", "property", "string"])
        self.assertEqual([line.confidence for line in lines], [0.8, 0.9, None])

    def test_ocr_numpy_scores_and_zero_confidence(self):
        lines = parse_ocr_lines({"rec_texts": np.array(["first", "second"]),
                                 "rec_scores": np.array([0.0, 0.9])})
        self.assertEqual([line.confidence for line in lines], [0.0, 0.9])
        self.assertEqual(parse_ocr_lines({"text": "zero", "score": 0, "confidence": 0.9})[0].confidence, 0)
        self.assertIsNone(parse_ocr_lines({"text": "invalid", "score": float("nan")})[0].confidence)

    def test_nonfinite_model_scores_use_fallback(self):
        for value in ("NaN", float("inf"), float("-inf"), None, "invalid"):
            self.assertEqual(coerce_float(value, 0.35), 0.35)
        self.assertEqual(coerce_float("0.8", 0.35), 0.8)

    def test_url_and_domain_extraction(self):
        text = "Go to https://secure-login.example.com/path or secure-login.example.com"
        self.assertEqual(extract_urls(text), ["https://secure-login.example.com/path"])
        self.assertIn("secure-login.example.com", extract_domains(text))

    def test_parse_json_response_with_code_fence(self):
        raw = '```json\n{"risk_level":"High","fraud_type":"phishing"}\n```'
        parsed = parse_json_response(raw)
        self.assertEqual(parsed["risk_level"], "High")

    def test_preprocessing_combines_typed_text_and_ocr(self):
        class OcrStub:
            image_name = "chat.png"
            text = "Enter password\nSMS code 123456"

        processed = build_analysis_input("Verify account\x00 now", [OcrStub()])
        self.assertIn("Verify account now", processed.normalized_text)
        self.assertIn("[Image OCR: chat.png]", processed.normalized_text)
        self.assertEqual(processed.removed_control_chars, 1)
        self.assertIn("typed_text", processed.text_sources)
        self.assertIn("image_ocr:chat.png", processed.text_sources)

    def test_entity_extraction_finds_sender_and_contacts(self):
        entities = extract_entities(
            "IT support says verify at http://secure-campus-login.example.com "
            "or email help@university.example. Pay 299 RMB training fee."
        )
        self.assertIn("secure-campus-login.example.com", entities.domains)
        self.assertIn("help@university.example", entities.email_addresses)
        self.assertIn("299 RMB", entities.money_mentions)
        self.assertIn("campus_office", entities.role_clues)

    def test_risk_feature_extraction_bilingual(self):
        text = (
            "Your university mailbox is suspended. Verify at "
            "http://secure-campus-login.example.com and enter password, SMS code, "
            "bank card details, and a 299 RMB training fee."
        )
        features = extract_risk_features(text, "en")
        self.assertIn("credential_request", features.matched_categories)
        self.assertIn("financial_info", features.matched_categories)
        self.assertIn("upfront_payment", features.matched_categories)
        self.assertGreater(features.risk_keyword_score, 0.3)
        self.assertTrue(features.urls)
        self.assertIn("299 RMB", features.money_mentions)

    def test_money_extraction_ignores_plain_dates_and_times(self):
        features = extract_risk_features("你已获得2026年度补贴，请在今晚22点前处理。", "zh")
        self.assertEqual(features.money_mentions, [])

    def test_ocr_parser_accepts_v2_and_v3_shapes(self):
        v2_raw = [[[[0, 0], [1, 0], [1, 1], [0, 1]], ("验证码 123456", 0.98)]]
        v3_raw = {"rec_texts": ["银行卡", "training fee"], "rec_scores": [0.91, 0.88]}
        v2_lines = parse_ocr_lines(v2_raw)
        v3_lines = parse_ocr_lines(v3_raw)

        self.assertEqual(v2_lines[0].text, "验证码 123456")
        self.assertAlmostEqual(v2_lines[0].confidence, 0.98)
        self.assertEqual([line.text for line in v3_lines], ["银行卡", "training fee"])

    def test_reranker_score_normalization(self):
        scores = normalize_reranker_scores(np.array([-2.0, 0.0, 2.0], dtype=np.float32))
        self.assertTrue(np.all(scores >= 0.0))
        self.assertTrue(np.all(scores <= 1.0))
        self.assertGreater(scores[2], scores[0])

        probabilities = normalize_reranker_scores(np.array([0.2, 0.9], dtype=np.float32))
        self.assertAlmostEqual(float(probabilities[0]), 0.2, places=5)
        self.assertAlmostEqual(float(probabilities[1]), 0.9, places=5)

    def test_evidence_dedup_keeps_highest_scoring_unique_items(self):
        results = [
            {"rank": 1, "id": "a", "score": 0.9, "title": "Same", "text": "Repeated evidence 123"},
            {"rank": 2, "id": "b", "score": 0.8, "title": "Same", "text": "Repeated evidence 456"},
            {"rank": 3, "id": "c", "score": 0.7, "title": "Different", "text": "Other evidence"},
        ]
        deduped = deduplicate_evidence_results(results, top_k=3)
        self.assertEqual([item["id"] for item in deduped], ["a", "c"])
        self.assertEqual([item["rank"] for item in deduped], [1, 2])

    def test_bm25_tokenization_and_scoring(self):
        docs = [
            tokenize_for_bm25("奖学金 验证码 银行卡"),
            tokenize_for_bm25("normal campus activity"),
        ]
        bm25 = BM25Index(docs)
        scores = bm25.get_scores(tokenize_for_bm25("银行卡验证码"))
        self.assertGreater(scores[0], scores[1])


if __name__ == "__main__":
    unittest.main()
