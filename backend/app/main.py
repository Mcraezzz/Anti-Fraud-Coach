from __future__ import annotations

import threading

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    AccountProfile,
    AccountProfileUpdate,
    AskRequest,
    AskResponse,
    LoginRequest,
    LoginResponse,
    OcrChatResponse,
    TrainingQuestion,
    TrainingSubmitRequest,
    TrainingSubmitResponse,
)
from app.services.account_service import (
    get_account_stats,
    get_admin_statistics,
    list_users,
    login,
    record_activity,
    resolve_user_from_header,
    update_profile,
)
from app.services.dashboard_service import get_admin_dashboard
from app.services.model_inference_service import get_model_inference_status, preload_qwen_model
from app.services.model_service import get_resource_status
from app.services.ocr_service import get_ocr_status, preload_ocr_engine, process_chat_screenshot
from app.services.rag_service import answer_question, get_rag_status, preload_rag_engine, rebuild_rag_index
from app.services.risk_rules import analyze_text
from app.services.training_service import get_training_questions, grade_training


app = FastAPI(title=settings.app_name, version="0.1.0")
from app.coach_api import router as coach_router
app.include_router(coach_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _preload_startup_models() -> None:
    if settings.ocr_preload:
        preload_ocr_engine()
    preload_rag_engine()
    if settings.qwen_enabled and settings.qwen_preload:
        preload_qwen_model()


@app.on_event("startup")
def startup_preload_models() -> None:
    thread = threading.Thread(target=_preload_startup_models, name="anti-fraud-model-preload", daemon=True)
    thread.start()


def _optional_user(authorization: str | None) -> dict[str, object] | None:
    return resolve_user_from_header(authorization)


def _required_user(authorization: str | None) -> dict[str, object]:
    user = _optional_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    return user


def _required_admin(authorization: str | None) -> dict[str, object]:
    user = _required_user(authorization)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.post("/api/auth/login", response_model=LoginResponse)
def auth_login(request: LoginRequest) -> LoginResponse:
    result = login(request.username, request.password)
    if not result:
        raise HTTPException(status_code=401, detail="账号或密码错误")
    return LoginResponse(**result)


@app.get("/api/auth/me", response_model=AccountProfile)
def auth_me(authorization: str | None = Header(default=None)) -> AccountProfile:
    return AccountProfile(**_required_user(authorization))


@app.patch("/api/account/profile", response_model=AccountProfile)
def account_profile_update(
    request: AccountProfileUpdate,
    authorization: str | None = Header(default=None),
) -> AccountProfile:
    user = _required_user(authorization)
    updated = update_profile(user["user_id"], request.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="账号不存在")
    return AccountProfile(**updated)


@app.get("/api/account/stats")
def account_stats(authorization: str | None = Header(default=None)) -> dict[str, object]:
    user = _required_user(authorization)
    return get_account_stats(user)


@app.get("/api/resources")
def resources() -> dict[str, object]:
    return get_resource_status()


@app.get("/api/models/status")
def model_inference_status() -> dict[str, object]:
    return get_model_inference_status()


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest, authorization: str | None = Header(default=None)) -> AnalyzeResponse:
    result = analyze_text(request.content, request.input_type)
    record_activity(
        _optional_user(authorization),
        "risk_analysis",
        {
            "input_type": request.input_type,
            "risk_level": result["risk_level"],
            "risk_score": result["risk_score"],
            "scam_type": result["scam_type"],
            "scam_type_id": result["scam_type_id"],
            "signal_count": len(result["signals"]),
        },
    )
    return AnalyzeResponse(**result)


@app.get("/api/ocr/status")
def ocr_status() -> dict[str, object]:
    return get_ocr_status()


@app.post("/api/ocr/chat", response_model=OcrChatResponse)
async def ocr_chat(file: UploadFile = File(...), authorization: str | None = Header(default=None)) -> OcrChatResponse:
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传聊天截图图片文件")
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="图片文件为空")
    try:
        result = process_chat_screenshot(image_bytes)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"OCR processing failed: {exc}") from exc
    result["risk_analysis"] = analyze_text(result["sanitized_text"], "screenshot_ocr")
    risk = result["risk_analysis"]
    record_activity(
        _optional_user(authorization),
        "ocr_analysis",
        {
            "risk_level": risk["risk_level"],
            "risk_score": risk["risk_score"],
            "scam_type": risk["scam_type"],
            "message_count": len(result.get("messages", [])),
            "sensitive_entities": len(result.get("sensitive_entities", [])),
        },
    )
    return OcrChatResponse(**result)


@app.post("/api/ask", response_model=AskResponse)
def ask(request: AskRequest, authorization: str | None = Header(default=None)) -> AskResponse:
    result = answer_question(request.question)
    record_activity(
        _optional_user(authorization),
        "rag_question",
        {
            "question": request.question[:120],
            "reference_count": len(result.get("references", [])),
            "case_count": len(result.get("case_citations", [])),
        },
    )
    return AskResponse(**result)


@app.get("/api/rag/status")
def rag_status() -> dict[str, object]:
    return get_rag_status()


@app.post("/api/rag/rebuild")
def rag_rebuild() -> dict[str, object]:
    return rebuild_rag_index()


@app.get("/api/training/questions", response_model=list[TrainingQuestion])
def training_questions() -> list[TrainingQuestion]:
    return [TrainingQuestion(**item) for item in get_training_questions()]


@app.post("/api/training/submit", response_model=TrainingSubmitResponse)
def submit_training(request: TrainingSubmitRequest, authorization: str | None = Header(default=None)) -> TrainingSubmitResponse:
    result = grade_training(request.answers)
    record_activity(
        _optional_user(authorization),
        "training_submit",
        {
            "score": result["score"],
            "correct": result["correct"],
            "total": result["total"],
            "weak_types": result["weak_types"],
            "radar": result["radar"],
        },
    )
    return TrainingSubmitResponse(**result)


@app.get("/api/dashboard")
def dashboard() -> dict[str, object]:
    return get_admin_dashboard()


@app.get("/api/admin/dashboard")
def admin_dashboard() -> dict[str, object]:
    return get_admin_dashboard()


@app.get("/api/admin/users")
def admin_users(authorization: str | None = Header(default=None)) -> dict[str, object]:
    _required_admin(authorization)
    return {"users": list_users()}


@app.get("/api/admin/statistics")
def admin_statistics(authorization: str | None = Header(default=None)) -> dict[str, object]:
    _required_admin(authorization)
    return get_admin_statistics()
