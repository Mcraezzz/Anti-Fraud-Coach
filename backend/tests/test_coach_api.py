"""New UI flow tests: isolated SQLite, no real accounts or local model downloads."""
import base64
import os

for key in ("ANTI_FRAUD_SEMANTIC_RAG", "ANTI_FRAUD_URL_CLASSIFIER", "ANTI_FRAUD_MACBERT_ENABLED", "ANTI_FRAUD_MACBERT_FRAUD_CLASSIFIER", "ANTI_FRAUD_OCR_PRELOAD", "ANTI_FRAUD_QWEN_ENABLED"):
    os.environ[key] = "0"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app import coach_api as coach


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTI_FRAUD_COACH_DB", str(tmp_path / "test.sqlite3"))
    app = FastAPI()
    app.include_router(coach.router)
    with TestClient(app) as client:
        yield client


def session(client):
    response = client.post("/api/coach/session")
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["token"]}


def test_scan_history_isolation_and_clear(client):
    one, two = session(client), session(client)
    response = client.post("/api/coach/scan", headers=one, json={"mode": "text", "text": "我是平台客服，请开屏幕共享并提供验证码123456，手机号13812345678"})
    assert response.status_code == 200
    result = response.json()
    assert result["riskLevel"] == "high"
    assert "12345678" not in result["extractedText"]
    assert "验证码123456" not in result["extractedText"]
    assert all(h["quote"] in result["extractedText"] for h in result["highlights"])
    assert len(client.get("/api/coach/history", headers=one).json()) == 1
    assert client.get("/api/coach/history", headers=two).json() == []
    assert client.get("/api/coach/report", headers=one).json()["scanCount"] == 1
    client.delete("/api/coach/history", headers=one)
    assert client.get("/api/coach/report", headers=one).json()["scanCount"] == 0


def test_scenario_answers_are_hidden_and_server_scores(client):
    headers = session(client)
    scenarios = client.get("/api/coach/scenarios", headers=headers).json()
    assert len(scenarios) == 6
    assert set(scenarios[0]["turns"][0]["actions"][0]) == {"id", "label"}
    assert client.get("/api/coach/report", headers=headers).json()["safetyScore"] is None
    for scenario in coach.SCENARIOS:
        answers = [max(t["actions"], key=lambda a: a["scoreDelta"])["id"] for t in scenario["turns"]]
        result = client.post(f'/api/coach/training/{scenario["id"]}', headers=headers, json={"answers": answers, "score": 0})
        assert result.status_code == 200
        assert result.json()["score"] == 100
    report = client.get("/api/coach/report", headers=headers).json()
    assert report["completed"] == 6 and report["completion"] == 100
    assert report["safetyScore"] == 100
    assert all(row["score"] == 100 for row in report["radar"])
    invalid = client.post("/api/coach/training/1", headers=headers, json={"answers": ["made-up"]})
    assert invalid.status_code == 422
    assert client.get("/api/coach/report", headers=headers).json()["trainingCount"] == 6


def test_validation_profile_and_admin_permissions(client, monkeypatch):
    assert client.get("/api/coach/report").status_code == 401
    headers = session(client)
    for payload in [{"text": " "}, {"mode": "url", "text": "not a URL"}, {"mode": "ocr", "imageBase64": "???"}, {"mode": "wrong"}]:
        assert client.post("/api/coach/scan", headers=headers, json=payload).status_code == 422
    assert client.patch("/api/coach/profile", headers=headers, json={"name": "  "}).status_code == 422
    assert client.patch("/api/coach/profile", headers=headers, json={"name": "测试同学", "preferences": {"weeklyReminder": False}}).json()["name"] == "测试同学"
    assert client.get("/api/coach/profile", headers=headers).json()["preferences"]["weeklyReminder"] is False
    assert client.get("/api/coach/admin", headers=headers).status_code == 403
    monkeypatch.setattr(coach, "resolve_user_from_header", lambda _: {"role": "student"})
    assert client.get("/api/coach/admin", headers={**headers, "X-Admin-Token": "student"}).status_code == 403
    monkeypatch.setattr(coach, "resolve_user_from_header", lambda _: {"role": "admin"})
    assert client.get("/api/coach/admin", headers={**headers, "X-Admin-Token": "admin"}).json()["userCount"] == 1


def test_ocr_unavailable_is_explicit(client, monkeypatch):
    def unavailable(_):
        raise RuntimeError("model missing")
    monkeypatch.setattr(coach, "process_chat_screenshot", unavailable)
    response = client.post("/api/coach/scan", headers=session(client), json={"mode": "ocr", "imageBase64": base64.b64encode(b"fake image").decode()})
    assert response.status_code == 503 and "OCR" in response.json()["detail"]


def test_qa_uses_existing_knowledge_service(client):
    headers = session(client)
    response = client.post("/api/coach/qa", headers=headers, json={"messages": [{"role": "user", "content": "兼职让我先交保证金怎么办？"}]})
    assert response.status_code == 200
    assert response.json()["answer"] and response.json()["references"]
    assert response.json()["engine"] == "rag"
    assert client.post("/api/coach/qa", headers=headers, json={"messages": []}).status_code == 422


def test_ocr_success_is_saved(client, monkeypatch):
    monkeypatch.setattr(coach, "process_chat_screenshot", lambda _: {"sanitized_text": "客服让我打开屏幕共享，提供验证码"})
    headers = session(client)
    response = client.post("/api/coach/scan", headers=headers, json={"mode": "ocr", "imageBase64": base64.b64encode(b"fixture image").decode()})
    assert response.status_code == 200
    assert response.json()["mode"] == "ocr"
    assert len(client.get("/api/coach/history", headers=headers).json()) == 1


def test_training_reset_is_isolated_and_dashboard_is_real(client, monkeypatch):
    first, second = session(client), session(client)
    scenario = coach.SCENARIOS[0]
    answers = [max(t["actions"], key=lambda a: a["scoreDelta"])["id"] for t in scenario["turns"]]
    for headers in (first, second):
        assert client.post("/api/coach/training/1", headers=headers, json={"answers": answers}).status_code == 200
    assert client.delete("/api/coach/training").status_code == 401
    assert client.delete("/api/coach/training", headers=first).status_code == 200
    assert client.get("/api/coach/report", headers=first).json()["safetyScore"] is None
    assert client.get("/api/coach/report", headers=second).json()["completed"] == 1
    monkeypatch.setattr(coach, "resolve_user_from_header", lambda _: {"role": "admin"})
    dashboard = client.get("/api/coach/admin", headers={**first, "X-Admin-Token": "test"}).json()
    assert dashboard["trainedRate"] == 50
    assert dashboard["scenarioCompletion"][0]["rate"] == 50
    assert all(item["rate"] == 0 for item in dashboard["scenarioCompletion"][1:])


def test_history_limit_preserves_full_report_counts_and_same_time_order(client, monkeypatch):
    headers, other = session(client), session(client)
    user = coach.current_user(headers["Authorization"])
    monkeypatch.setattr(coach.time, "time", lambda: 1234567)
    for index in range(75):
        coach.add_event(user, "scan", {"riskLevel": "high" if index % 2 else "low", "extractedText": str(index)})
    history = client.get("/api/coach/history", headers=headers).json()
    assert len(history) == 50
    assert [item["extractedText"] for item in history] == [str(i) for i in range(74, 24, -1)]
    report = client.get("/api/coach/report", headers=headers).json()
    assert report["scanCount"] == 75
    assert report["riskCount"] == 37
    assert client.get("/api/coach/report", headers=other).json()["scanCount"] == 0


def test_profile_patch_merges_against_latest_saved_values(client):
    headers = session(client)
    stale_user = coach.current_user(headers["Authorization"])
    coach.update_profile(coach.ProfileUpdate(name="新昵称", preferences={"weeklyReminder": False}), stale_user)
    # Both requests may have authenticated before either update committed.
    coach.update_profile(coach.ProfileUpdate(preferences={"autoMaskSensitive": False}), stale_user)
    actual = client.get("/api/coach/profile", headers=headers).json()
    assert actual["name"] == "新昵称"
    assert actual["preferences"] == {"weeklyReminder": False, "autoMaskSensitive": False}


@pytest.mark.parametrize("scam_id,expected", list(coach.SCAM_SCENARIOS.items()))
def test_training_recommendation_uses_stable_category_id(scam_id, expected):
    raw = {"scam_type_id": scam_id, "scam_type": "更新后的显示名称", "risk_score": 75, "risk_level": "高风险"}
    assert coach.adapt_risk(raw, "待检测文字", "text")["recommendedScenarioId"] == expected
