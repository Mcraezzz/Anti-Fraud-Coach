from __future__ import annotations

import json
from collections import Counter
from typing import Any

from app.core.config import DATA_DIR


QUESTION_FILE = DATA_DIR / "training_questions.json"


def _load_questions() -> list[dict[str, Any]]:
    return json.loads(QUESTION_FILE.read_text(encoding="utf-8"))


def get_training_questions() -> list[dict[str, Any]]:
    safe_questions = []
    for question in _load_questions():
        safe_questions.append(
            {
                "id": question["id"],
                "title": question["title"],
                "scene": question["scene"],
                "difficulty": question["difficulty"],
                "prompt": question["prompt"],
                "options": question["options"],
            }
        )
    return safe_questions


def grade_training(answers: dict[str, str]) -> dict[str, Any]:
    questions = _load_questions()
    total = len(questions)
    correct = 0
    feedback: list[dict[str, Any]] = []
    missed = Counter()
    radar = {
        "风险识别": 60,
        "核实意识": 60,
        "证据保存": 60,
        "隐私保护": 60,
        "平台意识": 60,
    }

    for question in questions:
        selected = answers.get(question["id"], "")
        is_correct = selected == question["answer"]
        if is_correct:
            correct += 1
            for key in question.get("abilities", []):
                radar[key] = min(100, radar.get(key, 60) + 8)
        else:
            missed[question["scene"]] += 1
            for key in question.get("abilities", []):
                radar[key] = max(35, radar.get(key, 60) - 6)

        feedback.append(
            {
                "id": question["id"],
                "title": question["title"],
                "scene": question["scene"],
                "selected": selected,
                "correct": question["answer"],
                "is_correct": is_correct,
                "explanation": question["explanation"],
                "risk_points": question["risk_points"],
            }
        )

    score = round(correct / total * 100) if total else 0
    weak_types = [item for item, _ in missed.most_common(3)]

    return {
        "total": total,
        "correct": correct,
        "score": score,
        "feedback": feedback,
        "weak_types": weak_types,
        "radar": radar,
    }
