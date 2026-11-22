from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


InputType = Literal["text", "sms", "link", "screenshot_ocr"]


class AnalyzeRequest(BaseModel):
    content: str = Field(..., min_length=1, description="用户输入的聊天文本、短信或 OCR 文本")
    input_type: InputType = "text"


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class AccountProfile(BaseModel):
    user_id: str
    username: str
    display_name: str
    role: Literal["student", "admin"]
    class_name: str = ""
    student_no: str = ""
    avatar: str = ""
    created_at: str = ""
    last_login_at: str = ""


class LoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    user: AccountProfile


class AccountProfileUpdate(BaseModel):
    display_name: str | None = None
    class_name: str | None = None
    student_no: str | None = None
    avatar: str | None = None


class RiskSignal(BaseModel):
    signal_id: str
    label: str
    keyword: str
    start: int
    end: int
    weight: int
    explanation: str
    suggestion: str


class SignalSummary(BaseModel):
    signal_id: str
    label: str
    count: int
    weight: int


class ModelInsight(BaseModel):
    model: str
    status: str
    label: str = ""
    score: float | int = 0
    detail: str = ""


class RiskTextSegment(BaseModel):
    text: str
    risk: bool = False
    label: str = ""
    signal_id: str = ""


class AnalyzeResponse(BaseModel):
    risk_level: Literal["低风险", "中风险", "高风险"]
    risk_score: int
    confidence: int
    scam_type: str
    scam_type_id: str
    summary: str
    signals: list[RiskSignal]
    signal_summary: list[SignalSummary]
    suggestions: list[str]
    highlighted_text: str
    highlighted_segments: list[RiskTextSegment] = Field(default_factory=list)
    evidence: list[str]
    model_insights: list[ModelInsight] = Field(default_factory=list)
    enhanced_advice: str = ""


class SensitiveEntity(BaseModel):
    type: str
    start: int
    end: int
    masked_value: str


class OcrRegion(BaseModel):
    index: int
    text: str
    confidence: float
    box: list[list[float]]
    bbox: dict[str, float]
    sensitive_entities: list[SensitiveEntity] = Field(default_factory=list)


class ChatMessage(BaseModel):
    order: int
    speaker: Literal["self", "other", "system", "unknown"]
    timestamp: str = ""
    text: str
    confidence: float
    bbox: dict[str, float]
    region_indices: list[int]
    sensitive_entities: list[SensitiveEntity] = Field(default_factory=list)


class OcrChatResponse(BaseModel):
    ocr_available: bool
    engine: str
    image_size: dict[str, int]
    regions: list[OcrRegion]
    messages: list[ChatMessage]
    sanitized_text: str
    sensitive_entities: list[SensitiveEntity]
    cache_hit: bool = False
    processing_ms: float = 0.0
    risk_analysis: AnalyzeResponse | None = None


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)


class KnowledgeReference(BaseModel):
    doc_id: str = ""
    title: str
    category: str
    score: float
    content: str
    source_type: str = "knowledge"
    source: str = ""
    version: str = ""
    updated_at: str = ""
    matched_keywords: list[str] = Field(default_factory=list)
    semantic_score: float = 0.0
    lexical_score: float = 0.0
    rerank_score: float = 0.0


class CaseCitation(BaseModel):
    case_id: str = ""
    title: str
    category: str
    scene: str
    risk_points: list[str] = Field(default_factory=list)
    handling: str = ""
    source: str = ""
    version: str = ""
    score: float | None = None


class AskResponse(BaseModel):
    answer: str
    references: list[KnowledgeReference]
    case_citations: list[CaseCitation] = Field(default_factory=list)
    knowledge_version: dict[str, Any] = Field(default_factory=dict)
    retrieval_method: str = "lexical"


class TrainingQuestion(BaseModel):
    id: str
    title: str
    scene: str
    difficulty: Literal["初级", "中级", "高级"]
    prompt: str
    options: list[dict[str, Any]]


class TrainingSubmitRequest(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict, description="question_id -> selected_option_id")


class TrainingSubmitResponse(BaseModel):
    total: int
    correct: int
    score: int
    feedback: list[dict[str, Any]]
    weak_types: list[str]
    radar: dict[str, int]
