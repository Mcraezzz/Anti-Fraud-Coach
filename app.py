from __future__ import annotations

import base64
import html
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from anti_fraud_rag.config import AppConfig
from anti_fraud_rag.ocr import ImageTextExtractor, OcrResult
from anti_fraud_rag.preprocessing import build_analysis_input as preprocess_analysis_input
from anti_fraud_rag.rag_engine import AntiFraudRagEngine
from anti_fraud_rag.utils import detect_language


LOGO_PATH = Path(r"C:\Users\22672\Desktop\反诈系统\miniprogram\assets\logo\afc-logo-v6-light.svg")
PAGE_ICON = str(LOGO_PATH) if LOGO_PATH.exists() else None


st.set_page_config(
    page_title="Anti-Fraud Coach",
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="auto",
)


@st.cache_resource(show_spinner=False)
def load_engine() -> AntiFraudRagEngine:
    config = AppConfig.from_env()
    return AntiFraudRagEngine.load(config)


@st.cache_resource(show_spinner=False)
def load_ocr_extractor() -> ImageTextExtractor:
    config = AppConfig.from_env()
    return ImageTextExtractor(config)


EXAMPLES = {
    "中文奖助学金诈骗": "【学校资助中心】你已获得2026年度助学金补贴，请在今晚22点前点击 http://campus-grant.example.cn 填写身份证、银行卡和短信验证码，逾期视为放弃。",
    "English email phishing": "Your university mailbox quota is full. Verify your student account now at http://secure-campus-login.example.com or your email access will be suspended. Enter your password and SMS code.",
    "Mixed internship scam": "Hi同学，我们是HR，远程实习已录用。Please pay a 299 RMB training deposit first, then we will send the onboarding materials.",
}

LANGUAGE_OPTIONS = {
    "zh": "中文",
    "en": "English",
}

NAV_ITEMS = [
    "首页概览",
    "媒体内容识别",
    "证据链分析",
    "反诈训练中心",
    "历史记录",
    "JSON / Debug",
]

NAV_ICON_LABELS = {
    "首页概览": "HO",
    "媒体内容识别": "SC",
    "证据链分析": "EV",
    "反诈训练中心": "TR",
    "历史记录": "HI",
    "JSON / Debug": "JS",
}

NAV_LABELS = {
    "zh": {
        "首页概览": "首页概览",
        "媒体内容识别": "媒体内容识别",
        "证据链分析": "证据链分析",
        "反诈训练中心": "反诈训练中心",
        "历史记录": "历史记录",
        "JSON / Debug": "JSON / Debug",
    },
    "en": {
        "首页概览": "Home",
        "媒体内容识别": "Media Recognition",
        "证据链分析": "Evidence Chain",
        "反诈训练中心": "Training Center",
        "历史记录": "History",
        "JSON / Debug": "JSON / Debug",
    },
}

QUERY_VIEW_TO_PAGE = {
    "home": "首页概览",
    "recognition": "媒体内容识别",
    "evidence": "证据链分析",
    "training": "反诈训练中心",
    "history": "历史记录",
    "debug": "JSON / Debug",
}

INPUT_MODES = ["文本", "聊天截图", "短信", "邮件", "URL / 社交媒体"]

INPUT_MODE_LABELS = {
    "zh": {
        "文本": "文本",
        "聊天截图": "聊天截图",
        "短信": "短信",
        "邮件": "邮件",
        "URL / 社交媒体": "URL / 社交媒体",
    },
    "en": {
        "文本": "Text",
        "聊天截图": "Chat Screenshot",
        "短信": "SMS",
        "邮件": "Email",
        "URL / 社交媒体": "URL / Social",
    },
}

INPUT_PLACEHOLDERS_BY_LANG = {
    "zh": {
        "文本": "请粘贴可疑短信、聊天记录、邮件内容、社交媒体文案或 URL 描述，例如：客服要求我点击链接填写银行卡号并输入验证码。",
        "聊天截图": "可输入截图背景说明；上传聊天截图后，OCR 文本会与这里的补充描述一起进入分析。",
        "短信": "粘贴短信正文，例如：你的校园补贴已到账，请今晚前点击链接填写银行卡和验证码。",
        "邮件": "粘贴邮件主题、发件人线索和正文，系统会提取账号、链接、机构和风险话术。",
        "URL / 社交媒体": "粘贴 URL、账号主页描述、私信内容或社交媒体文案，系统会结合域名、关键词和相似案例检索。",
    },
    "en": {
        "文本": "Paste a suspicious SMS, chat message, email, social post, or URL description, for example: a support agent asks me to enter my bank card and SMS code.",
        "聊天截图": "Add context for the screenshot. OCR text and this note will be analyzed together.",
        "短信": "Paste an SMS message, for example: your campus grant is ready, click this link and enter your bank card and SMS code before tonight.",
        "邮件": "Paste the email subject, sender clues, and body. The system extracts accounts, links, organizations, and risky wording.",
        "URL / 社交媒体": "Paste a URL, profile description, DM, or social media post. The system checks domains, keywords, and similar cases.",
    },
}

EXAMPLES_BY_LANG = {
    "zh": EXAMPLES,
    "en": {
        "中文奖助学金诈骗": "Campus Financial Aid Center: You have received a 2026 grant. Click http://campus-grant.example.cn before 22:00 tonight and enter your ID number, bank card, and SMS verification code, or the grant will expire.",
        "English email phishing": EXAMPLES["English email phishing"],
        "Mixed internship scam": "Hi student, we are HR and your remote internship has been approved. Please pay a 299 RMB training deposit first, then we will send onboarding materials.",
    },
}

EXAMPLE_LABELS = {
    "zh": {
        "中文奖助学金诈骗": "中文奖助学金诈骗",
        "English email phishing": "English email phishing",
        "Mixed internship scam": "中英混合实习骗局",
    },
    "en": {
        "中文奖助学金诈骗": "Campus grant scam",
        "English email phishing": "Email phishing",
        "Mixed internship scam": "Mixed internship scam",
    },
}

DEMO_ANALYSIS_TEXT = "【学校资助中心】你已获得2026年度助学金补贴，请在今晚22点前点击 http://campus-grant.example.cn 填写身份证、银行卡和短信验证码，逾期视为放弃。"

DEMO_RESULT = {
    "input_mode_time": "2026-06-15 14:30:00",
    "input_text": DEMO_ANALYSIS_TEXT,
    "risk_features": {
        "matched_categories": ["可疑链接", "银行卡信息", "验证码", "紧急话术"],
        "matched_terms": ["补贴", "身份证", "银行卡", "验证码"],
        "urls": ["http://campus-grant.example.cn"],
        "domains": ["campus-grant.example.cn"],
        "money_mentions": [],
    },
    "retrieved_evidence": [
        {
            "id": "E1",
            "title": "校园补贴与冒充资助中心诈骗规则",
            "reason": "包含“补贴”“银行卡”“验证码”等关键词",
            "bm25_score": 0.82,
            "dense_score": 0.76,
            "url_match_score": 0.0,
            "risk_keyword_score": 0.9,
            "reranker_score": 0.88,
            "score": 0.81,
            "content": "诈骗分子常冒充学校资助中心或平台客服，以奖助学金、账户冻结、系统升级为由，诱导学生点击钓鱼链接并填写银行卡、身份证和验证码。",
        },
        {
            "id": "E2",
            "title": "短链接与仿冒域名风险提示",
            "reason": "命中高危网址与限时处理话术",
            "bm25_score": 0.38,
            "dense_score": 0.67,
            "url_match_score": 0.85,
            "risk_keyword_score": 0.72,
            "reranker_score": 0.85,
            "score": 0.75,
            "content": "钓鱼页面会伪装成校园服务或官方通知页面，并通过紧急截止时间制造压力，诱导用户提交身份信息、支付信息或短信验证码。",
        },
    ],
    "analysis": {
        "risk_level": "High",
        "risk_score": 0.89,
        "fraud_type": "冒充资助中心 / 钓鱼链接 / 验证码套取",
        "risk_signals": ["可疑链接", "要求填写银行卡", "验证码", "身份信息", "紧急截止"],
        "natural_language_report": "该内容以学校资助中心名义发放补贴，并要求在限时内点击链接填写身份证、银行卡和短信验证码，符合典型冒充校园机构与钓鱼链接诈骗特征。",
        "anti_fraud_suggestion": "立即停止点击链接，不要提交身份证、银行卡、密码或验证码。请通过学校官网、辅导员或官方资助系统核实信息，并保留短信或聊天截图作为证据。",
        "compliance_rewrite": "请勿点击陌生短信或聊天记录中的链接，不要向任何人提供银行卡号、密码或验证码。真正的学校资助通知会通过官方渠道发布，如需核实，请登录学校官方系统或联系辅导员。",
        "compliance_reminder": "任何要求提供验证码、银行卡号或身份证信息的陌生链接都需要先通过官方渠道核实。",
        "training_question": {
            "question": "如果陌生短信自称是“学校资助中心”，要求你点击链接填写银行卡号和收到的验证码以领取补贴，你应该怎么做？",
            "options": [
                {"text": "按照要求填写，避免错过补贴"},
                {"text": "加对方微信问清楚后再填写"},
                {"text": "拒绝点击链接并提供信息，直接通过学校官方渠道核实"},
                {"text": "把收到的验证码发给对方帮忙处理"},
            ],
            "reference_answer": "选择 C。银行卡号、验证码和陌生链接同时出现时，通常属于高风险诈骗信号，必须停止操作并通过官方渠道核实。",
        },
    },
    "image_ocr": [],
}

DEMO_HISTORY = [
    {
        "时间": "2026-06-15 14:30:00",
        "输入类型": "TEXT",
        "风险等级": "高风险",
        "诈骗类型": "冒充资助中心 / 钓鱼链接 / 验证码套取",
        "风险评分": 89,
        "证据数": 2,
        "内容摘要": DEMO_ANALYSIS_TEXT[:72],
    },
    {
        "时间": "2026-06-14 09:12:00",
        "输入类型": "URL",
        "风险等级": "中风险",
        "诈骗类型": "可疑钓鱼链接",
        "风险评分": 67,
        "证据数": 1,
        "内容摘要": "http://taobao-security-update.example/login",
    },
]

UI_TEXT = {
    "brand_subtitle": {"zh": "识别与训练系统", "en": "Recognition & Training"},
    "language": {"zh": "语言", "en": "Language"},
    "settings": {"zh": "运行设置", "en": "Run Settings"},
    "mock_mode": {"zh": "Mock mode", "en": "Mock mode"},
    "mock_help": {"zh": "Run without calling Qwen API.", "en": "Run without calling Qwen API."},
    "retrieved_evidence": {"zh": "Retrieved evidence", "en": "Retrieved evidence"},
    "example": {"zh": "Example", "en": "Example"},
    "use_example": {"zh": "Use example", "en": "Use example"},
    "model_online": {"zh": "AI 模型在线", "en": "AI model online"},
    "home_title": {
        "zh": '大学生 <span class="wd-hero-blue">AI 反诈</span><br><span class="wd-hero-cyan">媒体</span><br>内容识别与训<br>练平台',
        "en": 'Student <span class="wd-hero-blue">AI Anti-Fraud</span><br><span class="wd-hero-cyan">Media</span><br>Recognition &<br>Training Platform',
    },
    "home_copy": {
        "zh": "支持短信、聊天截图、邮件、社交媒体文本与 URL 描述输入，结合风险特征抽取、混合检索、证据融合与大模型推理，生成可解释的反诈分析报告。",
        "en": "Analyze SMS, chat screenshots, emails, social posts, and URL descriptions with risk feature extraction, hybrid retrieval, evidence fusion, and explainable AI reasoning.",
    },
    "home_cta": {"zh": "开始媒体内容识别", "en": "Start Media Recognition"},
    "feature_input_title": {"zh": "多类型输入识别", "en": "Multi-Input Recognition"},
    "feature_input_copy": {"zh": "支持短信、聊天文本、邮件、社交媒体内容、URL 与截图上传。", "en": "Supports SMS, chat text, email, social content, URLs, and screenshots."},
    "feature_risk_title": {"zh": "风险特征感知", "en": "Risk Feature Sensing"},
    "feature_risk_copy": {"zh": "自动识别链接、转账、验证码、冒充身份、紧急话术等风险信号。", "en": "Detects risky links, transfers, SMS codes, impersonation, and urgency cues."},
    "feature_rag_title": {"zh": "混合 RAG 检索", "en": "Hybrid RAG Retrieval"},
    "feature_rag_copy": {"zh": "融合 BM25、BGE-M3、FAISS、URL 精确匹配和风险关键词匹配。", "en": "Combines BM25, BGE-M3, FAISS, exact URL matches, and risk keywords."},
    "feature_training_title": {"zh": "反诈训练生成", "en": "Training Generation"},
    "feature_training_copy": {"zh": "输出风险解释、反诈建议、合规改写和情境式训练题。", "en": "Generates explanations, safety advice, compliant rewrites, and scenario quizzes."},
    "recognition_title": {"zh": "待识别媒体内容", "en": "Media Content to Review"},
    "recognition_subtitle": {"zh": "上传或输入可疑内容进行风险诊断", "en": "Upload or enter suspicious content for risk diagnosis"},
    "analyze": {"zh": "分析风险", "en": "Analyze Risk"},
    "input_type": {"zh": "输入类型", "en": "Input Type"},
    "upload_screenshot": {"zh": "点击或拖拽上传截图", "en": "Click or drag to upload a screenshot"},
    "upload_help": {"zh": "支持聊天截图、短信截图、邮件截图、网页截图", "en": "Supports chat, SMS, email, and webpage screenshots"},
    "ocr_edit": {"zh": "可手动修正 OCR 识别文本", "en": "Edit OCR text manually"},
    "ocr_placeholder": {"zh": "上传截图后，可在这里补充或修正 OCR 识别文本。", "en": "After uploading a screenshot, add or correct OCR text here."},
    "optional_upload": {"zh": "可选：上传聊天截图、短信截图、邮件截图或网页截图", "en": "Optional: upload a chat, SMS, email, or webpage screenshot"},
    "risk_features": {"zh": "识别到的风险特征", "en": "Detected Risk Features"},
    "risk_level": {"zh": "风险等级", "en": "Risk Level"},
    "fraud_type": {"zh": "诈骗类型", "en": "Fraud Type"},
    "evidence_chain": {"zh": "证据链", "en": "Evidence Chain"},
    "result_hint": {"zh": "分析结果会在这里显示，包括风险评分、诈骗类型、风险信号、反诈建议和训练题。", "en": "Analysis results appear here, including score, fraud type, signals, advice, and training questions."},
    "suggestions": {"zh": "反诈处置建议", "en": "Anti-Fraud Actions"},
    "suggestions_waiting": {"zh": "提交内容后，系统会给出立即操作、核实方式和后续处置建议。", "en": "After submission, the system provides immediate actions, verification steps, and follow-up guidance."},
    "risk_score": {"zh": "风险评分", "en": "Risk Score"},
    "suspected_type": {"zh": "疑似诈骗类型:", "en": "Suspected fraud type:"},
    "qwen_fallback": {"zh": "Qwen API 调用失败，本次已使用本地 mock fallback 结果。", "en": "Qwen API failed. A local mock fallback result was used."},
    "empty_input": {"zh": "请输入文本，或上传包含可识别文字的图片。", "en": "Enter text or upload an image with readable text."},
    "ocr_spinner": {"zh": "正在识别截图中的文字...", "en": "Recognizing text in screenshots..."},
    "analysis_spinner": {"zh": "正在检索证据并生成结构化风险报告...", "en": "Retrieving evidence and generating a structured risk report..."},
    "core_output": {"zh": "核心输出", "en": "Core Output"},
    "report_tab": {"zh": "报告与建议", "en": "Report & Advice"},
    "training_tab": {"zh": "反诈训练题", "en": "Training Quiz"},
    "rewrite_tab": {"zh": "安全合规改写", "en": "Safe Rewrite"},
    "summary_judgment": {"zh": "综合判断", "en": "Overall Judgment"},
    "immediate_advice": {"zh": "立即处置建议", "en": "Immediate Actions"},
    "safe_rewrite": {"zh": "安全合规改写", "en": "Safe Compliant Rewrite"},
    "no_report": {"zh": "未生成报告。", "en": "No report generated."},
    "default_advice": {"zh": "请通过官方渠道核实，不点击陌生链接，不提供验证码或支付信息。", "en": "Verify through official channels. Do not click unknown links or provide SMS codes or payment details."},
    "default_rewrite": {"zh": "请通过官方渠道核实该请求后再采取行动。", "en": "Verify this request through official channels before taking action."},
    "quiz_label": {"zh": "情景测试题", "en": "Scenario Quiz"},
    "your_selection": {"zh": "已选择", "en": "Selected"},
    "show_answer": {"zh": "查看答案解析", "en": "Show Answer"},
    "reference_answer": {"zh": "参考答案", "en": "Reference Answer"},
    "ocr_text": {"zh": "OCR 识别文本", "en": "OCR Text"},
    "recognized_text": {"zh": "Recognized text", "en": "Recognized text"},
    "no_ocr": {"zh": "No readable text was detected in this image.", "en": "No readable text was detected in this image."},
    "evidence_title": {"zh": "RAG 证据链与检索来源", "en": "RAG Evidence Chain & Retrieval Sources"},
    "evidence_subtitle": {"zh": "混合检索与特征分数融合过程可视化", "en": "Visualize hybrid retrieval and feature-score fusion"},
    "no_evidence": {"zh": "还没有可展示的证据链。请先在“媒体内容识别”页完成一次分析。", "en": "No evidence chain is available yet. Run an analysis in Media Recognition first."},
    "flow_user": {"zh": "用户输入", "en": "User Input"},
    "flow_features": {"zh": "风险特征抽取", "en": "Risk Feature Extraction"},
    "flow_retrieval": {"zh": "混合检索证据", "en": "Hybrid Evidence Retrieval"},
    "flow_fusion": {"zh": "证据融合评分", "en": "Evidence Fusion Scoring"},
    "flow_reranker": {"zh": "BGE Reranker", "en": "BGE Reranker"},
    "flow_reasoning": {"zh": "Qwen 风险推理", "en": "Qwen Risk Reasoning"},
    "evidence_details": {"zh": "检索证据详情 (Top K)", "en": "Retrieved Evidence Details (Top K)"},
    "evidence_badge": {"zh": "证据", "en": "Evidence"},
    "match_reason": {"zh": "匹配原因：", "en": "Match reason: "},
    "rerank_score": {"zh": "Rerank 得分", "en": "Rerank Score"},
    "retrieval_scores": {"zh": "多路检索分数", "en": "Retrieval Scores"},
    "matched_content": {"zh": "匹配内容", "en": "Matched Content"},
    "training_title": {"zh": "反诈训练中心", "en": "Anti-Fraud Training Center"},
    "training_subtitle": {"zh": "根据上传案例自动生成的情景式训练题与合规科普", "en": "Scenario quizzes and safety guidance generated from the uploaded case"},
    "no_training": {"zh": "完成一次媒体内容识别后，这里会显示自动生成的训练题。", "en": "After one media analysis, generated training questions will appear here."},
    "core_rewrite": {"zh": "核心科普改写", "en": "Core Safety Rewrite"},
    "original_summary": {"zh": "原始内容摘要", "en": "Original Summary"},
    "safe_version": {"zh": "合规安全版本", "en": "Safe Version"},
    "learning_reminder": {"zh": "学习提醒", "en": "Learning Reminder"},
    "history_title": {"zh": "历史识别记录", "en": "Recognition History"},
    "history_subtitle": {"zh": "查看过往风险诊断与分析报告", "en": "Review previous risk diagnoses and reports"},
    "history_search": {"zh": "搜索记录...", "en": "Search records..."},
    "history_empty": {"zh": "当前会话还没有检测记录。", "en": "No detection records in this session yet."},
    "history_report_missing": {
        "zh": "这条历史记录缺少完整报告数据，请重新分析该内容后再查看报告。",
        "en": "This history record does not contain a full report. Re-analyze the content to view the report.",
    },
    "table_time": {"zh": "检测时间", "en": "Time"},
    "table_input": {"zh": "输入类型", "en": "Input Type"},
    "table_risk": {"zh": "风险等级", "en": "Risk Level"},
    "table_fraud": {"zh": "疑似诈骗类型", "en": "Suspected Fraud Type"},
    "table_score": {"zh": "风险评分", "en": "Risk Score"},
    "table_action": {"zh": "操作", "en": "Action"},
    "view_report": {"zh": "查看报告", "en": "View Report"},
    "debug_title": {"zh": "原始 JSON", "en": "Raw JSON"},
    "debug_subtitle": {"zh": "查看系统最终输出的结构化字段，可用于后续实验评估与接口对接", "en": "Inspect structured output fields for later evaluation and API integration"},
    "debug_empty": {"zh": "还没有 JSON 输出。请先完成一次风险分析。", "en": "No JSON output yet. Run a risk analysis first."},
    "copy": {"zh": "复制", "en": "Copy"},
    "copy_toast": {"zh": "JSON 已在下方代码区展示，可直接选择复制。", "en": "JSON is shown in the code panel below and can be selected for copying."},
    "download_report": {"zh": "下载报告", "en": "Download Report"},
    "field_notes": {"zh": "输出字段说明", "en": "Output Field Notes"},
}

RISK_STYLES = {
    "High": {
        "label": "高风险",
        "accent": "#EF4444",
        "surface": "#FEF2F2",
        "message": "存在明显诈骗特征，建议立即停止操作",
    },
    "Medium": {
        "label": "中风险",
        "accent": "#F59E0B",
        "surface": "#FFFBEB",
        "message": "存在可疑信号，建议进一步核实",
    },
    "Low": {
        "label": "低风险",
        "accent": "#10B981",
        "surface": "#ECFDF5",
        "message": "暂未发现明显诈骗风险",
    },
    "Unknown": {
        "label": "待分析",
        "accent": "#0062FF",
        "surface": "#E8F4FA",
        "message": "提交内容后生成风险诊断",
    },
}

FEATURE_TONES = {
    "credential_request": "orange",
    "financial_info": "red",
    "upfront_payment": "red",
    "urgency_pressure": "orange",
    "impersonation": "purple",
    "job_or_internship": "cyan",
    "campus_context": "green",
    "refund_or_reward": "orange",
    "investment_or_loan": "red",
}


def inject_design_system() -> None:
    st.markdown(
        """
<style>
:root {
  --brand-bg: #E8F4FA;
  --brand-primary: #0062FF;
  --brand-cyan: #00C6FF;
  --brand-dark: #0A1B35;
  --brand-muted: #64748B;
  --brand-line: #E5E7EB;
  --brand-soft-line: rgba(10, 27, 53, 0.12);
  --brand-green: #10B981;
  --brand-orange: #F59E0B;
  --brand-red: #EF4444;
  --brand-radius: 8px;
  --brand-shadow: 0 6px 16px rgba(0, 98, 255, 0.08);
}

.stApp {
  background: #FFFFFF;
  color: var(--brand-dark);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

[data-testid="stHeader"] {
  background: rgba(255, 255, 255, 0);
}

[data-testid="stToolbar"],
[data-testid="stDecoration"] {
  display: none;
}

.main .block-container {
  max-width: 1180px;
  padding: 1.05rem 2.4rem 4rem;
}

[data-testid="stSidebar"] > div:first-child {
  background: var(--brand-bg);
  border-right: 1px solid var(--brand-line);
  padding-top: 1.1rem;
}

[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div {
  color: var(--brand-dark);
}

[data-testid="stSidebar"] div[role="radiogroup"] {
  display: grid;
  gap: 0.5rem;
}

[data-testid="stSidebar"] label[data-baseweb="radio"] {
  min-height: 2.9rem;
  border: 1px solid transparent;
  border-radius: var(--brand-radius);
  padding: 0.72rem 0.95rem;
  background: transparent;
  transition: background 150ms ease, border-color 150ms ease, color 150ms ease;
}

[data-testid="stSidebar"] label[data-baseweb="radio"] > div:first-child,
[data-testid="stSidebar"] label[data-baseweb="radio"] > input {
  display: none;
}

[data-testid="stSidebar"] label[data-baseweb="radio"]:hover {
  background: rgba(255, 255, 255, 0.58);
}

[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) {
  background: #FFFFFF;
  border-color: var(--brand-line);
  box-shadow: 0 1px 0 rgba(10, 27, 53, 0.04);
}

[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) p {
  color: var(--brand-primary);
  font-weight: 700;
}

[data-testid="stSidebar"] hr {
  border-color: rgba(10, 27, 53, 0.08);
}

h1, h2, h3, h4, p, li, span, label {
  letter-spacing: 0;
}

h1, h2, h3, h4 {
  color: var(--brand-dark);
}

.stTextArea textarea,
.stTextInput input,
.stSelectbox div[data-baseweb="select"] > div,
.stMultiSelect div[data-baseweb="select"] > div {
  color: var(--brand-dark);
  background: #FFFFFF;
  border: 1px solid var(--brand-line);
  border-radius: var(--brand-radius);
}

.stTextArea textarea:focus,
.stTextInput input:focus {
  border-color: var(--brand-primary);
  box-shadow: 0 0 0 1px rgba(0, 98, 255, 0.16);
}

[data-testid="stWidgetLabel"] p {
  color: #64748B;
  font-size: 0.82rem;
  font-weight: 680;
}

[data-testid="stFileUploader"] section {
  background: #FFFFFF;
  border: 2px dashed #CBD5E1;
  border-radius: var(--brand-radius);
  min-height: 17rem;
  align-items: center;
  justify-content: center;
}

.stButton > button,
.stDownloadButton > button {
  min-height: 2.6rem;
  border-radius: var(--brand-radius);
  border: 1px solid var(--brand-line);
  background: #FFFFFF;
  color: var(--brand-dark);
  font-weight: 650;
  transition: background 150ms ease, border-color 150ms ease, transform 120ms ease;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
  background: #F8FAFC;
  border-color: rgba(0, 98, 255, 0.25);
  color: var(--brand-primary);
}

.stButton > button:active,
.stDownloadButton > button:active {
  transform: translateY(1px);
}

.stButton > button[kind="primary"] {
  background: linear-gradient(90deg, var(--brand-primary), var(--brand-cyan));
  border-color: transparent;
  color: #FFFFFF;
  font-weight: 850;
  box-shadow: 0 8px 16px rgba(0, 98, 255, 0.15);
}

.main div[role="radiogroup"] {
  display: flex;
  flex-wrap: nowrap;
  gap: 0.75rem;
  overflow-x: auto;
}

.main label[data-baseweb="radio"] {
  min-height: 2.55rem;
  border: 1px solid var(--brand-line);
  border-radius: var(--brand-radius);
  padding: 0.56rem 1.15rem;
  background: #FFFFFF;
  white-space: nowrap;
  box-shadow: 0 1px 2px rgba(10, 27, 53, 0.04);
}

.main label[data-baseweb="radio"] > div:first-child,
.main label[data-baseweb="radio"] > input {
  display: none;
}

.main label[data-baseweb="radio"]:has(input:checked) {
  background: var(--brand-bg);
  border-color: rgba(0, 98, 255, 0.28);
  box-shadow: 0 1px 0 rgba(0, 98, 255, 0.08);
}

.main label[data-baseweb="radio"]:has(input:checked) p {
  color: var(--brand-primary);
  font-weight: 750;
}

[data-testid="stTabs"] button {
  color: var(--brand-muted);
}

[data-testid="stTabs"] button[aria-selected="true"] {
  color: var(--brand-primary);
}

[data-testid="stExpander"] {
  background: #FFFFFF;
  border: 1px solid var(--brand-line);
  border-radius: var(--brand-radius);
}

.wd-sidebar-brand {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  padding: 0.6rem 0 1.5rem;
  margin-bottom: 1.1rem;
  border-bottom: 1px solid rgba(10, 27, 53, 0.08);
}

.wd-logo-box {
  width: 2.35rem;
  height: 2.35rem;
  display: grid;
  place-items: center;
  border-radius: var(--brand-radius);
  background: linear-gradient(135deg, var(--brand-primary), var(--brand-cyan));
  color: #FFFFFF;
  font-weight: 800;
}

.wd-logo-box img {
  width: 1.65rem;
  height: 1.65rem;
  display: block;
}

.wd-brand-title {
  color: var(--brand-dark);
  font-size: 1.05rem;
  line-height: 1.1;
  font-weight: 780;
}

.wd-brand-subtitle {
  margin-top: 0.25rem;
  color: #94A3B8;
  font-size: 0.66rem;
  font-weight: 800;
}

.wd-side-status {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  margin-top: 1.1rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(10, 27, 53, 0.08);
  color: #94A3B8;
  font-size: 0.7rem;
  font-weight: 800;
}

.wd-dot {
  width: 0.42rem;
  height: 0.42rem;
  border-radius: 999px;
  background: var(--brand-green);
}

.wd-view {
  display: grid;
  gap: 2rem;
  animation: wd-fade 180ms ease both;
}

@keyframes wd-fade {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (prefers-reduced-motion: reduce) {
  .wd-view {
    animation: none;
  }
}

.wd-view-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1.25rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--brand-line);
}

.wd-view-title {
  margin: 0;
  color: var(--brand-dark);
  font-size: 1.95rem;
  line-height: 1.15;
  font-weight: 360;
}

.wd-view-title strong {
  font-weight: 720;
}

.wd-view-copy {
  margin: 0.55rem 0 0;
  max-width: 62ch;
  color: var(--brand-muted);
  font-size: 0.98rem;
  line-height: 1.7;
}

.wd-pill {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  max-width: 100%;
  border: 1px solid rgba(0, 98, 255, 0.18);
  border-radius: 999px;
  background: var(--brand-bg);
  color: #075985;
  padding: 0.3rem 0.72rem;
  font-size: 0.72rem;
  font-weight: 750;
}

.wd-action-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1.25rem;
  padding-bottom: 1.1rem;
  border-bottom: 1px solid var(--brand-line);
}

.wd-action-header h2 {
  margin: 0;
  color: var(--brand-dark);
  font-family: "Songti SC", "STSong", "SimSun", "Noto Serif SC", Georgia, serif;
  font-size: 2.1rem;
  line-height: 1.18;
  font-weight: 400;
}

.wd-action-header p {
  margin: 0.55rem 0 0;
  color: var(--brand-muted);
  font-size: 1rem;
  line-height: 1.6;
}

.wd-title-with-icon {
  display: inline-flex;
  align-items: center;
  gap: 0.7rem;
}

.wd-title-icon {
  color: #9AA7B8;
  font-family: ui-sans-serif, system-ui, sans-serif;
  font-size: 1.25rem;
  font-weight: 800;
}

.wd-page-grid {
  display: grid;
  gap: 2rem;
}

.wd-page-grid-2 {
  grid-template-columns: minmax(0, 1fr) minmax(20rem, 1fr);
}

.wd-page-grid-flow {
  grid-template-columns: minmax(15rem, 18rem) minmax(0, 1fr);
}

.wd-page-grid-side {
  grid-template-columns: minmax(0, 1fr) minmax(18rem, 22rem);
}

.wd-soft-panel {
  border: 1px solid #DCEAF5;
  border-radius: var(--brand-radius);
  background: var(--brand-bg);
  padding: 1.55rem;
}

.wd-result-panel {
  border: 1px solid var(--brand-line);
  border-radius: var(--brand-radius);
  background: #FFFFFF;
  padding: 1.75rem;
  box-shadow: 0 2px 6px rgba(10, 27, 53, 0.05);
}

.wd-action-button-visual {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 3.1rem;
  min-width: 9.5rem;
  border-radius: var(--brand-radius);
  background: linear-gradient(90deg, var(--brand-primary), var(--brand-cyan));
  color: #FFFFFF !important;
  font-size: 0.95rem;
  font-weight: 850;
  text-decoration: none !important;
  box-shadow: 0 8px 16px rgba(0, 98, 255, 0.15);
}

.wd-hero {
  display: grid;
  grid-template-columns: minmax(23.5rem, 1fr) minmax(16rem, 0.68fr);
  gap: 2.6rem;
  align-items: center;
  min-height: 42.5rem;
  padding: 4.7rem 4.25rem;
  border: 1px solid var(--brand-line);
  border-radius: var(--brand-radius);
  background: var(--brand-bg);
  overflow: hidden;
}

.wd-hero h1 {
  margin: 0;
  max-width: 100%;
  color: var(--brand-dark);
  font-family: "Songti SC", "STSong", "SimSun", "Noto Serif SC", Georgia, serif;
  font-size: 3.75rem;
  line-height: 1.09;
  font-weight: 400;
}

.wd-title-nowrap {
  white-space: nowrap;
}

.wd-hero-blue,
.wd-hero-cyan {
  display: inline-block;
  color: var(--brand-primary);
}

.wd-hero-blue {
  color: var(--brand-primary);
  font-weight: 700;
}

.wd-hero-cyan {
  color: var(--brand-cyan);
  font-weight: 700;
}

.wd-hero p {
  margin: 2.4rem 0 0;
  max-width: 31rem;
  color: var(--brand-muted);
  font-size: 1.18rem;
  line-height: 1.72;
  font-weight: 340;
}

.wd-hero-cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 1.1rem;
  width: fit-content;
  min-width: 19.4rem;
  min-height: 4.5rem;
  margin-top: 3.85rem;
  padding: 0 2rem;
  border-radius: var(--brand-radius);
  background: linear-gradient(90deg, var(--brand-primary), var(--brand-cyan));
  color: #FFFFFF !important;
  font-size: 1rem;
  font-weight: 850;
  text-decoration: none !important;
  box-shadow: 0 16px 28px rgba(0, 98, 255, 0.14);
  transition: transform 140ms ease, box-shadow 140ms ease, opacity 140ms ease;
}

.wd-hero-cta:hover {
  color: #FFFFFF !important;
  opacity: 0.94;
  transform: translateY(-1px);
  box-shadow: 0 18px 32px rgba(0, 98, 255, 0.18);
}

.wd-hero-cta:active {
  transform: translateY(0);
}

.wd-hero-cta span {
  font-size: 1.55rem;
  line-height: 1;
  color: #FFFFFF;
}

.wd-hero-orbit {
  min-height: 22rem;
  display: grid;
  place-items: center;
}

.wd-orbit {
  position: relative;
  width: 20rem;
  aspect-ratio: 1;
  display: grid;
  place-items: center;
  border: 1px solid var(--brand-line);
  border-radius: 999px;
  background: #FFFFFF;
  box-shadow: 0 2px 7px rgba(10, 27, 53, 0.08);
}

.wd-orbit::before,
.wd-orbit::after {
  content: "";
  position: absolute;
  border: 1px solid #EFF3F8;
  border-radius: inherit;
}

.wd-orbit::before { inset: 0.72rem; }
.wd-orbit::after { inset: 2.45rem; }

.wd-shield-mark {
  position: relative;
  z-index: 1;
  width: 4.15rem;
  height: 4.15rem;
  color: var(--brand-primary);
}

.wd-feature-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1.5rem;
  align-items: stretch;
}

.wd-feature-card,
.wd-card,
.wd-panel,
.wd-evidence-card,
.wd-table-shell {
  border: 1px solid var(--brand-line);
  border-radius: var(--brand-radius);
  background: #FFFFFF;
}

.wd-feature-card {
  min-height: 13.6rem;
  padding: 1.75rem;
  background: linear-gradient(180deg, #FFFFFF 0%, #F8FBFF 100%);
  border-color: #DCEAF5;
  box-shadow: 0 10px 24px rgba(10, 27, 53, 0.06);
}

.wd-feature-card:nth-child(2),
.wd-feature-card:nth-child(4) {
  transform: translateY(0.7rem);
}

.wd-feature-icon {
  width: 3.1rem;
  height: 3.1rem;
  display: grid;
  place-items: center;
  border: 1px solid rgba(0, 98, 255, 0.14);
  border-radius: var(--brand-radius);
  background: #FFFFFF;
  color: var(--brand-primary);
  font-size: 0.72rem;
  font-weight: 850;
  margin-bottom: 1.4rem;
  box-shadow: 0 4px 12px rgba(0, 98, 255, 0.08);
}

.wd-feature-card h3,
.wd-card h3,
.wd-panel h3 {
  margin: 0 0 0.7rem;
  font-size: 1rem;
  color: var(--brand-dark);
}

.wd-feature-card p,
.wd-card p,
.wd-panel p {
  margin: 0;
  color: var(--brand-muted);
  font-size: 0.9rem;
  line-height: 1.7;
}

.wd-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1.5rem;
  padding-top: 2rem;
  border-top: 1px solid #F1F5F9;
}

.wd-stat {
  padding: 1.5rem;
  text-align: center;
  border: 1px solid var(--brand-line);
  border-radius: var(--brand-radius);
  background: var(--brand-bg);
}

.wd-stat strong {
  display: block;
  margin-bottom: 0.55rem;
  color: var(--brand-dark);
  font-size: 1.8rem;
  line-height: 1.1;
  font-weight: 330;
}

.wd-stat span {
  color: #94A3B8;
  font-size: 0.68rem;
  font-weight: 850;
}

.wd-work-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(20rem, 0.92fr);
  gap: 2rem;
  align-items: stretch;
}

.wd-panel {
  padding: 1.5rem;
}

.wd-panel-blue {
  background: var(--brand-bg);
}

.wd-panel-result {
  padding: 2rem;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(10, 27, 53, 0.04);
}

.wd-risk-card {
  border: 1px solid var(--risk-color);
  border-radius: var(--brand-radius);
  padding: 1.5rem;
  background: var(--risk-surface);
}

.wd-risk-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.wd-risk-label {
  color: var(--risk-color);
  font-size: 1.15rem;
  font-weight: 850;
}

.wd-risk-score {
  border: 1px solid color-mix(in srgb, var(--risk-color) 20%, white);
  border-radius: var(--brand-radius);
  background: #FFFFFF;
  color: var(--risk-color);
  padding: 0.35rem 0.7rem;
  font-size: 0.76rem;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
}

.wd-alert-strip {
  margin-top: 1rem;
  border-radius: var(--brand-radius);
  background: color-mix(in srgb, var(--risk-color) 9%, white);
  color: var(--risk-color);
  padding: 0.8rem 1rem;
  font-size: 0.88rem;
  font-weight: 720;
}

.wd-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.wd-chip {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  border: 1px solid var(--brand-line);
  border-radius: var(--brand-radius);
  background: #FFFFFF;
  color: var(--brand-muted);
  padding: 0.36rem 0.68rem;
  font-size: 0.78rem;
  font-weight: 680;
}

.wd-chip-cyan { border-color: rgba(0, 98, 255, 0.18); background: #E8F4FA; color: #075985; }
.wd-chip-green { border-color: rgba(16, 185, 129, 0.22); background: #ECFDF5; color: #047857; }
.wd-chip-orange { border-color: rgba(245, 158, 11, 0.24); background: #FFFBEB; color: #B45309; }
.wd-chip-red { border-color: rgba(239, 68, 68, 0.22); background: #FEF2F2; color: #B91C1C; }
.wd-chip-purple { border-color: rgba(124, 58, 237, 0.2); background: #F5F3FF; color: #6D28D9; }

.wd-section-label {
  margin: 1.5rem 0 0.85rem;
  color: #94A3B8;
  font-size: 0.68rem;
  font-weight: 850;
  letter-spacing: 0.06em;
}

.wd-callout {
  border: 1px solid var(--brand-line);
  border-radius: var(--brand-radius);
  background: var(--brand-bg);
  padding: 1rem;
  color: var(--brand-muted);
  font-size: 0.88rem;
  line-height: 1.7;
}

.wd-prose {
  color: #475569;
  font-size: 0.92rem;
  line-height: 1.75;
}

.wd-card {
  padding: 1.5rem;
}

.wd-flow {
  min-height: 38rem;
  display: grid;
  gap: 0.75rem;
  align-content: start;
  border: 1px solid var(--brand-line);
  border-radius: var(--brand-radius);
  background: var(--brand-bg);
  padding: 2rem;
}

.wd-flow-step {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.65rem;
  min-height: 3.9rem;
  border: 1px solid var(--brand-line);
  border-radius: var(--brand-radius);
  background: #FFFFFF;
  color: #475569;
  text-align: center;
  font-size: 0.88rem;
  font-weight: 720;
}

.wd-flow-step-active {
  border-color: var(--brand-cyan);
  color: var(--brand-primary);
  box-shadow: 0 2px 7px rgba(0, 98, 255, 0.09);
}

.wd-flow-step strong {
  color: var(--brand-primary);
}

.wd-flow-arrow {
  display: grid;
  place-items: center;
  color: #CBD5E1;
  font-size: 1.1rem;
  line-height: 1;
}

.wd-evidence-card {
  overflow: hidden;
  box-shadow: 0 2px 6px rgba(10, 27, 53, 0.05);
}

.wd-evidence-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.5rem;
  border-bottom: 1px solid #F1F5F9;
  background: var(--brand-bg);
}

.wd-evidence-title {
  margin: 0.55rem 0 0;
  color: var(--brand-dark);
  font-size: 1.05rem;
  font-weight: 780;
}

.wd-score-xl {
  color: var(--brand-primary);
  font-size: 1.85rem;
  font-weight: 330;
}

.wd-score-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.05fr);
  gap: 2rem;
  padding: 1.5rem;
}

.wd-score-row {
  display: grid;
  grid-template-columns: 7rem 1fr 2.8rem;
  gap: 0.8rem;
  align-items: center;
  margin: 0.72rem 0;
}

.wd-score-row span {
  color: var(--brand-muted);
  font-size: 0.75rem;
  font-weight: 700;
}

.wd-score-track {
  height: 0.42rem;
  border-radius: 999px;
  background: #F1F5F9;
  overflow: hidden;
}

.wd-score-fill {
  width: var(--score-width);
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--brand-primary), var(--brand-cyan));
}

.wd-quiz-shell {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(18rem, 22rem);
  gap: 2rem;
}

.wd-quiz-card {
  overflow: hidden;
  border: 1px solid var(--brand-line);
  border-radius: var(--brand-radius);
  background: #FFFFFF;
}

.wd-quiz-head {
  padding: 2rem;
  border-bottom: 1px solid #F1F5F9;
  background: var(--brand-bg);
}

.wd-quiz-question {
  margin: 0;
  color: var(--brand-dark);
  font-size: 1.22rem;
  line-height: 1.65;
  font-weight: 340;
}

.wd-option-list {
  display: grid;
  gap: 0.85rem;
  padding: 2rem;
}

.wd-option {
  border: 2px solid var(--brand-line);
  border-radius: var(--brand-radius);
  min-height: 4.6rem;
  padding: 1.25rem 1.45rem;
  color: #475569;
  background: #FFFFFF;
  line-height: 1.55;
  display: flex;
  align-items: center;
  gap: 0.8rem;
}

.wd-option strong {
  margin-right: 0.65rem;
  color: #94A3B8;
}

.main div[role="radiogroup"][aria-label="情景测试题"],
.main div[role="radiogroup"][aria-label="Scenario Quiz"] {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.85rem;
  overflow: visible;
  padding: 2rem;
  border: 1px solid var(--brand-line);
  border-top: 0;
  border-radius: 0 0 var(--brand-radius) var(--brand-radius);
  background: #FFFFFF;
}

.main div[role="radiogroup"][aria-label="情景测试题"] label[data-baseweb="radio"],
.main div[role="radiogroup"][aria-label="Scenario Quiz"] label[data-baseweb="radio"] {
  width: 100%;
  min-height: 4.6rem;
  border: 2px solid var(--brand-line);
  border-radius: var(--brand-radius);
  padding: 1.15rem 1.35rem;
  white-space: normal;
  box-shadow: none;
}

.main div[role="radiogroup"][aria-label="情景测试题"] label[data-baseweb="radio"]:hover,
.main div[role="radiogroup"][aria-label="Scenario Quiz"] label[data-baseweb="radio"]:hover {
  border-color: rgba(0, 98, 255, 0.35);
  background: #F8FBFF;
}

.main div[role="radiogroup"][aria-label="情景测试题"] label[data-baseweb="radio"]:has(input:checked),
.main div[role="radiogroup"][aria-label="Scenario Quiz"] label[data-baseweb="radio"]:has(input:checked) {
  background: var(--brand-bg);
  border-color: var(--brand-primary);
}

.main div[role="radiogroup"][aria-label="情景测试题"] label[data-baseweb="radio"] p,
.main div[role="radiogroup"][aria-label="Scenario Quiz"] label[data-baseweb="radio"] p {
  white-space: normal;
  line-height: 1.55;
}

.wd-table-shell {
  overflow-x: auto;
  min-height: 33rem;
  border: 1px solid var(--brand-line);
  border-radius: var(--brand-radius);
  background: #FFFFFF;
  box-shadow: 0 2px 6px rgba(10, 27, 53, 0.05);
}

.wd-table {
  width: 100%;
  border-collapse: collapse;
  color: #475569;
  font-size: 0.88rem;
}

.wd-table th {
  padding: 1.15rem 1.5rem;
  border-bottom: 1px solid var(--brand-line);
  background: var(--brand-bg);
  color: #94A3B8;
  text-align: left;
  font-size: 0.68rem;
  font-weight: 850;
}

.wd-table td {
  padding: 1.35rem 1.5rem;
  border-bottom: 1px solid #F1F5F9;
  vertical-align: middle;
}

.wd-table-action {
  color: var(--brand-primary) !important;
  font-size: 0.82rem;
  font-weight: 850;
  text-decoration: none !important;
}

.wd-history-head-cell {
  min-height: 3.2rem;
  padding: 0.9rem 1rem;
  background: var(--brand-bg);
  color: #94A3B8;
  border-top: 1px solid var(--brand-line);
  border-bottom: 1px solid var(--brand-line);
  font-size: 0.68rem;
  font-weight: 850;
}

.wd-history-cell {
  min-height: 5.2rem;
  padding: 1rem;
  border-bottom: 1px solid #F1F5F9;
  color: #334155;
  display: flex;
  align-items: center;
  line-height: 1.55;
}

.wd-history-action {
  min-height: 5.2rem;
  padding: 0.75rem 0;
  border-bottom: 1px solid #F1F5F9;
  display: flex;
  align-items: center;
}

.wd-history-action .stButton {
  width: 100%;
}

.wd-json-shell {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(18rem, 20rem);
  gap: 2rem;
}

.wd-code-panel {
  overflow: hidden;
  border: 1px solid var(--brand-line);
  border-radius: var(--brand-radius);
  background: #FFFFFF;
  box-shadow: 0 2px 6px rgba(10, 27, 53, 0.05);
}

.wd-code-head {
  display: flex;
  justify-content: space-between;
  padding: 0.9rem 1.25rem;
  border-bottom: 1px solid var(--brand-line);
  background: var(--brand-bg);
  color: #64748B;
  font-size: 0.72rem;
  font-weight: 850;
}

.wd-code-body {
  max-height: 43rem;
  overflow: auto;
  padding: 1.65rem;
  background: var(--brand-bg);
  color: #475569;
  font-size: 0.9rem;
  line-height: 1.65;
}

.wd-field {
  padding: 0.95rem 0;
  border-bottom: 1px solid #F1F5F9;
}

.wd-field code {
  color: var(--brand-primary);
  font-size: 0.8rem;
  font-weight: 780;
}

.wd-field div {
  margin-top: 0.35rem;
  color: var(--brand-muted);
  font-size: 0.78rem;
  line-height: 1.55;
}

.wd-empty {
  border: 1px dashed #CBD5E1;
  border-radius: var(--brand-radius);
  background: #FFFFFF;
  padding: 1.5rem;
  color: var(--brand-muted);
  line-height: 1.7;
}

.wd-side-note {
  border: 1px solid var(--brand-line);
  border-radius: var(--brand-radius);
  background: #FFFFFF;
  padding: 1.35rem;
  color: var(--brand-dark);
  font-size: 0.92rem;
  line-height: 1.75;
  box-shadow: 0 2px 6px rgba(10, 27, 53, 0.05);
}

.wd-inline-summary {
  border-left: 2px solid #CBD5E1;
  padding-left: 1rem;
  color: #64748B;
  font-size: 0.9rem;
  font-style: italic;
  line-height: 1.7;
}

.wd-search-wrap {
  max-width: 19.5rem;
  margin-left: auto;
}

@media (max-width: 1100px) {
  .wd-hero {
    grid-template-columns: minmax(0, 1fr) minmax(15rem, 0.72fr);
    min-height: 36rem;
    padding: 3.2rem 2.6rem;
  }
  .wd-hero h1 {
    max-width: 11ch;
    font-size: 3.2rem;
  }
  .wd-hero p {
    max-width: 28rem;
    font-size: 1.04rem;
  }
  .wd-hero-cta {
    min-width: 17.5rem;
    min-height: 4rem;
    margin-top: 2.6rem;
  }
  .wd-hero-orbit {
    min-height: 19rem;
  }
  .wd-orbit {
    width: 19rem;
  }
  .wd-feature-grid,
  .wd-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .wd-feature-card:nth-child(2),
  .wd-feature-card:nth-child(4) {
    transform: none;
  }
  .wd-work-grid,
  .wd-quiz-shell,
  .wd-json-shell,
  .wd-page-grid-2,
  .wd-page-grid-flow,
  .wd-page-grid-side {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .main .block-container {
    padding: 1.2rem 1rem 3rem;
  }
  .wd-view-header {
    align-items: flex-start;
    flex-direction: column;
  }
  .wd-action-header {
    align-items: flex-start;
    flex-direction: column;
  }
  .wd-hero {
    grid-template-columns: 1fr;
    min-height: auto;
    padding: 2rem 1.45rem;
  }
  .wd-hero h1 {
    max-width: 100%;
    font-size: 2.55rem;
    line-height: 1.12;
  }
  .wd-hero p {
    margin-top: 1.35rem;
    font-size: 1rem;
    line-height: 1.68;
  }
  .wd-hero-cta {
    width: 100%;
    min-width: 0;
    min-height: 3.55rem;
    margin-top: 2rem;
    padding: 0 1.25rem;
    font-size: 0.95rem;
  }
  .wd-hero-orbit {
    display: none;
  }
  .wd-feature-grid,
  .wd-stats,
  .wd-score-grid {
    grid-template-columns: 1fr;
  }
  .wd-evidence-head {
    flex-direction: column;
  }
  .wd-score-row {
    grid-template-columns: 1fr;
  }
  .wd-soft-panel,
  .wd-result-panel,
  .wd-quiz-head,
  .wd-option-list {
    padding: 1.2rem;
  }
  .wd-table-shell {
    min-height: 22rem;
  }
}
</style>
""",
        unsafe_allow_html=True,
    )


def extract_uploaded_images(uploaded_images) -> list[OcrResult]:
    if not uploaded_images:
        return []

    extractor = load_ocr_extractor()
    results: list[OcrResult] = []
    for uploaded in uploaded_images:
        suffix = Path(uploaded.name).suffix or ".png"
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                handle.write(uploaded.getbuffer())
                temp_path = Path(handle.name)
            results.append(extractor.extract(temp_path, image_name=uploaded.name))
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)
    return results


def escape_text(value: Any) -> str:
    return html.escape(str(value or ""))


def html_text(value: Any) -> str:
    return escape_text(value).replace("\n", "<br>")


def as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def score_percent(value: Any) -> int:
    score = coerce_float(value)
    if score <= 1.0:
        score *= 100.0
    return int(round(max(0.0, min(score, 100.0))))


def score_fraction(value: Any) -> float:
    score = coerce_float(value)
    if score > 1.0:
        score /= 100.0
    return max(0.0, min(score, 1.0))


def normalize_risk_level(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text.startswith("high") or text.startswith("高"):
        return "High"
    if text.startswith("medium") or text.startswith("moderate") or text.startswith("中"):
        return "Medium"
    if text.startswith("low") or text.startswith("低"):
        return "Low"
    return "Unknown"


def risk_style(parsed: dict[str, Any] | None) -> dict[str, str]:
    level = normalize_risk_level((parsed or {}).get("risk_level"))
    style = dict(RISK_STYLES[level])
    if current_language() == "en":
        style["label"] = {"High": "High Risk", "Medium": "Medium Risk", "Low": "Low Risk", "Unknown": "Pending"}[level]
        style["message"] = {
            "High": "Clear fraud signals detected. Stop all actions immediately.",
            "Medium": "Suspicious signals detected. Verify before continuing.",
            "Low": "No obvious fraud signals detected.",
            "Unknown": "Submit content to generate a diagnosis.",
        }[level]
    return style


def chip(text: Any, tone: str = "cyan") -> str:
    tone = tone if tone in {"cyan", "green", "orange", "red", "purple"} else "cyan"
    return f'<span class="wd-chip wd-chip-{tone}">{escape_text(text)}</span>'


def current_language() -> str:
    return st.session_state.get("language", "zh")


def t(key: str) -> str:
    value = UI_TEXT.get(key)
    if isinstance(value, dict):
        return value.get(current_language()) or value.get("zh") or key
    return key


def nav_label(page: str) -> str:
    return NAV_LABELS.get(current_language(), NAV_LABELS["zh"]).get(page, page)


def input_mode_label(mode: str) -> str:
    return INPUT_MODE_LABELS.get(current_language(), INPUT_MODE_LABELS["zh"]).get(mode, mode)


def example_label(example_name: str) -> str:
    return EXAMPLE_LABELS.get(current_language(), EXAMPLE_LABELS["zh"]).get(example_name, example_name)


def risk_tone_from_label(label: Any) -> str:
    text = str(label or "").strip().lower()
    if text.startswith("高") or text.startswith("high"):
        return "red"
    if text.startswith("中") or text.startswith("medium"):
        return "orange"
    if text.startswith("低") or text.startswith("low"):
        return "green"
    return "cyan"


def localized_examples() -> dict[str, str]:
    return EXAMPLES_BY_LANG.get(current_language(), EXAMPLES_BY_LANG["zh"])


def localized_demo_result(language: str) -> dict[str, Any]:
    result = json.loads(json.dumps(DEMO_RESULT, ensure_ascii=False))
    result["_demo"] = True
    result["_lang"] = language
    if language != "en":
        return result
    result["input_text"] = EXAMPLES_BY_LANG["en"]["中文奖助学金诈骗"]
    result["risk_features"] = {
        "matched_categories": ["Suspicious link", "Bank card info", "SMS code", "Urgent wording"],
        "matched_terms": ["grant", "ID number", "bank card", "SMS code"],
        "urls": ["http://campus-grant.example.cn"],
        "domains": ["campus-grant.example.cn"],
        "money_mentions": [],
    }
    result["retrieved_evidence"] = [
        {
            "id": "E1",
            "title": "Campus grant and fake financial-aid center scam rules",
            "reason": "Contains keywords such as grant, bank card, and SMS code",
            "bm25_score": 0.82,
            "dense_score": 0.76,
            "url_match_score": 0.0,
            "risk_keyword_score": 0.9,
            "reranker_score": 0.88,
            "score": 0.81,
            "content": "Scammers often impersonate university financial-aid offices or platform support teams and use grants, account freezes, or system updates to lure students into phishing pages that collect bank cards, ID numbers, and SMS codes.",
        },
        {
            "id": "E2",
            "title": "Short-link and lookalike-domain risk warning",
            "reason": "Matches a suspicious URL pattern and urgent deadline wording",
            "bm25_score": 0.38,
            "dense_score": 0.67,
            "url_match_score": 0.85,
            "risk_keyword_score": 0.72,
            "reranker_score": 0.85,
            "score": 0.75,
            "content": "Phishing pages may imitate campus services or official notices and use urgent deadlines to pressure users into submitting identity, payment, or SMS verification information.",
        },
    ]
    result["analysis"] = {
        "risk_level": "High",
        "risk_score": 0.89,
        "fraud_type": "Fake financial-aid office / phishing link / SMS-code harvesting",
        "risk_signals": ["Suspicious link", "Bank card request", "SMS code", "Identity info", "Urgent deadline"],
        "natural_language_report": "The message impersonates a campus financial-aid center, offers a grant, and asks the student to click a link and enter ID, bank card, and SMS verification code information before a deadline. This matches a high-risk phishing pattern.",
        "anti_fraud_suggestion": "Stop immediately. Do not click the link or submit ID numbers, bank card details, passwords, or SMS codes. Verify through the official university website, counselor, or financial-aid system, and keep screenshots as evidence.",
        "compliance_rewrite": "Do not click unknown links in SMS or chat messages, and never provide bank card numbers, passwords, or SMS codes to strangers. Real university financial-aid notices are issued through official channels. To verify, log in to the official school system or contact your counselor.",
        "compliance_reminder": "Any unknown link that asks for an SMS code, bank card, or ID information should be verified through official channels first.",
        "training_question": {
            "question": "If an unknown SMS claims to be from the university financial-aid center and asks you to click a link, enter your bank card, and provide an SMS code to receive a grant, what should you do?",
            "options": [
                {"text": "Fill it in quickly to avoid missing the grant"},
                {"text": "Add the sender on WeChat and ask for more details"},
                {"text": "Refuse to click or provide information, then verify through official university channels"},
                {"text": "Send the SMS code to the sender so they can process it"},
            ],
            "reference_answer": "Choose C. Bank card details, SMS codes, and unknown links appearing together are high-risk fraud signals. Stop and verify through official channels.",
        },
    }
    return result


def localized_demo_history(language: str) -> list[dict[str, Any]]:
    if language != "en":
        return json.loads(json.dumps(DEMO_HISTORY, ensure_ascii=False))
    return [
        {
            "时间": "2026-06-15 14:30:00",
            "输入类型": "TEXT",
            "风险等级": "High Risk",
            "诈骗类型": "Fake financial-aid office / phishing link / SMS-code harvesting",
            "风险评分": 89,
            "证据数": 2,
            "内容摘要": EXAMPLES_BY_LANG["en"]["中文奖助学金诈骗"][:72],
        },
        {
            "时间": "2026-06-14 09:12:00",
            "输入类型": "URL",
            "风险等级": "Medium Risk",
            "诈骗类型": "Suspicious phishing link",
            "风险评分": 67,
            "证据数": 1,
            "内容摘要": "http://taobao-security-update.example/login",
        },
    ]


def logo_data_uri() -> str | None:
    if not LOGO_PATH.exists():
        return None
    encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def render_sidebar_brand() -> None:
    logo_uri = logo_data_uri()
    logo_html = f'<img src="{logo_uri}" alt="Anti-Fraud Coach logo">' if logo_uri else "AF"
    st.markdown(
        f"""
<div class="wd-sidebar-brand">
  <div class="wd-logo-box">{logo_html}</div>
  <div>
    <div class="wd-brand-title">Anti-Fraud Coach</div>
    <div class="wd-brand-subtitle">{t("brand_subtitle")}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_view_header(title: str, subtitle: str, pill: str | None = None) -> None:
    pill_html = f'<span class="wd-pill">{escape_text(pill)}</span>' if pill else ""
    st.markdown(
        f"""
<div class="wd-view-header">
  <div>
    <h2 class="wd-view-title">{title}</h2>
    <p class="wd-view-copy">{escape_text(subtitle)}</p>
  </div>
  {pill_html}
</div>
""",
        unsafe_allow_html=True,
    )


def query_param_value(name: str) -> str | None:
    value = st.query_params.get(name)
    if isinstance(value, list):
        value = value[0] if value else None
    return str(value) if value is not None else None


def public_history_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if not str(key).startswith("_")}


def activate_history_report(raw_index: str | None) -> bool:
    try:
        index = int(str(raw_index))
    except (TypeError, ValueError):
        return False

    history = st.session_state.get("history", [])
    if not (0 <= index < len(history)):
        return False

    entry = history[index]
    result = entry.get("_result")
    if not isinstance(result, dict) and index == 0 and isinstance(st.session_state.get("latest_result"), dict):
        result = st.session_state.latest_result
    if not isinstance(result, dict):
        return False

    analysis_text = entry.get("_analysis_text") or result.get("input_text") or entry.get("内容摘要") or ""
    st.session_state.latest_result = result
    st.session_state.latest_analysis_text = analysis_text
    st.session_state.input_text = analysis_text
    st.session_state.latest_ocr_results = entry.get("_ocr_results") or []
    input_mode = entry.get("_input_mode")
    if input_mode in INPUT_MODES:
        st.session_state.input_mode = input_mode
    return True


def init_session_state() -> None:
    pending_language = st.session_state.get("pending_language")
    if pending_language in LANGUAGE_OPTIONS:
        st.session_state.language = pending_language
        st.session_state.language_picker = pending_language
        st.session_state.last_query_lang = pending_language
        st.query_params["lang"] = pending_language
        del st.session_state.pending_language
    else:
        query_lang = query_param_value("lang")
        query_language = str(query_lang) if str(query_lang) in LANGUAGE_OPTIONS else None
        if "language" not in st.session_state:
            st.session_state.language = query_language or "zh"
        if query_language and st.session_state.get("last_query_lang") != query_language:
            st.session_state.language = query_language
            st.session_state.language_picker = query_language
            st.session_state.last_query_lang = query_language
        elif "last_query_lang" not in st.session_state:
            st.session_state.last_query_lang = st.session_state.language
    if "previous_language" not in st.session_state:
        st.session_state.previous_language = st.session_state.language
    if "page" not in st.session_state:
        st.session_state.page = "首页概览"
    if "nav_page" not in st.session_state:
        st.session_state.nav_page = st.session_state.page
    if "input_text" not in st.session_state:
        st.session_state.input_text = ""
    if "latest_result" not in st.session_state:
        st.session_state.latest_result = None
    if "latest_ocr_results" not in st.session_state:
        st.session_state.latest_ocr_results = []
    if "latest_analysis_text" not in st.session_state:
        st.session_state.latest_analysis_text = ""
    if "history" not in st.session_state:
        st.session_state.history = []
    if isinstance(st.session_state.get("latest_result"), dict) and st.session_state.latest_result.get("_demo"):
        st.session_state.latest_result = None
        st.session_state.latest_ocr_results = []
        st.session_state.latest_analysis_text = ""
    demo_histories = [localized_demo_history("zh"), localized_demo_history("en")]
    if st.session_state.get("history") in demo_histories:
        st.session_state.history = []

    if st.session_state.previous_language != current_language():
        demo_like = bool((st.session_state.latest_result or {}).get("_demo"))
        if demo_like:
            st.session_state.latest_result = localized_demo_result(current_language())
            st.session_state.latest_analysis_text = st.session_state.latest_result["input_text"]
            st.session_state.input_text = localized_examples()["中文奖助学金诈骗"]
            st.session_state.history = localized_demo_history(current_language())
        st.session_state.previous_language = current_language()

    query_view = query_param_value("view")
    query_run = query_param_value("run")
    query_report = query_param_value("report")
    query_page = QUERY_VIEW_TO_PAGE.get(str(query_view)) if query_view else None
    report_selected = activate_history_report(query_report) if query_report is not None else False
    if query_report is not None and not report_selected:
        st.session_state.history_report_missing = True
    if query_run == "analysis":
        st.session_state.pending_analysis = True
    if query_page:
        st.session_state.page = query_page
        st.session_state.nav_page = query_page
    if query_page or query_run or query_report is not None:
        active_language = current_language()
        st.query_params.clear()
        st.query_params["lang"] = active_language
        st.session_state.last_query_lang = active_language


def navigate_to(page: str) -> None:
    st.session_state.pending_page = page
    st.rerun()


def run_analysis(
    input_text: str,
    uploaded_images,
    top_k: int,
    mock: bool,
    qwen_key: str,
) -> tuple[dict[str, Any] | None, list[OcrResult], str]:
    ocr_results: list[OcrResult] = []
    if uploaded_images:
        with st.spinner(t("ocr_spinner")):
            ocr_results = extract_uploaded_images(uploaded_images)

    preprocessed_input = preprocess_analysis_input(input_text, ocr_results)
    analysis_text = preprocessed_input.normalized_text
    if not analysis_text.strip():
        st.warning(t("empty_input"))
        return None, ocr_results, analysis_text

    with st.spinner(t("analysis_spinner")):
        engine = load_engine()
        result = engine.analyze(analysis_text, top_k=top_k, mock=mock, api_key=qwen_key or None)
        result["image_ocr"] = [ocr_result.to_dict() for ocr_result in ocr_results]
        result["input_mode_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return result, ocr_results, analysis_text


def append_history(
    result: dict[str, Any],
    input_mode: str,
    analysis_text: str,
    ocr_results: list[OcrResult] | None = None,
) -> None:
    parsed = result.get("analysis", {})
    risk_label = risk_style(parsed)["label"]
    entry = {
        "时间": result.get("input_mode_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "输入类型": input_mode_label(input_mode),
        "风险等级": risk_label,
        "诈骗类型": parsed.get("fraud_type", "Unknown"),
        "风险评分": score_percent(parsed.get("risk_score")),
        "证据数": len(result.get("retrieved_evidence", [])),
        "内容摘要": analysis_text[:72],
        "_result": result,
        "_analysis_text": analysis_text,
        "_ocr_results": list(ocr_results or []),
        "_input_mode": input_mode,
    }
    st.session_state.history = [entry] + st.session_state.history[:24]


def score_bar_html(label: str, value: Any) -> str:
    fraction = score_fraction(value)
    return (
        f'<div class="wd-score-row"><span>{escape_text(label)}</span>'
        f'<div class="wd-score-track"><div class="wd-score-fill" style="--score-width: {fraction * 100:.1f}%;"></div></div>'
        f"<span>{fraction:.2f}</span></div>"
    )


def render_home() -> None:
    title_html = t("home_title")
    st.markdown(
        f"""
<div class="wd-view">
  <section class="wd-hero">
    <div>
      <h1>{title_html}</h1>
      <p>{escape_text(t("home_copy"))}</p>
      <a class="wd-hero-cta" href="?view=recognition&amp;lang={escape_text(current_language())}">{escape_text(t("home_cta"))} <span>→</span></a>
    </div>
    <div class="wd-hero-orbit">
      <div class="wd-orbit">
        <svg class="wd-shield-mark" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
          <path d="M32 8L51 16V30C51 43.5 43.1 53.1 32 58C20.9 53.1 13 43.5 13 30V16L32 8Z" fill="none" stroke="currentColor" stroke-width="5.5" stroke-linejoin="round"/>
          <path d="M24.5 32.5L30.3 38.2L41.5 26.8" fill="none" stroke="currentColor" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
    </div>
  </section>
</div>
""",
        unsafe_allow_html=True,
    )

    features = [
        ("IN", t("feature_input_title"), t("feature_input_copy")),
        ("FX", t("feature_risk_title"), t("feature_risk_copy")),
        ("RG", t("feature_rag_title"), t("feature_rag_copy")),
        ("QA", t("feature_training_title"), t("feature_training_copy")),
    ]
    feature_html = "".join(
        f"""
<article class="wd-feature-card">
  <div class="wd-feature-icon">{escape_text(icon)}</div>
  <h3>{escape_text(title)}</h3>
  <p>{escape_text(copy)}</p>
</article>
"""
        for icon, title, copy in features
    )
    st.markdown(
        f"""
<div class="wd-view" style="margin-top: 2.4rem;">
  <section class="wd-feature-grid">{feature_html}</section>
</div>
""",
        unsafe_allow_html=True,
    )


def render_recognition(qwen_key: str, mock: bool, top_k: int, example_name: str, use_example: bool) -> None:
    if use_example:
        st.session_state.input_text = localized_examples()[example_name]
    if st.session_state.pop("history_report_missing", False):
        st.warning(t("history_report_missing"))

    st.markdown(
        f"""
<div class="wd-action-header" style="border-bottom: 0; padding-bottom: 0;">
  <div>
    <h2>{t("recognition_title")}</h2>
    <p>{t("recognition_subtitle")}</p>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown('<div style="border-bottom: 1px solid var(--brand-line); margin: 0.35rem 0 2rem;"></div>', unsafe_allow_html=True)

    left, right = st.columns([1.02, 1], gap="large")
    with left:
        with st.container(border=True):
            st.markdown(f'<div class="wd-section-label" style="margin-top: 0;">{t("input_type")}</div>', unsafe_allow_html=True)
            input_mode = st.radio(
                t("input_type"),
                INPUT_MODES,
                index=0,
                horizontal=True,
                label_visibility="collapsed",
                format_func=input_mode_label,
                key="input_mode",
            )
            uploaded_images = None
            if input_mode == "聊天截图":
                uploaded_images = st.file_uploader(
                    t("upload_screenshot"),
                    type=["png", "jpg", "jpeg", "webp", "bmp"],
                    accept_multiple_files=True,
                    help=t("upload_help"),
                )
                input_text = st.text_area(
                    t("ocr_edit"),
                    value=st.session_state.input_text,
                    height=110,
                    placeholder=t("ocr_placeholder"),
                )
            else:
                input_text = st.text_area(
                    t("recognition_title"),
                    value=st.session_state.input_text,
                    height=360,
                    placeholder=INPUT_PLACEHOLDERS_BY_LANG[current_language()][input_mode],
                )
                uploaded_images = st.file_uploader(
                    t("optional_upload"),
                    type=["png", "jpg", "jpeg", "webp", "bmp"],
                    accept_multiple_files=True,
                )
            st.session_state.input_text = input_text
            if uploaded_images:
                st.image(uploaded_images, caption=[image.name for image in uploaded_images], width=260)
            analyze_clicked = st.button(t("analyze"), type="primary", use_container_width=True, key="analyze_content")

        analyze = analyze_clicked or bool(st.session_state.pop("pending_analysis", False))
        if analyze:
            result, ocr_results, analysis_text = run_analysis(input_text, uploaded_images, top_k, mock, qwen_key)
            st.session_state.latest_result = result
            st.session_state.latest_ocr_results = ocr_results
            st.session_state.latest_analysis_text = analysis_text
            if result:
                append_history(result, input_mode, analysis_text, ocr_results)

    with right:
        with st.container(border=True):
            latest = st.session_state.latest_result
            if latest:
                parsed = latest.get("analysis", {})
                if parsed.get("api_error"):
                    st.warning(t("qwen_fallback"))
                render_risk_diagnosis(latest)
            else:
                render_waiting_panel()

    latest = st.session_state.latest_result
    if latest:
        render_ocr_results(st.session_state.latest_ocr_results)
        render_report_sections(latest)


def render_waiting_panel() -> None:
    style = risk_style({"risk_level": "Unknown"})
    st.markdown(
        f"""
<div class="wd-risk-card" style="--risk-color: {style["accent"]}; --risk-surface: {style["surface"]};">
  <div class="wd-risk-top">
    <div>
      <div class="wd-risk-label">{style["label"]}</div>
      <p class="wd-prose" style="margin: 0.35rem 0 0; font-weight: 720; color: var(--brand-dark);">{style["message"]}</p>
    </div>
    <div class="wd-risk-score">0 / 100</div>
  </div>
</div>
<div class="wd-section-label">{t("risk_features")}</div>
<div class="wd-chip-row">
  {chip(t("risk_level"), "cyan")}
  {chip(t("fraud_type"), "cyan")}
  {chip(t("evidence_chain"), "cyan")}
</div>
<div class="wd-callout" style="margin-top: 1.45rem;">{escape_text(t("result_hint"))}</div>
<div class="wd-section-label">{t("suggestions")}</div>
<div class="wd-prose">{escape_text(t("suggestions_waiting"))}</div>
""",
        unsafe_allow_html=True,
    )


def render_risk_diagnosis(result: dict[str, Any]) -> None:
    parsed = result.get("analysis", {})
    style = risk_style(parsed)
    score = score_percent(parsed.get("risk_score"))
    fraud_type = parsed.get("fraud_type", "Unknown")
    st.markdown(
        f"""
<div class="wd-risk-card" style="--risk-color: {style["accent"]}; --risk-surface: {style["surface"]};">
  <div class="wd-risk-top">
    <div>
      <div class="wd-risk-label">{escape_text(style["label"])}</div>
      <p class="wd-prose" style="margin: 0.35rem 0 0;"><span style="color: #64748B;">{escape_text(t("suspected_type"))}</span> {escape_text(fraud_type)}</p>
    </div>
    <div class="wd-risk-score">{escape_text(t("risk_score"))}: <strong>{score}</strong> / 100</div>
  </div>
  <div class="wd-alert-strip">{escape_text(style["message"])}</div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown(f'<div class="wd-section-label">{t("risk_features")}</div>', unsafe_allow_html=True)
    render_feature_tags(result.get("risk_features", {}), parsed)
    signals = as_list(parsed.get("risk_signals"))
    if signals:
        signal_html = "".join(chip(signal, "orange" if i < 2 else "cyan") for i, signal in enumerate(signals[:5]))
        st.markdown(f'<div class="wd-callout" style="margin-top: 1rem;">{signal_html}</div>', unsafe_allow_html=True)
    suggestion = parsed.get("anti_fraud_suggestion") or parsed.get("suggestion")
    if suggestion:
        st.markdown(
            f"""
<div class="wd-section-label">{t("suggestions")}</div>
<div class="wd-prose">{html_text(suggestion)}</div>
""",
            unsafe_allow_html=True,
        )


def render_feature_tags(features: dict[str, Any], parsed: dict[str, Any]) -> None:
    categories = features.get("matched_categories") or []
    terms = features.get("matched_terms") or []
    urls = features.get("urls") or []
    domains = features.get("domains") or []
    money = features.get("money_mentions") or []
    chips: list[str] = []
    for category in categories[:6]:
        chips.append(chip(category, FEATURE_TONES.get(str(category), "cyan")))
    for term in terms[:6]:
        chips.append(chip(term, "cyan"))
    for value in urls[:1] + domains[:1]:
        chips.append(chip(value, "purple"))
    for value in money[:2]:
        chips.append(chip(value, "red"))

    if not chips:
        fallback_features = parsed.get("risk_features", {})
        if isinstance(fallback_features, dict):
            chips = [chip(key, "cyan") for key, value in fallback_features.items() if value][:10]

    if chips:
        st.markdown('<div class="wd-chip-row">' + "".join(chips[:14]) + "</div>", unsafe_allow_html=True)
    else:
        empty_text = "No clear risk features were extracted." if current_language() == "en" else "暂未提取到明确风险特征。"
        st.markdown(f'<div class="wd-empty">{empty_text}</div>', unsafe_allow_html=True)


def render_report_sections(result: dict[str, Any]) -> None:
    parsed = result.get("analysis", {})
    st.markdown(f'<div class="wd-section-label">{t("core_output")}</div>', unsafe_allow_html=True)
    report_tab, training_tab, rewrite_tab = st.tabs([t("report_tab"), t("training_tab"), t("rewrite_tab")])

    with report_tab:
        report_col, advice_col = st.columns([1, 1], gap="large")
        with report_col:
            st.markdown(
                f"""
<div class="wd-card">
  <h3>{t("summary_judgment")}</h3>
  <div class="wd-prose">{html_text(parsed.get("natural_language_report") or parsed.get("reasoning") or t("no_report"))}</div>
</div>
""",
                unsafe_allow_html=True,
            )
        with advice_col:
            st.markdown(
                f"""
<div class="wd-card">
  <h3>{t("immediate_advice")}</h3>
  <div class="wd-prose">{html_text(parsed.get("anti_fraud_suggestion") or t("default_advice"))}</div>
</div>
""",
                unsafe_allow_html=True,
            )

    with training_tab:
        render_training_question(parsed, compact=True)

    with rewrite_tab:
        st.markdown(
            f"""
<div class="wd-card">
  <h3>{t("safe_rewrite")}</h3>
  <div class="wd-prose">{html_text(parsed.get("compliance_rewrite") or t("default_rewrite"))}</div>
</div>
""",
            unsafe_allow_html=True,
        )


def training_content_language(*parts: str) -> str:
    detected = detect_language(" ".join(part for part in parts if part))
    return detected if detected in LANGUAGE_OPTIONS else current_language()


def default_training_options(language: str) -> list[str]:
    if language == "en":
        return [
            "Keep clicking the unknown link",
            "Transfer money as requested",
            "Verify through official channels and keep evidence",
            "Give the SMS code to the stranger",
        ]
    return ["继续点击陌生链接", "先按要求转账", "通过官方渠道核实并保留证据", "向陌生人提供验证码"]


def default_training_reference(language: str) -> str:
    if language == "en":
        return "Verify through official channels and keep evidence."
    return "通过官方渠道核实并保留证据。"


def parse_training_question(parsed: dict[str, Any]) -> tuple[str, list[str], str]:
    question = parsed.get("training_question")
    if isinstance(question, dict):
        question_text = str(question.get("question") or ("What should you do next when content looks suspicious?" if current_language() == "en" else "遇到疑似诈骗内容时，下一步应该怎么做？"))
        question_language = training_content_language(question_text)
        raw_options = question.get("options") or question.get("choices") or []
        options = [str(option.get("text") if isinstance(option, dict) else option) for option in raw_options]
        reference = str(
            question.get("reference_answer")
            or question.get("answer")
            or question.get("explanation")
            or default_training_reference(question_language)
        )
    elif question:
        question_text = str(question)
        question_language = training_content_language(question_text)
        options = default_training_options(question_language)
        reference = default_training_reference(question_language)
    else:
        question_text = "If a stranger asks you to click a link and provide an SMS code, what should you do?" if current_language() == "en" else "如果陌生人要求你点击链接并提供验证码，你应该怎么做？"
        options = ["Continue", "Provide the SMS code", "Verify through official channels and refuse to share sensitive information", "Transfer money to verify identity"] if current_language() == "en" else ["继续操作", "提供验证码", "通过官方渠道核实并拒绝提供敏感信息", "转账验证身份"]
        reference = "Verify through official channels and refuse to share sensitive information." if current_language() == "en" else "通过官方渠道核实并拒绝提供敏感信息。"
    if not options:
        options = default_training_options(training_content_language(question_text, reference))
    return question_text, options, reference


def render_training_question(parsed: dict[str, Any], compact: bool = False) -> None:
    question_text, options, reference = parse_training_question(parsed)
    option_indices = list(range(len(options)))
    st.markdown(
        f"""
<div class="wd-quiz-card">
  <div class="wd-quiz-head">
    <div class="wd-section-label" style="margin-top: 0;">{t("quiz_label")}</div>
    <p class="wd-quiz-question">{escape_text(question_text)}</p>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    selected_index = st.radio(
        t("quiz_label"),
        option_indices,
        index=None,
        format_func=lambda index: f"{chr(65 + index)}. {options[index]}",
        key=f"training_choice_{current_language()}_{'compact' if compact else 'full'}",
        label_visibility="collapsed",
    )
    if selected_index is not None:
        st.markdown(
            f"""
<div class="wd-callout" style="margin-top: 1rem;">
  {chip(t("your_selection"), "cyan")}
  <div style="margin-top: 0.75rem;">{escape_text(chr(65 + selected_index))}. {html_text(options[selected_index])}</div>
</div>
""",
            unsafe_allow_html=True,
        )
    if st.button(t("show_answer"), key=f"answer_{'compact' if compact else 'full'}"):
        st.markdown(
            f"""
<div class="wd-callout" style="margin-top: 1rem;">
  {chip(t("reference_answer"), "green")}
  <div style="margin-top: 0.75rem;">{html_text(reference)}</div>
</div>
""",
            unsafe_allow_html=True,
        )


def render_ocr_results(ocr_results: list[OcrResult]) -> None:
    if not ocr_results:
        return
    st.markdown(f'<div class="wd-section-label">{t("ocr_text")}</div>', unsafe_allow_html=True)
    for result in ocr_results:
        with st.expander(f"{result.image_name} OCR result", expanded=bool(result.text.strip())):
            if result.error:
                st.warning(result.error)
            if result.text.strip():
                st.text_area(t("recognized_text"), value=result.text, height=140, disabled=True)
                if result.lines:
                    st.dataframe([line.to_dict() for line in result.lines], use_container_width=True)
            elif not result.error:
                st.info(t("no_ocr"))


def render_evidence_page() -> None:
    render_view_header(t("evidence_title"), t("evidence_subtitle"), None)

    result = st.session_state.latest_result
    if not result:
        st.markdown(f'<div class="wd-empty">{t("no_evidence")}</div>', unsafe_allow_html=True)
        return

    left, right = st.columns([0.3, 1], gap="large")
    with left:
        flow_steps = [
            t("flow_user"),
            t("flow_features"),
            t("flow_retrieval"),
            t("flow_fusion"),
            t("flow_reranker"),
            t("flow_reasoning"),
        ]
        flow_parts = []
        for index, step in enumerate(flow_steps):
            active = " wd-flow-step-active" if step == t("flow_retrieval") else ""
            flow_parts.append(f'<div class="wd-flow-step{active}">{"<strong>" if active else ""}{escape_text(step)}{"</strong>" if active else ""}</div>')
            if index < len(flow_steps) - 1:
                flow_parts.append('<div class="wd-flow-arrow">↓</div>')
        flow_html = "".join(flow_parts)
        st.markdown(f'<div class="wd-flow">{flow_html}</div>', unsafe_allow_html=True)
    with right:
        st.markdown(f'<div class="wd-section-label" style="margin-top: 0;">{t("evidence_details")}</div>', unsafe_allow_html=True)
        for index, item in enumerate(result.get("retrieved_evidence", []), start=1):
            render_evidence_item(item, index)


def render_evidence_item(item: dict[str, Any], index: int) -> None:
    title = item.get("title", "Untitled evidence")
    fallback_reason = "Matched a similar fraud knowledge snippet" if current_language() == "en" else "命中相似诈骗知识片段"
    reason = item.get("reason") or item.get("match_reason") or item.get("source", fallback_reason)
    rerank = item.get("reranker_score", item.get("score", 0.0))
    content = item.get("text") or item.get("content") or ""
    score_html = "".join(
        [
            score_bar_html("BM25", item.get("bm25_score", 0.0)),
            score_bar_html("Dense (BGE-M3)", item.get("dense_score", 0.0)),
            score_bar_html("URL Match", item.get("url_match_score", 0.0)),
            score_bar_html("Risk Keyword", item.get("risk_keyword_score", 0.0)),
        ]
    )
    st.markdown(
        f"""
<article class="wd-evidence-card" style="margin-bottom: 1.5rem;">
  <div class="wd-evidence-head">
    <div>
      {chip(f"{t('evidence_badge')} {index}", "cyan")}
      <h3 class="wd-evidence-title">{escape_text(title)}</h3>
      <p class="wd-prose" style="margin: 0.5rem 0 0;">{escape_text(t("match_reason"))}{escape_text(reason)}</p>
    </div>
    <div>
      <div class="wd-section-label" style="margin: 0 0 0.25rem;">{t("rerank_score")}</div>
      <div class="wd-score-xl">{score_fraction(rerank):.2f}</div>
    </div>
  </div>
  <div class="wd-score-grid">
    <div>
      <div class="wd-section-label" style="margin-top: 0;">{t("retrieval_scores")}</div>
      {score_html}
    </div>
    <div>
      <div class="wd-section-label" style="margin-top: 0;">{t("matched_content")}</div>
      <div class="wd-callout">{html_text(content)}</div>
    </div>
  </div>
</article>
""",
        unsafe_allow_html=True,
    )


def render_training_center() -> None:
    render_view_header(f'<span class="wd-title-with-icon"><span class="wd-title-icon">□</span><span>{t("training_title")}</span></span>', t("training_subtitle"), None)
    result = st.session_state.latest_result
    if not result:
        st.markdown(f'<div class="wd-empty">{t("no_training")}</div>', unsafe_allow_html=True)
        return
    parsed = result.get("analysis", {})
    left, right = st.columns([1, 0.43], gap="large")
    with left:
        render_training_question(parsed)
    with right:
        rewrite = parsed.get("compliance_rewrite") or t("default_rewrite")
        reminder = parsed.get("compliance_reminder") or ("If you need to verify an account status, log in to the official app or contact an official school channel." if current_language() == "en" else "如需核实账号状态，请直接登录官方 App 或联系学校官方渠道。")
        st.markdown(
            f"""
<div class="wd-panel wd-panel-blue">
  <div class="wd-section-label" style="margin-top: 0;">{t("core_rewrite")}</div>
  <div class="wd-section-label">{t("original_summary")}</div>
  <div class="wd-inline-summary">{html_text(st.session_state.latest_analysis_text[:120])}</div>
  <div class="wd-section-label">{t("safe_version")}</div>
  <div class="wd-side-note">{html_text(rewrite)}</div>
  <div class="wd-section-label">{t("learning_reminder")}</div>
  <div class="wd-prose">{html_text(reminder)}</div>
</div>
""",
            unsafe_allow_html=True,
        )


def render_history_page() -> None:
    header_left, header_right = st.columns([1, 0.33], gap="large")
    with header_left:
        st.markdown(
            f"""
<div class="wd-action-header" style="border-bottom: 0; padding-bottom: 0;">
  <div>
    <h2>{t("history_title")}</h2>
    <p>{t("history_subtitle")}</p>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
    with header_right:
        st.markdown('<div class="wd-search-wrap">', unsafe_allow_html=True)
        query = st.text_input("Search records", placeholder=t("history_search"), label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown('<div style="border-bottom: 1px solid var(--brand-line); margin: 0.35rem 0 1.75rem;"></div>', unsafe_allow_html=True)
    history = st.session_state.history
    if not history:
        st.markdown(f'<div class="wd-empty">{t("history_empty")}</div>', unsafe_allow_html=True)
        return
    rows = list(enumerate(history))
    if query.strip():
        needle = query.strip().lower()
        rows = [
            (index, row)
            for index, row in rows
            if needle in json.dumps(public_history_row(row), ensure_ascii=False).lower()
        ]
    if not rows:
        st.markdown(f'<div class="wd-empty">{t("history_empty")}</div>', unsafe_allow_html=True)
        return

    with st.container(border=True):
        header_cols = st.columns([1.35, 0.82, 1.15, 4.0, 0.8, 0.9], gap="small")
        for col, label in zip(
            header_cols,
            [t("table_time"), t("table_input"), t("table_risk"), t("table_fraud"), t("table_score"), t("table_action")],
        ):
            with col:
                st.markdown(f'<div class="wd-history-head-cell">{escape_text(label)}</div>', unsafe_allow_html=True)

        for index, row in rows:
            row_cols = st.columns([1.35, 0.82, 1.15, 4.0, 0.8, 0.9], gap="small")
            cells = [
                escape_text(row.get("时间")),
                escape_text(row.get("输入类型")),
                chip(row.get("风险等级"), risk_tone_from_label(row.get("风险等级"))),
                escape_text(row.get("诈骗类型")),
                escape_text(row.get("风险评分")),
            ]
            for col, cell in zip(row_cols[:5], cells):
                with col:
                    st.markdown(f'<div class="wd-history-cell">{cell}</div>', unsafe_allow_html=True)
            with row_cols[5]:
                st.markdown('<div class="wd-history-action">', unsafe_allow_html=True)
                if st.button(t("view_report"), key=f"history_view_report_{index}", use_container_width=True):
                    if activate_history_report(str(index)):
                        navigate_to("媒体内容识别")
                    st.warning(t("history_report_missing"))
                st.markdown("</div>", unsafe_allow_html=True)


def render_json_debug() -> None:
    result = st.session_state.latest_result
    if not result:
        render_view_header(t("debug_title"), t("debug_subtitle"), None)
        st.markdown(f'<div class="wd-empty">{t("debug_empty")}</div>', unsafe_allow_html=True)
        return
    json_text = json.dumps(result, ensure_ascii=False, indent=2)
    header_left, header_right = st.columns([1, 0.34], gap="large")
    with header_left:
        st.markdown(
            f"""
<div class="wd-action-header" style="border-bottom: 0; padding-bottom: 0;">
  <div>
    <h2><span class="wd-title-with-icon"><span class="wd-title-icon">&lt;&gt;</span><span>{t("debug_title")}</span></span></h2>
    <p>{t("debug_subtitle")}</p>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
    with header_right:
        copy_col, download_col = st.columns([0.43, 0.57], gap="small")
        with copy_col:
            if st.button(t("copy"), use_container_width=True):
                st.toast(t("copy_toast"))
        with download_col:
            st.download_button(
                t("download_report"),
                json_text,
                file_name="anti_fraud_report.json",
                mime="application/json",
                use_container_width=True,
            )
    st.markdown('<div style="border-bottom: 1px solid var(--brand-line); margin: 0.35rem 0 1.75rem;"></div>', unsafe_allow_html=True)
    fields = [
        ("riskLevel", "综合判定的风险等级 (low/medium/high)。"),
        ("riskScore", "大模型与检索融合综合得分 (0-100)。"),
        ("fraudType", "归类的具体网络诈骗类型。"),
        ("riskFeatures", "独立抽取到的关键风险信号数组。"),
        ("evidence", "从知识库检索到的 Top K 证据及多路分数。"),
        ("suggestions", "多层级的立刻处置与后续核实建议。"),
        ("complianceRewrite", "剥离风险后的安全文本。"),
        ("trainingQuestion", "基于当前场景生成的测试题。"),
    ]
    if current_language() == "en":
        fields = [
            ("riskLevel", "Overall risk level (low/medium/high)."),
            ("riskScore", "Combined LLM and retrieval score (0-100)."),
            ("fraudType", "Specific online fraud category."),
            ("riskFeatures", "Independently extracted risk signals."),
            ("evidence", "Top K evidence retrieved from the knowledge base and multi-route scores."),
            ("suggestions", "Immediate, verification, and follow-up recommendations."),
            ("complianceRewrite", "Safe text after removing risky parts."),
            ("trainingQuestion", "Quiz question generated from the current scenario."),
        ]
    field_html = "".join(
        f'<div class="wd-field"><code>{escape_text(name)}</code><div>{escape_text(desc)}</div></div>'
        for name, desc in fields
    )
    left, right = st.columns([1, 0.42], gap="large")
    with left:
        st.markdown(
            f"""
<div class="wd-code-panel">
  <div class="wd-code-head"><span>response.json</span><span>UTF-8</span></div>
  <pre class="wd-code-body">{escape_text(json_text)}</pre>
</div>
""",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(f'<div class="wd-card"><h3>{t("field_notes")}</h3>{field_html}</div>', unsafe_allow_html=True)


def main() -> None:
    inject_design_system()
    init_session_state()
    if st.session_state.get("pending_page"):
        st.session_state.nav_page = st.session_state.pending_page
        st.session_state.page = st.session_state.pending_page
        del st.session_state.pending_page

    with st.sidebar:
        render_sidebar_brand()
        language_codes = list(LANGUAGE_OPTIONS.keys())
        active_language = current_language()
        if "language_picker" not in st.session_state:
            st.session_state.language_picker = active_language
        language_choice = st.radio(
            t("language"),
            language_codes,
            format_func=lambda code: LANGUAGE_OPTIONS[code],
            key="language_picker",
            horizontal=True,
        )
        if language_choice != active_language:
            st.session_state.pending_language = language_choice
            st.rerun()
        if st.session_state.nav_page not in NAV_ITEMS:
            st.session_state.nav_page = "首页概览"
        page = st.radio(
            "页面导航",
            NAV_ITEMS,
            key="nav_page",
            label_visibility="collapsed",
            format_func=nav_label,
        )
        st.session_state.page = page
        st.divider()
        st.markdown(f'<div class="wd-section-label">{t("settings")}</div>', unsafe_allow_html=True)
        qwen_key = st.text_input("Qwen API key", type="password")
        mock = st.toggle(t("mock_mode"), value=False, help=t("mock_help"))
        top_k = st.slider(t("retrieved_evidence"), 3, 10, 6)
        example_name = st.selectbox(t("example"), list(EXAMPLES.keys()), format_func=example_label)
        use_example = st.button(t("use_example"), use_container_width=True)
        st.markdown(f'<div class="wd-side-status"><span class="wd-dot"></span><span>{t("model_online")}</span></div>', unsafe_allow_html=True)

    if page == "首页概览":
        render_home()
    elif page == "媒体内容识别":
        render_recognition(qwen_key, mock, top_k, example_name, use_example)
    elif page == "证据链分析":
        render_evidence_page()
    elif page == "反诈训练中心":
        render_training_center()
    elif page == "历史记录":
        render_history_page()
    else:
        render_json_debug()


if __name__ == "__main__":
    main()
