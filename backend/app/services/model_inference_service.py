from __future__ import annotations

import ipaddress
import contextlib
import io
import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import numpy as np

from app.core.config import settings


URL_PATTERN = re.compile(
    r"(https?://[^\s，。；;]+|www\.[^\s，。；;]+|[a-zA-Z0-9-]+\.(?:com|cn|net|top|xyz|vip|shop|cc)[^\s，。；;]*)"
)

SHORTENER_DOMAINS = {
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "goo.gl",
    "ow.ly",
    "is.gd",
    "buff.ly",
    "cutt.ly",
    "rebrand.ly",
    "suo.im",
    "dwz.cn",
}

SUSPICIOUS_URL_WORDS = {
    "login",
    "verify",
    "account",
    "secure",
    "update",
    "password",
    "reset",
    "bank",
    "wallet",
    "pay",
    "bonus",
    "free",
    "refund",
    "claim",
    "gift",
    "客服",
    "退款",
    "验证",
    "账户",
}

URL_FEATURE_NAMES = [
    "url_length",
    "hostname_length",
    "count_letters",
    "count_digits",
    "count_@",
    "count_?",
    "count_-",
    "count_=",
    "count_.",
    "count_#",
    "count_%",
    "count_+",
    "count_$",
    "count_!",
    "count_*",
    "count_,",
    "count_slashes",
    "count_www",
    "has_ip",
    "abnormal_url",
    "short_url",
    "https",
    "count_dir",
    "count_embed_domain",
    "fd_length",
    "tld_length",
    "suspicious",
]

MACBERT_PROTOTYPES = [
    ("刷单返利", "点赞关注 兼职刷单 先垫付 连单 卡单 组合单 返利 佣金 提现失败 高佣任务组 高收益 小额返利 任务群"),
    ("冒充客服", "平台客服 订单异常 退款理赔 屏幕共享 验证码 账户冻结 注销贷款账户"),
    ("虚假兼职", "线上兼职 校园推广员 远程办公 入职前交资料费 培训费 保证金 押金 高薪日结 无需经验 名额有限"),
    ("校园贷/注销校园贷", "校园贷 注销校园贷 影响征信 清空额度 安全账户 转账认证 低息贷款 无抵押 刷流水 征信修复"),
    ("冒充公检法", "公安 检察院 法院 涉嫌洗钱 案件相关人员 资金核查 安全账户 保密调查 远程调查 通缉令 法律责任"),
    ("虚假购物/二手交易", "低价转让 内部渠道 二手交易 演唱会门票 先付定金 私下转账 不走平台 急出 先付邮费"),
    ("网络游戏交易诈骗", "游戏账号 装备 点券 皮肤 私下改绑 先付款 解冻金 保证金 代练全款 担保平台 资金冻结"),
    ("虚假中奖/福利领取", "中奖 免费领取 限时领奖 支付邮费 实名认证 现金红包 点击链接 领奖信息 逾期自动放弃"),
    ("恋爱交友/杀猪盘", "网恋 不方便公开视频 投资平台 内部渠道 老师带着操作 充值 行情很好 错过机会 收益稳定"),
    ("虚假投资理财", "稳赚不赔 内部消息 内部数据 老师带单 高收益 翻倍 提现缴税 通道费 收益到账 本金安全"),
    ("冒充熟人/AI换脸", "老师同学学长换号 不方便打电话 开会不方便 急用钱 借钱转账 代缴报名费 帮忙转账 不方便视频"),
    ("链接安全", "短信链接 账号异常 输入学号 密码 验证码 钓鱼页面 陌生链接"),
]


def _url_with_scheme(url: str) -> str:
    return url if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url) else f"http://{url}"


def _is_ip(hostname: str) -> int:
    try:
        ipaddress.ip_address(hostname)
        return 1
    except ValueError:
        return 0


def _safe_tld(hostname: str) -> str:
    parts = [part for part in hostname.split(".") if part]
    return parts[-1] if len(parts) >= 2 else ""


def extract_url_feature_dict(url: str) -> dict[str, int]:
    try:
        parsed = urlparse(_url_with_scheme(url))
    except ValueError:
        parsed = urlparse("http://")
    hostname = parsed.hostname or ""
    path_parts = [part for part in parsed.path.split("/") if part]
    first_dir = path_parts[0] if path_parts else ""
    tld = _safe_tld(hostname)
    lower = url.lower()
    features = {
        "url_length": len(url),
        "hostname_length": len(hostname),
        "count_letters": sum(char.isalpha() for char in url),
        "count_digits": sum(char.isdigit() for char in url),
        "count_@": url.count("@"),
        "count_?": url.count("?"),
        "count_-": url.count("-"),
        "count_=": url.count("="),
        "count_.": url.count("."),
        "count_#": url.count("#"),
        "count_%": url.count("%"),
        "count_+": url.count("+"),
        "count_$": url.count("$"),
        "count_!": url.count("!"),
        "count_*": url.count("*"),
        "count_,": url.count(","),
        "count_slashes": url.count("/"),
        "count_www": lower.count("www"),
        "has_ip": _is_ip(hostname),
        "abnormal_url": 1 if "@" in parsed.netloc or "//" in parsed.path else 0,
        "short_url": 1 if hostname.lower() in SHORTENER_DOMAINS else 0,
        "https": 1 if parsed.scheme.lower() == "https" else 0,
        "count_dir": len(path_parts),
        "count_embed_domain": max(0, hostname.count(".") - 1) + max(0, url.count("//") - 1),
        "fd_length": len(first_dir),
        "tld_length": len(tld),
        "suspicious": sum(1 for word in SUSPICIOUS_URL_WORDS if word in lower),
    }
    return features


def _extract_url_features(url: str, feature_names: list[str]) -> Any:
    features = extract_url_feature_dict(url)
    row = {name: features.get(name, 0) for name in feature_names}
    try:
        import pandas as pd

        return pd.DataFrame([row], columns=feature_names)
    except Exception:
        return np.asarray([[row[name] for name in feature_names]], dtype="float32")


@lru_cache(maxsize=1)
def _url_classifier() -> dict[str, Any]:
    if not settings.url_classifier_enabled:
        return {"available": False, "error": "disabled by ANTI_FRAUD_URL_CLASSIFIER=0"}

    model_dir = settings.url_classifier_model_path
    model_path = model_dir / settings.url_classifier_model_name
    scaler_path = model_dir / settings.url_classifier_scaler_name
    encoder_path = model_dir / settings.url_classifier_label_encoder_name
    if not model_path.exists():
        model_path = model_dir / "decision_tree.pkl"
    if not scaler_path.exists():
        scaler_path = model_dir / "scaler.pkl"
    if not encoder_path.exists():
        encoder_path = model_dir / "label_encoder.pkl"
    if not model_path.exists() or not scaler_path.exists() or not encoder_path.exists():
        return {"available": False, "error": f"url classifier files not found: {model_dir}"}

    try:
        import joblib

        scaler = joblib.load(scaler_path)
        model = joblib.load(model_path)
        encoder = joblib.load(encoder_path)
        feature_names = list(getattr(scaler, "feature_names_in_", []))
        if not feature_names:
            feature_names = URL_FEATURE_NAMES
        return {
            "available": True,
            "model": model,
            "scaler": scaler,
            "encoder": encoder,
            "feature_names": feature_names,
            "model_path": str(model_path),
            "scaler_path": str(scaler_path),
            "encoder_path": str(encoder_path),
            "error": "",
        }
    except Exception as exc:
        return {"available": False, "error": f"url classifier unavailable: {exc}"}


def classify_urls(text: str) -> list[dict[str, Any]]:
    backend = _url_classifier()
    matches = list(URL_PATTERN.finditer(text))
    if not matches:
        return []

    results: list[dict[str, Any]] = []
    if not backend.get("available"):
        for match in matches:
            results.append(
                {
                    "url": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                    "label": "unknown",
                    "confidence": 0,
                    "status": "unavailable",
                    "detail": backend.get("error", ""),
                }
            )
        return results

    model = backend["model"]
    scaler = backend["scaler"]
    encoder = backend["encoder"]
    feature_names = backend["feature_names"]
    for match in matches:
        url = match.group(0)
        features = _extract_url_features(url, feature_names)
        scaled = scaler.transform(features)
        pred = model.predict(scaled)[0]
        label = str(encoder.inverse_transform([pred])[0])
        confidence = 0
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(scaled)[0]
            confidence = int(round(float(np.max(proba)) * 100))
        results.append(
            {
                "url": url,
                "start": match.start(),
                "end": match.end(),
                "label": label,
                "confidence": confidence,
                "status": "ok",
                "detail": f"URL model classified as {label}",
            }
        )
    return results


@lru_cache(maxsize=1)
def _macbert_fraud_backend() -> dict[str, Any]:
    if not settings.macbert_fraud_classifier_enabled:
        return {"available": False, "error": "disabled by ANTI_FRAUD_MACBERT_FRAUD_CLASSIFIER=0"}
    model_dir = settings.macbert_fraud_model_path
    if not model_dir.exists():
        return {"available": False, "error": "fine-tuned MacBERT fraud model not found"}
    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(model_dir, local_files_only=True)
        model.eval()
        return {
            "available": True,
            "tokenizer": tokenizer,
            "model": model,
            "torch": torch,
            "error": "",
        }
    except Exception as exc:
        return {"available": False, "error": f"fine-tuned MacBERT unavailable: {exc}"}


def classify_fraud_text(text: str) -> dict[str, Any]:
    backend = _macbert_fraud_backend()
    if not text.strip():
        return {"status": "skipped", "label": "", "score": 0, "detail": "empty text"}
    if not backend.get("available"):
        return {"status": "unavailable", "label": "", "score": 0, "detail": backend.get("error", "")}

    tokenizer = backend["tokenizer"]
    model = backend["model"]
    torch = backend["torch"]
    try:
        inputs = tokenizer(text[:1000], return_tensors="pt", truncation=True, max_length=256)
        device = next(model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.no_grad():
            logits = model(**inputs).logits
            probs = torch.softmax(logits, dim=-1)[0]
        pred_id = int(torch.argmax(probs).item())
        id2label = getattr(model.config, "id2label", {}) or {0: "normal", 1: "fraud"}
        label = str(id2label.get(pred_id, pred_id)).lower()
        score = int(round(float(probs[pred_id].item()) * 100))
        return {
            "status": "ok",
            "label": label,
            "score": score,
            "detail": f"fine-tuned MacBERT classified as {label}",
        }
    except Exception as exc:
        return {"status": "error", "label": "", "score": 0, "detail": f"fine-tuned MacBERT failed: {exc}"}


@lru_cache(maxsize=1)
def _macbert_backend() -> dict[str, Any]:
    if not settings.macbert_enabled:
        return {"available": False, "error": "disabled by ANTI_FRAUD_MACBERT_ENABLED=0"}
    model_path = settings.macbert_model_path
    if not model_path.exists():
        return {"available": False, "error": f"MacBERT model not found: {model_path}"}

    try:
        import torch
        from transformers import AutoModel, AutoTokenizer

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
            model = AutoModel.from_pretrained(str(model_path), local_files_only=True)
        model.eval()
        return {
            "available": True,
            "tokenizer": tokenizer,
            "model": model,
            "torch": torch,
            "model_path": str(model_path),
            "error": "",
        }
    except Exception as exc:
        return {"available": False, "error": f"MacBERT unavailable: {exc}"}


def _macbert_encode(texts: list[str]) -> np.ndarray | None:
    backend = _macbert_backend()
    if not backend.get("available"):
        return None
    tokenizer = backend["tokenizer"]
    model = backend["model"]
    torch = backend["torch"]
    inputs = tokenizer(texts, padding=True, truncation=True, max_length=192, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
        hidden = outputs.last_hidden_state
        mask = inputs["attention_mask"].unsqueeze(-1).float()
        pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
        pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
    return pooled.cpu().numpy().astype("float32")


@lru_cache(maxsize=1)
def _prototype_embeddings() -> np.ndarray | None:
    return _macbert_encode([text for _, text in MACBERT_PROTOTYPES])


def semantic_match_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if len(stripped) < 8:
        return {"status": "skipped", "detail": "text too short"}

    backend = _macbert_backend()
    if not backend.get("available"):
        return {"status": "unavailable", "detail": backend.get("error", "")}

    query = _macbert_encode([stripped])
    prototypes = _prototype_embeddings()
    if query is None or prototypes is None:
        return {"status": "unavailable", "detail": "MacBERT embedding failed"}

    scores = np.dot(prototypes, query[0])
    order = np.argsort(-scores)
    best = int(order[0])
    second = int(order[1]) if len(order) > 1 else best
    best_score = float(scores[best])
    margin = float(scores[best] - scores[second]) if second != best else 0.0
    return {
        "status": "ok",
        "label": MACBERT_PROTOTYPES[best][0],
        "score": round(best_score, 4),
        "margin": round(margin, 4),
        "top_matches": [
            {"label": MACBERT_PROTOTYPES[int(index)][0], "score": round(float(scores[int(index)]), 4)}
            for index in order[:3]
        ],
        "detail": "MacBERT semantic prototype similarity",
    }


@lru_cache(maxsize=1)
def _qwen_backend() -> dict[str, Any]:
    if not settings.qwen_enabled:
        return {"available": False, "error": "disabled by ANTI_FRAUD_QWEN_ENABLED=0"}
    model_path = settings.qwen_model_path
    if not model_path.exists():
        return {"available": False, "error": f"Qwen model not found: {model_path}"}

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(
                str(model_path),
                local_files_only=True,
                trust_remote_code=True,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
            )
        model.eval()
        return {
            "available": True,
            "tokenizer": tokenizer,
            "model": model,
            "torch": torch,
            "model_path": str(model_path),
            "error": "",
        }
    except Exception as exc:
        return {"available": False, "error": f"Qwen unavailable: {exc}"}


def generate_qwen_advice(text: str, analysis: dict[str, Any]) -> dict[str, Any]:
    backend = _qwen_backend()
    if not backend.get("available"):
        return {"status": "unavailable", "detail": backend.get("error", "")}

    tokenizer = backend["tokenizer"]
    model = backend["model"]
    torch = backend["torch"]
    prompt = (
        "你是高校反诈教育助手。请基于系统已识别的风险信号，生成一段不超过120字的中文建议，"
        "要求强调风险点、核验方式和证据保存，不要作法律定性。\n"
        f"可疑内容：{text[:800]}\n"
        f"风险等级：{analysis.get('risk_level')}，疑似类型：{analysis.get('scam_type')}，"
        f"风险信号：{'、'.join(analysis.get('evidence', [])[:6])}\n"
        "建议："
    )
    try:
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1400)
        device = next(model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.no_grad():
            output = model.generate(
                **inputs,
                max_new_tokens=settings.qwen_max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        generated = tokenizer.decode(output[0][inputs["input_ids"].shape[-1] :], skip_special_tokens=True)
        return {"status": "ok", "text": generated.strip(), "detail": "Qwen local generation"}
    except Exception as exc:
        return {"status": "error", "detail": f"Qwen generation failed: {exc}"}


def preload_qwen_model() -> dict[str, Any]:
    backend = _qwen_backend()
    if backend.get("available"):
        return {
            "status": "ok",
            "loaded": True,
            "model": backend.get("model_path", str(settings.qwen_model_path)),
            "detail": "Qwen model preloaded",
        }
    return {
        "status": "unavailable",
        "loaded": False,
        "model": str(settings.qwen_model_path),
        "detail": backend.get("error", ""),
    }


def get_model_inference_status() -> dict[str, Any]:
    url_backend = _url_classifier()
    macbert_loaded = settings.macbert_enabled and _macbert_backend.cache_info().currsize > 0
    qwen_loaded = settings.qwen_enabled and _qwen_backend.cache_info().currsize > 0
    return {
        "url_classifier": {
            "enabled": settings.url_classifier_enabled,
            "available": bool(url_backend.get("available")),
            "model": url_backend.get(
                "model_path",
                str(settings.url_classifier_model_path / settings.url_classifier_model_name),
            ),
            "scaler": url_backend.get(
                "scaler_path",
                str(settings.url_classifier_model_path / settings.url_classifier_scaler_name),
            ),
            "error": url_backend.get("error", ""),
        },
        "macbert_fraud_classifier": {
            "enabled": settings.macbert_fraud_classifier_enabled,
            "available": settings.macbert_fraud_model_path.exists(),
            "model": str(settings.macbert_fraud_model_path),
            "loaded": _macbert_fraud_backend.cache_info().currsize > 0,
            "error": "" if settings.macbert_fraud_model_path.exists() else "fine-tuned model directory not found",
        },
        "macbert": {
            "enabled": settings.macbert_enabled,
            "available": settings.macbert_model_path.exists(),
            "model": str(settings.macbert_model_path),
            "loaded": macbert_loaded,
            "error": "" if settings.macbert_model_path.exists() else "model directory not found",
        },
        "qwen": {
            "enabled": settings.qwen_enabled,
            "preload_enabled": settings.qwen_preload,
            "available": settings.qwen_model_path.exists(),
            "model": str(settings.qwen_model_path),
            "loaded": qwen_loaded,
            "error": (
                _qwen_backend().get("error", "")
                if qwen_loaded
                else "" if settings.qwen_model_path.exists() else "model directory not found"
            ),
        },
        "phishing_url_bert_reference": {
            "available": settings.phishing_url_bert_model_path.exists(),
            "model": str(settings.phishing_url_bert_model_path),
            "note": "reference model; main URL flow uses the local 27-feature classifier by default",
        },
    }
