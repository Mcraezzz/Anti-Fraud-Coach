from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.services.ocr_service import OcrRegion, mask_sensitive_text, restore_chat_timeline
from app.services import risk_rules


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_high_risk():
    response = client.post(
        "/api/analyze",
        json={"content": "刷单任务需要先垫付保证金，马上加微信私聊，不要告诉别人。", "input_type": "text"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["risk_level"] == "高风险"
    assert body["scam_type"] == "刷单返利"
    assert body["signals"]
    assert body["confidence"] >= 80
    assert any(item["signal_id"] == "rebate_task_flow" for item in body["signals"])
    assert "【风险:" not in body["highlighted_text"]
    assert any(item["risk"] and "保证金" in item["text"] for item in body["highlighted_segments"])


def test_fake_customer_service_flow():
    response = client.post(
        "/api/analyze",
        json={"content": "我是平台客服，你的订单异常需要退款，请加微信并打开屏幕共享，提供验证码。", "input_type": "text"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["risk_level"] == "高风险"
    assert body["scam_type"] == "冒充客服"
    assert any(item["signal_id"] == "fake_service_flow" for item in body["signals"])


def test_url_classifier_model_flow():
    response = client.post(
        "/api/analyze",
        json={"content": "请打开 http://login-verify-pay.xyz/account?password=123 处理账户冻结", "input_type": "link"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["risk_level"] == "高风险"
    assert body["scam_type"] == "可疑链接/仿冒页面"
    assert any(item["model"] == "URL分类模型" and item["status"] == "ok" for item in body["model_insights"])
    assert any(item["signal_id"].startswith("url_model_") for item in body["signals"])


@pytest.mark.parametrize(
    ("content", "expected_type", "min_score"),
    [
        ("同学你好，学校周边商家招线上兼职，手机操作即可，点赞关注一单3元，做完立返，不收任何费用，有兴趣加群。", "刷单返利", 45),
        ("本公司招聘校园推广员，无需经验，日结200—500元，名额有限，先交99元资料费即可入职。", "虚假兼职", 60),
        ("您好，您大学期间注册过校园贷账号，根据监管要求需要注销，否则将影响个人征信。", "校园贷/注销校园贷", 25),
        ("您好，您购买的商品被检测出质量问题，平台将给您三倍赔偿，请点击链接填写银行卡信息。", "冒充客服", 60),
        ("我是辅导员，现在学校临时统计助学金信息，请把身份证号、银行卡号和验证码发给我。", "冒充熟人/AI换脸", 50),
        ("你名下银行卡涉嫌洗钱案件，请保持电话畅通，不得告诉任何人，否则将承担法律责任。", "冒充公检法", 45),
        ("全新平板电脑低价转让，只要市场价一半，先付定金保留名额，不支持平台交易。", "虚假购物/二手交易", 55),
        ("低价出售游戏账号，满级皮肤齐全，先付款后改绑，平台交易手续费太高，直接微信转账。", "网络游戏交易诈骗", 60),
        ("平台周年庆随机发放现金红包，请点击链接领取，需完成实名认证。", "虚假中奖/福利领取", 55),
        ("今天行情很好，你先充值，我帮你操作，错过这次就没有这么好的机会了。", "恋爱交友/杀猪盘", 40),
        ("你的账户收益已到账，但提现前需要缴纳个人所得税和通道费。", "虚假投资理财", 55),
        ("我刚换了微信，这是新号。现在有点急事，能不能先借我800元？", "冒充熟人/AI换脸", 50),
    ],
)
def test_expanded_scam_samples_more_sensitive(monkeypatch, content, expected_type, min_score):
    monkeypatch.setattr(risk_rules, "generate_qwen_advice", lambda _text, _analysis: {"status": "disabled", "detail": "test"})
    body = risk_rules.analyze_text(content, "text")
    assert body["risk_score"] >= min_score
    assert body["risk_level"] in {"中风险", "高风险"}
    assert body["scam_type"] == expected_type


def test_model_status_endpoint():
    response = client.get("/api/models/status")
    assert response.status_code == 200
    body = response.json()
    assert body["url_classifier"]["enabled"] is True
    assert body["macbert"]["available"] is True
    assert body["qwen"]["available"] is True


def test_login_and_account_stats_flow():
    login_response = client.post("/api/auth/login", json={"username": "student", "password": "student123"})
    assert login_response.status_code == 200
    token = login_response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "student"

    questions = client.get("/api/training/questions").json()
    answers = {item["id"]: item["options"][0]["id"] for item in questions}
    submit = client.post("/api/training/submit", json={"answers": answers}, headers=headers)
    assert submit.status_code == 200

    stats = client.get("/api/account/stats", headers=headers)
    assert stats.status_code == 200
    assert stats.json()["training_attempts"] >= 1


def test_admin_account_management_endpoints():
    login_response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert login_response.status_code == 200
    headers = {"Authorization": f"Bearer {login_response.json()['token']}"}

    users = client.get("/api/admin/users", headers=headers)
    assert users.status_code == 200
    assert any(item["username"] == "student" for item in users.json()["users"])

    statistics = client.get("/api/admin/statistics", headers=headers)
    assert statistics.status_code == 200
    assert statistics.json()["user_count"] >= 2


def test_resource_status_includes_local_assets():
    response = client.get("/api/resources")
    assert response.status_code == 200
    body = response.json()
    assert body["models"]
    assert body["datasets"]
    assert body["paddleocr_cache"]["exists"] is True
    assert body["size_cache"]["enabled"] is True
    assert "model_inference" in body


def test_rag_emergency_answer():
    response = client.post("/api/ask", json={"question": "我已经转账了怎么办？"})
    assert response.status_code == 200
    body = response.json()
    assert "保存" in body["answer"]
    assert body["references"]
    assert body["knowledge_version"]["active_version"] == "2026.05-rag-final"
    assert body["retrieval_method"]


def test_rag_case_citation():
    response = client.post("/api/ask", json={"question": "平台客服让我开屏幕共享还要验证码怎么办？"})
    assert response.status_code == 200
    body = response.json()
    assert body["case_citations"]
    assert any("客服" in item["title"] for item in body["case_citations"])


def test_rag_status():
    response = client.get("/api/rag/status")
    assert response.status_code == 200
    body = response.json()
    assert body["knowledge_version"]["active_version"] == "2026.05-rag-final"
    assert body["document_count"] >= 8
    assert body["case_count"] >= 6


def test_admin_dashboard_metrics():
    response = client.get("/api/admin/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["completion_rate"] > 0
    assert body["top_error_types"]
    assert {"wrong_count", "attempt_count", "common_mistake", "action"} <= set(body["top_error_types"][0])
    assert body["high_risk_sample_stats"]["total"] == body["high_risk_cases"]
    assert body["high_risk_sample_stats"]["recent_samples"]
    assert body["education_advice"]
    assert body["education_advice"][0]["actions"]


def test_ocr_status():
    response = client.get("/api/ocr/status")
    assert response.status_code == 200
    body = response.json()
    assert body["engine"] == "PaddleOCR"
    assert "timeline_restore" in body["features"]


def test_sensitive_masking_and_timeline_restore():
    masked, entities = mask_sensitive_text("手机号13812345678，验证码123456，银行卡6222020202020202")
    assert "138****5678" in masked
    assert "验证码 ******" in masked
    assert "6222 **** **** 0202" in masked
    assert {item["type"] for item in entities} >= {"phone", "verification_code", "bank_card"}

    regions = [
        OcrRegion(0, "10:30", 0.99, [[300, 10], [380, 10], [380, 30], [300, 30]]),
        OcrRegion(1, "我是平台客服", 0.96, [[20, 80], [220, 80], [220, 120], [20, 120]]),
        OcrRegion(2, "请提供验证码123456", 0.94, [[20, 126], [280, 126], [280, 166], [20, 166]]),
        OcrRegion(3, "我先核实", 0.95, [[500, 210], [700, 210], [700, 250], [500, 250]]),
    ]
    messages = restore_chat_timeline(regions, {"width": 750, "height": 1000})
    assert messages[0]["speaker"] == "other"
    assert messages[0]["timestamp"] == "10:30"
    assert "验证码 ******" in messages[0]["text"]
    assert messages[1]["speaker"] == "self"


def test_training_submit():
    questions = client.get("/api/training/questions").json()
    answers = {item["id"]: "b" for item in questions}
    response = client.post("/api/training/submit", json={"answers": answers})
    assert response.status_code == 200
    assert response.json()["total"] == 10
