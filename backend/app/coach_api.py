"""Native coach UI API. Reuses existing inference services; stores UI activity in SQLite."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.config import DATA_DIR
from app.services.account_service import resolve_user_from_header
from app.services.ocr_service import process_chat_screenshot
from app.services.rag_service import answer_question
from app.services.risk_rules import analyze_text

router = APIRouter(prefix="/api/coach", tags=["coach"])
SCENARIOS = json.loads((DATA_DIR / "coach_scenarios.json").read_text(encoding="utf-8"))
DIMENSIONS = {"moneyInducement": "金钱诱导", "identityVerify": "身份核验", "stopLoss": "求助止损", "evidenceKeep": "证据保存", "privacyGuard": "隐私保护", "offPlatform": "脱离平台"}
SCENARIO_DIMENSIONS = {"1": ["moneyInducement", "evidenceKeep"], "2": ["moneyInducement", "offPlatform"], "3": ["privacyGuard", "identityVerify"], "4": ["offPlatform", "evidenceKeep"], "5": ["stopLoss", "privacyGuard"], "6": ["identityVerify", "stopLoss"]}
SCAM_SCENARIOS = {"fake_part_time": "1", "rebate_task": "2", "fake_customer_service": "3", "game_trade": "4", "campus_loan": "5", "acquaintance_impersonation": "6"}


@contextmanager
def database():
    path = Path(os.getenv("ANTI_FRAUD_COACH_DB", str(DATA_DIR / "coach.sqlite3")))
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=15)
    connection.row_factory = sqlite3.Row
    try:
        connection.executescript("CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, token TEXT UNIQUE, name TEXT, preferences TEXT); CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,user_id TEXT,kind TEXT,time INTEGER,payload TEXT); CREATE INDEX IF NOT EXISTS coach_event_user ON events(user_id,time); CREATE INDEX IF NOT EXISTS coach_event_user_kind_time ON events(user_id,kind,time DESC);")
        yield connection
        connection.commit()
    finally:
        connection.close()


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def current_user(authorization: str | None = Header(default=None)) -> dict:
    token = (authorization or "").removeprefix("Bearer ")
    with database() as db:
        row = db.execute("SELECT * FROM users WHERE token=?", (digest(token),)).fetchone() if token else None
    if not row:
        raise HTTPException(401, "设备会话已失效，请到个人中心重新连接")
    return dict(row)


def public_user(user: dict) -> dict:
    return {"id": user["id"], "name": user["name"], "preferences": json.loads(user["preferences"])}


def add_event(user: dict, kind: str, payload: dict) -> dict:
    result = {**payload, "id": str(uuid.uuid4()), "timestamp": int(time.time() * 1000)}
    with database() as db:
        db.execute("INSERT INTO events VALUES(?,?,?,?,?)", (result["id"], user["id"], kind, result["timestamp"], json.dumps(result, ensure_ascii=False)))
    return result


def events(user: dict, kind: str, limit: int | None = None) -> list[dict]:
    query = "SELECT payload FROM events WHERE user_id=? AND kind=? ORDER BY time DESC, rowid DESC"
    params: tuple = (user["id"], kind)
    if limit is not None:
        query += " LIMIT ?"
        params += (limit,)
    with database() as db:
        return [json.loads(row[0]) for row in db.execute(query, params)]


def masked(text: str) -> str:
    text = re.sub(r"(?<!\d)(1[3-9]\d)\d{4}(\d{4})(?!\d)", r"\1****\2", text)
    text = re.sub(r"(?<!\d)(\d{6})\d{8}(\d{3}[\dXx])(?!\d)", r"\1********\2", text)
    text = re.sub(r"((?:验证码|密码|动态码)\s*[:：]?\s*)[A-Za-z0-9]{4,20}", r"\1******", text)
    return text


@router.get("/health")
def health():
    return {"ok": True, "engine": "local", "storage": "sqlite"}


@router.post("/session")
def session():
    token, user_id = secrets.token_hex(32), str(uuid.uuid4())
    with database() as db:
        db.execute("INSERT INTO users VALUES(?,?,?,?)", (user_id, digest(token), "校园同学", json.dumps({"autoMaskSensitive": True, "weeklyReminder": True})))
    return {"token": token, "user": {"id": user_id, "name": "校园同学"}}


class ProfileUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=24)
    preferences: dict[str, bool] = Field(default_factory=dict)


@router.get("/profile")
def profile(user: dict = Depends(current_user)):
    return public_user(user)


@router.patch("/profile")
def update_profile(body: ProfileUpdate, user: dict = Depends(current_user)):
    if body.name is not None and not body.name.strip():
        raise HTTPException(422, "昵称不能为空")
    with database() as db:
        # Re-read under the write lock: dependency data may predate another PATCH.
        db.execute("BEGIN IMMEDIATE")
        latest = db.execute("SELECT name,preferences FROM users WHERE id=?", (user["id"],)).fetchone()
        name = body.name.strip() if body.name is not None else latest["name"]
        preferences = json.loads(latest["preferences"])
        preferences.update({k: v for k, v in body.preferences.items() if k in {"autoMaskSensitive", "weeklyReminder"}})
        db.execute("UPDATE users SET name=?,preferences=? WHERE id=?", (name, json.dumps(preferences), user["id"]))
    return {"id": user["id"], "name": name, "preferences": preferences}


class ScanRequest(BaseModel):
    mode: Literal["text", "ocr", "url", "sms"] = "text"
    text: str = Field("", max_length=12000)
    imageBase64: str = Field("", max_length=8 * 1024 * 1024)
    imageMimeType: Literal["image/jpeg", "image/png", "image/webp"] = "image/jpeg"


def adapt_risk(raw: dict, text: str, mode: str) -> dict:
    scam_type = raw.get("scam_type", "未明确类型")
    scenario_id = SCAM_SCENARIOS.get(raw.get("scam_type_id")) or next((s["id"] for s in SCENARIOS if s["title"][:3] in scam_type), "1")
    score = int(raw["risk_score"])
    highlights = [{"quote": s["keyword"], "tag": s["label"], "severity": "high" if s.get("weight", 0) >= 20 else "medium", "explanation": s["explanation"]} for s in raw.get("signals", []) if s.get("keyword") and s["keyword"] in text]
    model_used = any(m.get("status") == "ok" for m in raw.get("model_insights", []))
    return {"mode": mode, "extractedText": text, "riskScore": score, "riskLevel": {"高风险": "high", "中风险": "medium", "低风险": "low"}.get(raw.get("risk_level"), "low"), "scamType": scam_type, "confidence": None, "engine": "local" if model_used else "rules", "signals": [{"label": s["label"], "severity": "high" if s.get("weight", 0) >= 20 else "medium"} for s in raw.get("signal_summary", [])], "highlights": highlights, "summaryAnalysis": raw.get("summary", ""), "actionSteps": raw.get("suggestions", []), "recommendedScenarioId": scenario_id, "modelInsights": raw.get("model_insights", [])}


@router.post("/scan")
def scan(body: ScanRequest, user: dict = Depends(current_user)):
    text = body.text.strip()
    if body.mode == "ocr":
        try:
            image = base64.b64decode(body.imageBase64, validate=True)
        except (ValueError, TypeError):
            raise HTTPException(422, "图片编码无效")
        if not image or len(image) > 6 * 1024 * 1024:
            raise HTTPException(422, "请选择不超过 6MB 的图片")
        try:
            ocr = process_chat_screenshot(image)
        except Exception:
            raise HTTPException(503, "本地 OCR 暂不可用，请检查 OCR 模型与依赖，或粘贴图片中的文字")
        text = ocr.get("sanitized_text", "").strip()
        if not text:
            raise HTTPException(422, "未识别出可分析的文字，请换一张清晰截图")
    if not text:
        raise HTTPException(422, "请输入待检测内容")
    if body.mode == "url" and not re.fullmatch(r"https?://\S+", text):
        raise HTTPException(422, "请输入完整的 http 或 https 链接")
    if json.loads(user["preferences"])["autoMaskSensitive"]:
        text = masked(text)
    raw = analyze_text(text, {"url": "link", "ocr": "screenshot_ocr"}.get(body.mode, body.mode))
    return add_event(user, "scan", adapt_risk(raw, text, body.mode))


@router.get("/history")
def history(user: dict = Depends(current_user)):
    return events(user, "scan", limit=50)


@router.delete("/history")
def clear_history(user: dict = Depends(current_user)):
    with database() as db:
        db.execute("DELETE FROM events WHERE user_id=? AND kind='scan'", (user["id"],))
    return {"ok": True}


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class AskRequest(BaseModel):
    messages: list[Message] = Field(..., min_length=1, max_length=12)


@router.post("/qa")
def ask(body: AskRequest, user: dict = Depends(current_user)):
    last = body.messages[-1]
    if last.role != "user" or not last.content.strip():
        raise HTTPException(422, "请输入需要咨询的问题")
    # Existing RAG service accepts a standalone question. Do not imply multi-turn memory.
    result = answer_question(masked(last.content.strip()))
    return {"answer": result["answer"], "references": result.get("references", []), "signals": [], "verdict": "info", "engine": "rag", "retrievalMethod": result.get("retrieval_method", "lexical")}


@router.get("/scenarios")
def scenario_list(user: dict = Depends(current_user)):
    return [{**s, "turns": [{**t, "actions": [{"id": a["id"], "label": a["label"]} for a in t["actions"]]} for t in s["turns"]]} for s in SCENARIOS]


class TrainingRequest(BaseModel):
    answers: list[str] = Field(..., min_length=1, max_length=20)


@router.post("/training/{scenario_id}")
def training(scenario_id: str, body: TrainingRequest, user: dict = Depends(current_user)):
    scenario = next((s for s in SCENARIOS if s["id"] == scenario_id), None)
    if not scenario:
        raise HTTPException(404, "训练情景不存在")
    if len(body.answers) != len(scenario["turns"]):
        raise HTTPException(422, "请完成全部对话选择")
    feedback = []
    for turn, answer in zip(scenario["turns"], body.answers):
        action = next((a for a in turn["actions"] if a["id"] == answer), None)
        if not action:
            raise HTTPException(422, "存在无效的训练选项")
        feedback.append({**action, "turnId": turn["id"]})
    score = round(sum(a["scoreDelta"] for a in feedback) / len(feedback))
    return add_event(user, "training", {"scenarioId": scenario_id, "title": scenario["title"], "score": score, "completed": score >= 80, "feedback": feedback})


@router.get("/report")
def report(user: dict = Depends(current_user)):
    # Count in SQLite instead of decoding every potentially large OCR/scan payload.
    with database() as db:
        scan_stats = db.execute("SELECT COUNT(*), COALESCE(SUM(json_extract(payload, '$.riskLevel') != 'low'), 0) FROM events WHERE user_id=? AND kind='scan'", (user["id"],)).fetchone()
    trainings = events(user, "training")
    progress = {}
    for t in reversed(trainings):
        previous = progress.get(t["scenarioId"], {"bestScore": 0, "attempts": 0, "completed": False})
        progress[t["scenarioId"]] = {"bestScore": max(previous["bestScore"], t["score"]), "lastScore": t["score"], "attempts": previous["attempts"] + 1, "completed": previous["completed"] or t["completed"]}
    radar = []
    for key, label in DIMENSIONS.items():
        scores = [t["score"] for t in trainings if key in SCENARIO_DIMENSIONS.get(t["scenarioId"], [])]
        radar.append({"key": key, "label": label, "score": round(sum(scores) / len(scores)) if scores else None})
    completed = sum(p["completed"] for p in progress.values())
    weaknesses = [{"id": s["id"], "title": s["title"], "score": progress.get(s["id"], {}).get("lastScore")} for s in SCENARIOS]
    weaknesses.sort(key=lambda s: s["score"] if s["score"] is not None else -1)
    return {"scanCount": scan_stats[0], "riskCount": scan_stats[1], "trainingCount": len(trainings), "completed": completed, "completion": round(completed / len(SCENARIOS) * 100), "safetyScore": round(sum(t["score"] for t in trainings) / len(trainings)) if trainings else None, "progress": progress, "radar": radar, "weaknesses": weaknesses[:3], "recentTraining": trainings[:10]}


@router.delete("/training")
def reset_training(user: dict = Depends(current_user)):
    with database() as db:
        db.execute("DELETE FROM events WHERE user_id=? AND kind='training'", (user["id"],))
    return {"ok": True}


@router.get("/admin")
def admin(user: dict = Depends(current_user), x_admin_token: str | None = Header(default=None)):
    admin_user = resolve_user_from_header("Bearer " + x_admin_token) if x_admin_token else None
    if not admin_user or admin_user.get("role") != "admin":
        raise HTTPException(403, "需要管理员账号")
    with database() as db:
        rows = [(r["kind"], r["time"], json.loads(r["payload"])) for r in db.execute("SELECT * FROM events ORDER BY time DESC")]
        count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        training_rows = [(r["user_id"], json.loads(r["payload"])) for r in db.execute("SELECT user_id,payload FROM events WHERE kind=\'training\'")]
    scans = [p for kind, _, p in rows if kind == "scan"]
    trainings = [p for kind, _, p in rows if kind == "training"]
    distribution: dict[str, int] = {}
    for s in scans:
        distribution[s["scamType"]] = distribution.get(s["scamType"], 0) + 1
    trained_rate = round(len({uid for uid, _ in training_rows}) / count * 100) if count else 0
    completion = [{"id": s["id"], "shortTitle": s["title"][:2], "rate": round(len({uid for uid, p in training_rows if p["scenarioId"] == s["id"] and p["completed"]}) / count * 100) if count else 0} for s in SCENARIOS]
    return {"trainedRate": trained_rate, "scenarioCompletion": completion, "userCount": count, "scanCount": len(scans), "riskCount": sum(s["riskLevel"] == "high" for s in scans), "trainingCount": len(trainings), "averageScore": round(sum(t["score"] for t in trainings) / len(trainings)) if trainings else None, "distribution": [{"label": k, "count": v} for k, v in distribution.items()], "recent": [{"time": timestamp, "kind": kind, "title": p.get("scamType", p.get("title", "")), "score": p.get("riskScore", p.get("score", 0))} for kind, timestamp, p in rows[:12]]}
