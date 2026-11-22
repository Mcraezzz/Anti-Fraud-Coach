from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from app.core.config import DATA_DIR


TRAINING_FILE = DATA_DIR / "training_questions.json"
CASE_FILE = DATA_DIR / "fraud_cases.json"


SCENE_ERROR_PROFILE = {
    "刷单返利": {"attempts": 48, "wrong": 18, "common_mistake": "容易被小额返利和连续任务诱导，忽视先垫付风险。"},
    "冒充客服": {"attempts": 44, "wrong": 16, "common_mistake": "对退款、理赔和验证码索取的组合风险识别不足。"},
    "虚假兼职": {"attempts": 39, "wrong": 14, "common_mistake": "将培训费、保证金误认为正规兼职流程。"},
    "校园贷/套路贷": {"attempts": 31, "wrong": 11, "common_mistake": "对刷流水、解冻费和身份信息索取警惕不够。"},
    "游戏交易诈骗": {"attempts": 28, "wrong": 8, "common_mistake": "低估私下交易和陌生担保链接的资金风险。"},
    "冒充熟人": {"attempts": 34, "wrong": 9, "common_mistake": "看到熟人头像后没有进行电话或视频核实。"},
    "链接安全": {"attempts": 26, "wrong": 7, "common_mistake": "对陌生链接中的账号密码和验证码输入风险认识不足。"},
    "应急处置": {"attempts": 22, "wrong": 6, "common_mistake": "转账后没有第一时间保留证据、止付和报警。"},
}


SAMPLE_PROFILE = {
    "刷单返利": {"count": 7, "pending": 2, "avg_score": 91, "channel": "兼职群截图"},
    "冒充客服": {"count": 6, "pending": 2, "avg_score": 88, "channel": "短信/OCR截图"},
    "虚假兼职": {"count": 4, "pending": 1, "avg_score": 84, "channel": "招聘私信"},
    "校园贷": {"count": 3, "pending": 1, "avg_score": 86, "channel": "可疑链接"},
    "游戏交易": {"count": 2, "pending": 0, "avg_score": 82, "channel": "游戏交易聊天"},
    "冒充熟人": {"count": 1, "pending": 0, "avg_score": 79, "channel": "社交账号私信"},
}


def _load_json(path: Any) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_scene(scene: str) -> str:
    if "刷单" in scene:
        return "刷单返利"
    if "客服" in scene:
        return "冒充客服"
    if "兼职" in scene:
        return "虚假兼职"
    if "校园贷" in scene or "套路贷" in scene:
        return "校园贷/套路贷"
    if "游戏" in scene:
        return "游戏交易诈骗"
    if "熟人" in scene:
        return "冒充熟人"
    if "链接" in scene:
        return "链接安全"
    if "应急" in scene:
        return "应急处置"
    return scene


def _load_training_questions() -> list[dict[str, Any]]:
    return _load_json(TRAINING_FILE)


def _load_cases() -> list[dict[str, Any]]:
    return _load_json(CASE_FILE)


def _build_top_error_types(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scene_question_count = Counter(_normalize_scene(item["scene"]) for item in questions)
    scene_difficulty = defaultdict(list)
    for question in questions:
        scene_difficulty[_normalize_scene(question["scene"])].append(question["difficulty"])

    rows = []
    for scene, question_count in scene_question_count.items():
        profile = SCENE_ERROR_PROFILE.get(scene, {"attempts": 24, "wrong": 6, "common_mistake": "该类型仍需通过案例复盘强化识别。"})
        attempts = profile["attempts"]
        wrong = profile["wrong"]
        error_rate = round(wrong / attempts * 100) if attempts else 0
        priority = "高" if error_rate >= 34 else "中" if error_rate >= 25 else "低"
        rows.append(
            {
                "label": scene,
                "value": error_rate,
                "wrong_count": wrong,
                "attempt_count": attempts,
                "question_count": question_count,
                "difficulty": "、".join(sorted(set(scene_difficulty[scene]))),
                "priority": priority,
                "common_mistake": profile["common_mistake"],
                "action": _scene_action(scene),
            }
        )
    return sorted(rows, key=lambda item: (item["value"], item["wrong_count"]), reverse=True)


def _scene_action(scene: str) -> str:
    actions = {
        "刷单返利": "安排刷单返利闯关题，重点讲清先小额返利、后大额垫付的链路。",
        "冒充客服": "组织退款理赔案例复盘，要求学生演练官方渠道核验流程。",
        "虚假兼职": "结合就业指导课讲解正规兼职流程，强调任何入职前收费都需警惕。",
        "校园贷/套路贷": "联合资助中心讲解正规助学渠道，提示不要刷流水和提交隐私材料。",
        "游戏交易诈骗": "提醒学生坚持官方交易平台，不点击陌生担保链接。",
        "冒充熟人": "设计电话、视频、共同联系人三步核验训练。",
        "链接安全": "开展钓鱼链接识别训练，强调账号密码和验证码不能在陌生页面输入。",
        "应急处置": "发放转账后处置清单，训练证据保存、平台止付和报警流程。",
    }
    return actions.get(scene, "补充同类案例训练，并在班会中复盘错误原因。")


def _build_high_risk_sample_stats(cases: list[dict[str, Any]]) -> dict[str, Any]:
    by_type = []
    total = 0
    pending = 0
    for label, profile in SAMPLE_PROFILE.items():
        count = profile["count"]
        total += count
        pending += profile["pending"]
        by_type.append(
            {
                "label": label,
                "count": count,
                "avg_score": profile["avg_score"],
                "pending_review": profile["pending"],
                "channel": profile["channel"],
            }
        )

    recent_samples = []
    now = datetime(2026, 5, 24, 9, 30)
    for index, case in enumerate(cases[:6], start=1):
        category = _normalize_case_category(case["category"])
        profile = SAMPLE_PROFILE.get(category, {"avg_score": 82, "channel": "学生上报"})
        detected_at = now - timedelta(hours=index * 7)
        recent_samples.append(
            {
                "sample_id": f"HR-{20260500 + index}",
                "scam_type": category,
                "risk_score": max(76, profile["avg_score"] - index % 4),
                "risk_level": "高风险" if profile["avg_score"] >= 84 else "中风险",
                "channel": profile["channel"],
                "detected_at": detected_at.strftime("%Y-%m-%d %H:%M"),
                "summary": case["title"],
                "risk_points": case.get("risk_points", [])[:4],
                "status": "待复核" if index in {1, 3, 4} else "已归档",
            }
        )

    trend = [
        {"date": "05-18", "count": 2},
        {"date": "05-19", "count": 4},
        {"date": "05-20", "count": 3},
        {"date": "05-21", "count": 5},
        {"date": "05-22", "count": 4},
        {"date": "05-23", "count": 3},
        {"date": "05-24", "count": 2},
    ]
    return {
        "total": total,
        "today_new": trend[-1]["count"],
        "pending_review": pending,
        "verified": total - pending,
        "by_type": sorted(by_type, key=lambda item: item["count"], reverse=True),
        "trend": trend,
        "recent_samples": recent_samples,
    }


def _normalize_case_category(category: str) -> str:
    if "刷单" in category:
        return "刷单返利"
    if "客服" in category:
        return "冒充客服"
    if "兼职" in category:
        return "虚假兼职"
    if "校园贷" in category:
        return "校园贷"
    if "游戏" in category:
        return "游戏交易"
    if "熟人" in category:
        return "冒充熟人"
    return category


def _build_education_advice(top_errors: list[dict[str, Any]], sample_stats: dict[str, Any]) -> list[dict[str, Any]]:
    advice = []
    for index, item in enumerate(top_errors[:3], start=1):
        advice.append(
            {
                "priority": item["priority"],
                "title": f"{item['label']}专项强化",
                "target": f"错误率 {item['value']}%，错题 {item['wrong_count']} 次",
                "reason": item["common_mistake"],
                "actions": [
                    item["action"],
                    "课后推送 3 道同类情景题，要求学生写出风险点和核验动作。",
                    "辅导员后台跟踪完成率，对连续两次误判学生进行单独提醒。",
                ],
            }
        )

    if sample_stats["pending_review"] > 0:
        advice.append(
            {
                "priority": "高",
                "title": "高风险样本复核",
                "target": f"{sample_stats['pending_review']} 条样本待复核",
                "reason": "近期学生上报样本中仍存在未归档的高风险聊天、链接或截图。",
                "actions": [
                    "优先复核待处理样本，提取典型话术加入训练题库。",
                    "对同班级或同群聊来源的重复样本进行集中预警。",
                    "将已脱敏案例同步到 RAG 知识库，形成可引用案例。",
                ],
            }
        )
    return advice


def get_admin_dashboard() -> dict[str, Any]:
    questions = _load_training_questions()
    cases = _load_cases()
    top_error_types = _build_top_error_types(questions)
    sample_stats = _build_high_risk_sample_stats(cases)
    education_advice = _build_education_advice(top_error_types, sample_stats)
    completed_students = 134
    total_students = 156

    return {
        "average_score": 82,
        "training_count": 128,
        "total_students": total_students,
        "completed_students": completed_students,
        "completion_rate": round(completed_students / total_students * 100),
        "high_risk_cases": sample_stats["total"],
        "top_error_types": top_error_types,
        "high_risk_sample_stats": sample_stats,
        "education_advice": education_advice,
        "radar": {
            "风险识别": 84,
            "核实意识": 76,
            "证据保存": 69,
            "隐私保护": 81,
            "平台意识": 73,
        },
        "updated_at": "2026-05-24 09:30",
    }
