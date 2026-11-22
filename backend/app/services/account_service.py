from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from app.core.config import DATA_DIR, settings


ACCOUNT_FILE = DATA_DIR / "accounts.json"
TOKEN_TTL_HOURS = 24 * 7


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


def _make_user(
    user_id: str,
    username: str,
    password: str,
    display_name: str,
    role: str,
    class_name: str = "",
    student_no: str = "",
) -> dict[str, Any]:
    salt = secrets.token_hex(8)
    return {
        "user_id": user_id,
        "username": username,
        "display_name": display_name,
        "role": role,
        "class_name": class_name,
        "student_no": student_no,
        "avatar": "",
        "salt": salt,
        "password_hash": _hash_password(password, salt),
        "created_at": _now(),
        "last_login_at": "",
    }


def _default_store() -> dict[str, Any]:
    return {
        "users": [
            _make_user("u_student_demo", "student", "student123", "学生演示账号", "student", "人工智能 2301 班", "20230001"),
            _make_user("u_admin_demo", "admin", "admin123", "辅导员管理员", "admin", "人工智能学院", "A0001"),
        ],
        "events": [],
    }


def _read_store() -> dict[str, Any]:
    if not ACCOUNT_FILE.exists():
        store = _default_store()
        _write_store(store)
        return store
    try:
        store = json.loads(ACCOUNT_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        store = _default_store()
        _write_store(store)
    store.setdefault("users", [])
    store.setdefault("events", [])
    _ensure_demo_users(store)
    return store


def _write_store(store: dict[str, Any]) -> None:
    ACCOUNT_FILE.parent.mkdir(parents=True, exist_ok=True)
    ACCOUNT_FILE.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


def _ensure_demo_users(store: dict[str, Any]) -> None:
    usernames = {user.get("username") for user in store.get("users", [])}
    changed = False
    if "student" not in usernames:
        store["users"].append(_make_user("u_student_demo", "student", "student123", "学生演示账号", "student", "人工智能 2301 班", "20230001"))
        changed = True
    if "admin" not in usernames:
        store["users"].append(_make_user("u_admin_demo", "admin", "admin123", "辅导员管理员", "admin", "人工智能学院", "A0001"))
        changed = True
    if changed:
        _write_store(store)


def _public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "display_name": user.get("display_name", user["username"]),
        "role": user.get("role", "student"),
        "class_name": user.get("class_name", ""),
        "student_no": user.get("student_no", ""),
        "avatar": user.get("avatar", ""),
        "created_at": user.get("created_at", ""),
        "last_login_at": user.get("last_login_at", ""),
    }


def _sign(payload: str) -> str:
    return hmac.new(settings.auth_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def _issue_token(user: dict[str, Any]) -> str:
    expires_at = int((datetime.now() + timedelta(hours=TOKEN_TTL_HOURS)).timestamp())
    payload = f"{user['user_id']}:{user.get('role', 'student')}:{expires_at}"
    signed = f"{payload}:{_sign(payload)}"
    return base64.urlsafe_b64encode(signed.encode("utf-8")).decode("ascii")


def _verify_token(token: str) -> dict[str, Any] | None:
    try:
        signed = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        user_id, role, expires_at, signature = signed.rsplit(":", 3)
        payload = f"{user_id}:{role}:{expires_at}"
    except Exception:
        return None
    if not hmac.compare_digest(signature, _sign(payload)):
        return None
    if int(expires_at) < int(datetime.now().timestamp()):
        return None
    store = _read_store()
    user = next((item for item in store["users"] if item.get("user_id") == user_id), None)
    if not user:
        return None
    return _public_user(user)


def login(username: str, password: str) -> dict[str, Any] | None:
    store = _read_store()
    user = next((item for item in store["users"] if item.get("username") == username), None)
    if not user:
        return None
    expected = _hash_password(password, user.get("salt", ""))
    if not hmac.compare_digest(expected, user.get("password_hash", "")):
        return None
    user["last_login_at"] = _now()
    _write_store(store)
    public = _public_user(user)
    record_activity(public, "login", {"role": public["role"]})
    return {"token": _issue_token(user), "user": public}


def resolve_user_from_header(authorization: str | None) -> dict[str, Any] | None:
    if not authorization:
        return None
    prefix = "Bearer "
    token = authorization[len(prefix) :] if authorization.startswith(prefix) else authorization
    return _verify_token(token.strip())


def update_profile(user_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {"display_name", "class_name", "student_no", "avatar"}
    store = _read_store()
    user = next((item for item in store["users"] if item.get("user_id") == user_id), None)
    if not user:
        return None
    for key, value in fields.items():
        if key in allowed and value is not None:
            user[key] = str(value).strip()
    _write_store(store)
    return _public_user(user)


def record_activity(user: dict[str, Any] | None, event_type: str, payload: dict[str, Any]) -> None:
    store = _read_store()
    event = {
        "event_id": f"EV-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(3)}",
        "user_id": user.get("user_id") if user else "guest",
        "role": user.get("role") if user else "guest",
        "type": event_type,
        "created_at": _now(),
        "payload": payload,
    }
    store["events"].append(event)
    if len(store["events"]) > 1000:
        store["events"] = store["events"][-1000:]
    _write_store(store)


def _events_for_user(user_id: str) -> list[dict[str, Any]]:
    return [event for event in _read_store().get("events", []) if event.get("user_id") == user_id]


def get_account_stats(user: dict[str, Any]) -> dict[str, Any]:
    events = _events_for_user(user["user_id"])
    training_events = [event for event in events if event.get("type") == "training_submit"]
    analysis_events = [event for event in events if event.get("type") in {"risk_analysis", "ocr_analysis"}]
    scores = [int(event["payload"].get("score", 0)) for event in training_events]
    weak_counter = Counter()
    radar_totals: defaultdict[str, list[int]] = defaultdict(list)
    risk_levels = Counter()
    scam_types = Counter()

    for event in training_events:
        payload = event.get("payload", {})
        weak_counter.update(payload.get("weak_types", []))
        for key, value in payload.get("radar", {}).items():
            radar_totals[key].append(int(value))

    for event in analysis_events:
        payload = event.get("payload", {})
        risk_levels.update([payload.get("risk_level", "未知")])
        scam_types.update([payload.get("scam_type", "未明确类型")])

    radar = {
        "风险识别": 60,
        "核实意识": 60,
        "证据保存": 60,
        "隐私保护": 60,
        "平台意识": 60,
    }
    for key, values in radar_totals.items():
        radar[key] = round(sum(values) / len(values)) if values else radar.get(key, 60)

    recent = sorted(events, key=lambda item: item.get("created_at", ""), reverse=True)[:8]
    return {
        "user": user,
        "training_attempts": len(training_events),
        "average_score": round(sum(scores) / len(scores)) if scores else 0,
        "best_score": max(scores) if scores else 0,
        "completed_questions": sum(int(event["payload"].get("total", 0)) for event in training_events),
        "detection_count": len(analysis_events),
        "high_risk_count": risk_levels.get("高风险", 0),
        "risk_level_distribution": dict(risk_levels),
        "top_scam_types": [{"label": label, "count": count} for label, count in scam_types.most_common(5)],
        "weak_types": [{"label": label, "count": count} for label, count in weak_counter.most_common(5)],
        "radar": radar,
        "recent_activity": recent,
    }


def list_users() -> list[dict[str, Any]]:
    store = _read_store()
    rows = []
    for user in store["users"]:
        public = _public_user(user)
        stats = get_account_stats(public)
        rows.append(
            {
                **public,
                "training_attempts": stats["training_attempts"],
                "average_score": stats["average_score"],
                "detection_count": stats["detection_count"],
                "high_risk_count": stats["high_risk_count"],
            }
        )
    return rows


def get_admin_statistics() -> dict[str, Any]:
    store = _read_store()
    events = store.get("events", [])
    users = list_users()
    role_counts = Counter(user["role"] for user in users)
    event_counts = Counter(event.get("type", "unknown") for event in events)
    risk_levels = Counter(
        event.get("payload", {}).get("risk_level")
        for event in events
        if event.get("type") in {"risk_analysis", "ocr_analysis"} and event.get("payload", {}).get("risk_level")
    )
    scam_types = Counter(
        event.get("payload", {}).get("scam_type")
        for event in events
        if event.get("type") in {"risk_analysis", "ocr_analysis"} and event.get("payload", {}).get("scam_type")
    )
    score_rows = [
        int(event.get("payload", {}).get("score", 0))
        for event in events
        if event.get("type") == "training_submit"
    ]
    active_user_ids = {event.get("user_id") for event in events if event.get("user_id") not in {None, "guest"}}
    return {
        "user_count": len(users),
        "student_count": role_counts.get("student", 0),
        "admin_count": role_counts.get("admin", 0),
        "active_user_count": len(active_user_ids),
        "event_count": len(events),
        "training_attempts": event_counts.get("training_submit", 0),
        "analysis_count": event_counts.get("risk_analysis", 0) + event_counts.get("ocr_analysis", 0),
        "average_training_score": round(sum(score_rows) / len(score_rows)) if score_rows else 0,
        "risk_level_distribution": dict(risk_levels),
        "top_scam_types": [{"label": label, "count": count} for label, count in scam_types.most_common(8)],
        "recent_events": sorted(events, key=lambda item: item.get("created_at", ""), reverse=True)[:12],
        "users": users,
    }
