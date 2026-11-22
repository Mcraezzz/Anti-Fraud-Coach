from __future__ import annotations

import json
import re
from typing import Any

from app.core.config import DATA_DIR, settings
from app.services.model_inference_service import (
    classify_fraud_text,
    classify_urls,
    generate_qwen_advice,
    semantic_match_text,
)


RULE_FILE = DATA_DIR / "risk_rules.json"
URL_RE = re.compile(r"(https?://[^\s，。；;]+|www\.[^\s，。；;]+|[a-zA-Z0-9-]+\.(?:com|cn|net|top|xyz|vip|shop|cc)[^\s，。；;]*)")
AMOUNT_RE = re.compile(r"(?:￥|¥)?\d+(?:\.\d+)?\s*(?:元|块|rmb|RMB)")
MAX_SUGGESTIONS = 12


URL_MODEL_LABELS = {
    "phishing": {
        "label": "URL模型判定：钓鱼链接",
        "weight": 20,
        "explanation": "本地 URL 分类模型根据域名、路径、特殊字符和可疑词等 27 项特征，将该链接判为 phishing。",
        "suggestion": "不要点击或输入账号、密码、验证码，应通过官方 App、官网或学校渠道重新打开服务。",
    },
    "malware": {
        "label": "URL模型判定：恶意软件链接",
        "weight": 22,
        "explanation": "本地 URL 分类模型将该链接判为 malware，可能诱导下载恶意程序或远程控制工具。",
        "suggestion": "不要下载陌生链接中的安装包，不授予远程控制或屏幕共享权限。",
    },
    "defacement": {
        "label": "URL模型判定：篡改/仿冒页面",
        "weight": 16,
        "explanation": "本地 URL 分类模型将该链接判为 defacement，可能是仿冒或被篡改页面。",
        "suggestion": "不要在该页面提交个人信息，应回到可信官方入口核验。",
    },
}


SCAM_TYPE_ACTIONS = {
    "rebate_task": [
        "立即停止刷单、点赞关注、组合单等任务，不再充值或垫付。",
        "不要相信“做完立返”“连续完成后统一结算”“系统卡单”等解释。",
        "不要继续联系所谓派单员、导师或任务群管理员。",
        "保存群聊记录、任务页面、付款截图、收款账户和对方账号信息。",
        "如已转账，马上联系支付平台或银行申请止付、冻结或交易争议处理。",
        "把可疑群聊和账号举报给平台，并提醒同学不要加入同类任务群。",
        "向辅导员、学校保卫处或反诈中心说明情况，必要时拨打 110。",
        "不要为了提现继续完成追加任务，追加投入通常会扩大损失。",
        "后续兼职优先通过学校就业平台、正规招聘平台和企业官方渠道核验。",
    ],
    "fake_part_time": [
        "不要缴纳资料费、培训费、押金、保证金、入职费等入职前费用。",
        "要求先交钱、扫码填身份信息或私下收款的兼职先暂停处理。",
        "核验招聘主体营业执照、官方联系方式、岗位来源和学校就业平台记录。",
        "不要提交身份证、银行卡、验证码、人脸识别等敏感信息。",
        "保存招聘聊天记录、岗位截图、收款码、合同或报名表页面。",
        "向学校就业指导中心、辅导员或学院老师核实岗位真实性。",
        "不要因“名额有限”“今天截止”仓促付款或签署不明协议。",
        "已付款的，立即联系支付平台申请止付并保留凭证。",
        "将可疑招聘链接、群聊或账号举报给对应平台。",
    ],
    "campus_loan": [
        "不要按陌生客服要求注销校园贷、清空额度或转账认证。",
        "不要把贷款额度借出后转入所谓安全账户或指定账户。",
        "通过正规金融机构官方 App、官网客服电话或学校资助部门核实。",
        "不要提供身份证、银行卡、验证码、人脸识别、登录码等信息。",
        "不要相信“影响征信”“监管要求”“额度异常”的电话或私信施压。",
        "保存对方号码、聊天记录、链接、转账账户和贷款平台页面。",
        "如已借款或转账，立即联系银行、贷款平台和支付渠道申请止付。",
        "向辅导员、学校资助中心或保卫处报告，必要时报警。",
        "后续贷款、助学资金问题优先走学校和正规金融机构渠道。",
    ],
    "fake_customer_service": [
        "不要点击陌生退款、理赔、赔偿、取消扣费链接。",
        "不要填写银行卡、验证码、密码、身份证号或开启屏幕共享。",
        "不要下载陌生会议软件、远程控制软件或按对方指引操作账户。",
        "通过购物平台官方 App、订单页面或官方客服电话核实。",
        "快递丢失、商品质量、会员扣费等问题只在官方平台内处理。",
        "保存短信、聊天记录、链接、来电号码、对方账号和付款凭证。",
        "如已输入银行卡或验证码，立即联系银行冻结账户或修改密码。",
        "向平台举报冒充客服账号，并同步提醒同学警惕同类话术。",
        "已造成资金损失时，第一时间报警并提交证据材料。",
    ],
    "acquaintance_impersonation": [
        "涉及借钱、转账、代缴、资料费或验证码时，先电话或视频核实本人身份。",
        "对方称不方便通话、手机坏了、换号了、正在开会时更要暂停操作。",
        "不要仅凭头像、昵称、语气或短视频判断对方身份。",
        "通过原手机号、共同好友、班级群、辅导员或线下方式二次确认。",
        "不要向陌生账户转账，不替他人垫付报名费、资料费或项目费。",
        "不要发送身份证号、银行卡号、验证码、支付密码等信息。",
        "保存聊天记录、收款账户、转账要求和对方账号变更信息。",
        "确认被冒充后提醒班级群、社团群或共同联系人。",
        "如已转账，立即联系银行或支付平台止付并报警。",
    ],
    "fake_authority": [
        "立即停止通话或聊天，不继续配合所谓案件核查。",
        "不要向安全账户、核查账户或指定账户转账。",
        "不要下载指定软件、开启远程会议、屏幕共享或关闭定位录屏提醒。",
        "公检法不会通过电话要求转账、保密调查或远程办案。",
        "通过 110、当地派出所或官方政务渠道核实案件信息。",
        "不要透露银行卡、验证码、身份证、人脸识别、账户余额等信息。",
        "保存来电号码、聊天记录、所谓文书、通缉令、转账账户等证据。",
        "向家人、辅导员或学校保卫处说明，避免被“保密”话术隔离。",
        "如已转账，立刻申请止付并报警。",
    ],
    "fake_shopping_trade": [
        "不要脱离平台私下转账、先付定金、邮费或全款。",
        "低价转让、内部渠道、急出、走平台太慢等话术先暂停。",
        "使用正规平台担保交易，确认商品、票务和物流信息真实。",
        "不要相信付款后发电子票、收到不满意可退等口头承诺。",
        "核验卖家历史记录、实名认证、评价和平台保障规则。",
        "保存商品页面、聊天记录、收款账户、转账凭证和物流信息。",
        "演唱会门票等高风险商品应通过官方票务渠道购买。",
        "已付款未发货时，立即申请平台介入或支付渠道争议处理。",
        "将虚假账号、链接和收款码举报给平台。",
    ],
    "game_trade": [
        "不要私下购买或出售游戏账号、装备、点券、皮肤等虚拟物品。",
        "不要先付款后改绑，不缴纳解冻金、保证金或认证费。",
        "游戏交易、代练和账号转让优先走官方平台或平台担保流程。",
        "不要相信低价皮肤、满级账号、失败全额退款等承诺。",
        "不要把账号密码、验证码、密保、人脸信息提供给陌生人。",
        "保存聊天记录、游戏 ID、交易页面、收款账户和转账凭证。",
        "账号异常时通过游戏官方客服处理，不按陌生人指引操作。",
        "已付款或账号被盗时，立即联系游戏平台和支付渠道冻结处理。",
        "向平台举报可疑担保平台、代练账号和交易群。",
    ],
    "fake_prize": [
        "不要点击陌生领奖链接或填写领奖信息、实名认证信息。",
        "不要为中奖、免费领取、福利红包支付邮费、税费或手续费。",
        "通过活动主办方官网、学校官方通知或平台官方入口核实。",
        "不要相信 30 分钟领奖、逾期作废等催促话术。",
        "不要提交身份证、银行卡、验证码、手机号登录码等敏感信息。",
        "保存中奖通知、链接、发件号码、聊天记录和要求付款信息。",
        "将虚假福利短信、链接和账号举报给平台或运营商。",
        "已付款或提交银行卡信息后，立即联系银行、支付平台处理。",
        "提醒同学不要转发不明领奖链接或现金红包活动。",
    ],
    "romance_investment": [
        "网络交友后出现投资、赌博、充值、带单时立即暂停。",
        "不要向陌生投资平台、内部渠道或对方推荐账户充值。",
        "不要相信稳定收益、老师带着操作、错过机会等话术。",
        "对方不愿视频、长期回避线下核实或要求保密时提高警惕。",
        "核验平台是否具备正规金融资质，不使用陌生链接开户。",
        "不要为了提现继续缴纳保证金、税费、通道费或解冻费。",
        "保存聊天记录、平台页面、充值记录、收款账户和对方身份信息。",
        "向家人、辅导员或反诈中心求助，避免被情感话术持续诱导。",
        "已充值的，立即联系支付渠道止付并报警。",
    ],
    "fake_investment": [
        "不要相信稳赚不赔、内部消息、内部数据、老师带单等承诺。",
        "不要向陌生理财平台充值或把资金交给他人代操作。",
        "提现前要求缴税、通道费、保证金、解冻费时立即停止。",
        "核验平台金融牌照、官方网站、监管信息和资金托管情况。",
        "不要因为限时名额、三天翻倍、短期高收益而仓促投资。",
        "保存投资群聊、导师账号、平台页面、充值记录和提现失败截图。",
        "向正规金融机构、学校老师或反诈中心咨询风险。",
        "已投入资金的，尽快联系银行、支付平台申请止付并报警。",
        "不要继续追加资金试图解冻或提现。",
    ],
    "phishing_url": [
        "不要点击陌生链接，不在陌生页面输入账号、密码、验证码。",
        "不要下载链接中的安装包、会议软件或所谓安全插件。",
        "通过官方 App、官网、学校通知或客服电话重新进入服务。",
        "检查域名拼写、HTTPS 状态、页面备案和官方入口是否一致。",
        "涉及银行卡、实名、退款、领奖、账户冻结的链接一律先核实。",
        "保存短信、链接、页面截图、发件号码和跳转地址。",
        "已输入账号密码的，立即修改密码并开启二次验证。",
        "已输入银行卡或验证码的，立即联系银行冻结账户。",
        "向平台、运营商或国家反诈中心举报钓鱼链接。",
    ],
}


def _load_rules() -> dict[str, Any]:
    return json.loads(RULE_FILE.read_text(encoding="utf-8"))


def _find_keyword_spans(text: str, keyword: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    while True:
        idx = text.find(keyword, start)
        if idx == -1:
            break
        spans.append((idx, idx + len(keyword)))
        start = idx + max(len(keyword), 1)
    return spans


def _make_signal(
    signal_id: str,
    label: str,
    keyword: str,
    start: int,
    end: int,
    weight: int,
    explanation: str,
    suggestion: str,
) -> dict[str, Any]:
    return {
        "signal_id": signal_id,
        "label": label,
        "keyword": keyword,
        "start": start,
        "end": end,
        "weight": weight,
        "explanation": explanation,
        "suggestion": suggestion,
    }


def _has_signal(signals: list[dict[str, Any]], *signal_ids: str) -> bool:
    existing = {signal["signal_id"] for signal in signals}
    return any(signal_id in existing for signal_id in signal_ids)


def _add_composite_signals(signals: list[dict[str, Any]]) -> None:
    existing = {signal["signal_id"] for signal in signals}

    def add_composite(
        signal_id: str,
        label: str,
        keyword: str,
        weight: int,
        explanation: str,
        suggestion: str,
    ) -> None:
        if signal_id in existing:
            return
        signals.append(_make_signal(signal_id, label, keyword, -1, -1, weight, explanation, suggestion))
        existing.add(signal_id)

    if (
        "fake_service_flow" not in existing
        and _has_signal(signals, "identity_impersonation", "account_anomaly")
        and _has_signal(signals, "privacy_request", "off_platform", "remote_control")
    ):
        add_composite(
            "fake_service_flow",
            "冒充客服组合话术",
            "客服身份+异常/退款+隐私索取/脱离平台",
            22,
            "身份伪装、退款理赔或账户异常与隐私索取、脱离平台、远程会议同时出现，符合冒充客服类诈骗链路。",
            "立刻停止沟通，通过官方 App 或客服电话核实，不要提供验证码、银行卡或开启屏幕共享。",
        )

    if (
        "rebate_task_flow" not in existing
        and _has_signal(signals, "high_return", "rebate_task_lure")
        and _has_signal(signals, "money_inducement", "amount", "rebate_task_lure")
        and _has_signal(signals, "off_platform", "urgency_pressure", "rebate_task_lure")
    ):
        add_composite(
            "rebate_task_flow",
            "刷单返利组合话术",
            "任务返利+充值/提现/连单",
            18,
            "任务返利、点赞关注、组合单、充值垫付、无法提现等要素叠加，是刷单返利骗局的典型流程。",
            "不要继续做任务、充值或垫付，保存群聊、任务单和转账记录。",
        )

    if (
        "loan_trap_flow" not in existing
        and _has_signal(signals, "loan_trap")
        and _has_signal(signals, "money_inducement", "privacy_request", "account_anomaly")
    ):
        add_composite(
            "loan_trap_flow",
            "贷款陷阱组合话术",
            "贷款/征信+收费/隐私索取",
            16,
            "贷款、征信、注销校园贷话术中叠加收费、刷流水、清空额度或索要身份信息，可能涉及校园贷、套路贷或注销校园贷骗局。",
            "不要提交身份证、银行卡或支付费用，优先咨询学校资助部门或正规金融机构。",
        )

    if (
        "safe_account_flow" not in existing
        and _has_signal(signals, "account_anomaly", "authority_threat", "loan_trap")
        and _has_signal(signals, "money_inducement")
    ):
        add_composite(
            "safe_account_flow",
            "安全账户/转账认证组合话术",
            "异常/核查+安全账户/转账认证",
            18,
            "以账户异常、资金核查、注销贷款或安全账户为由要求转账，属于高危资金转移话术。",
            "不要向所谓安全账户转账，遇到资金核查应通过官方渠道或 110 核实。",
        )

    if (
        "fake_job_fee_flow" not in existing
        and _has_signal(signals, "recruitment_lure")
        and _has_signal(signals, "money_inducement", "privacy_request")
    ):
        add_composite(
            "fake_job_fee_flow",
            "虚假兼职收费组合话术",
            "招聘兼职+先收费/身份信息",
            18,
            "线上兼职、校园推广、远程办公等招聘话术叠加入职前收费或身份信息填写，符合虚假兼职招聘套路。",
            "不要缴纳资料费、押金、培训费或保证金，应通过学校就业平台核实岗位。",
        )

    if (
        "authority_safe_account_flow" not in existing
        and _has_signal(signals, "authority_threat")
        and _has_signal(signals, "money_inducement", "privacy_request", "remote_control", "secrecy")
    ):
        add_composite(
            "authority_safe_account_flow",
            "冒充公检法组合话术",
            "涉嫌案件+保密/资金核查/远程调查",
            22,
            "涉嫌犯罪、资金核查、保密调查、安全账户或远程调查同时出现，符合冒充公检法高危诈骗链路。",
            "公检法不会电话办案要求转账或远程调查，应立即挂断并拨打 110 核实。",
        )

    if (
        "private_trade_flow" not in existing
        and _has_signal(signals, "private_trade_lure")
        and _has_signal(signals, "money_inducement", "off_platform", "urgency_pressure")
    ):
        add_composite(
            "private_trade_flow",
            "私下交易组合话术",
            "低价/内部渠道+先付款/不走平台",
            18,
            "低价转让、内部渠道、先付定金和不走平台叠加出现，符合虚假购物或二手交易诈骗链路。",
            "坚持平台担保交易，不私下转账，不先付定金或邮费。",
        )

    if (
        "game_trade_flow" not in existing
        and _has_signal(signals, "game_trade_lure")
        and _has_signal(signals, "money_inducement", "off_platform", "private_trade_lure")
    ):
        add_composite(
            "game_trade_flow",
            "游戏交易组合话术",
            "账号/代练+先付款/解冻金/私下改绑",
            18,
            "游戏账号、装备、皮肤或代练交易中叠加先付款、解冻金、私下改绑，容易导致资金或账号损失。",
            "游戏交易应走官方平台，不先付款、不缴解冻金、不私下改绑。",
        )

    if (
        "prize_fee_flow" not in existing
        and _has_signal(signals, "prize_lure")
        and _has_signal(signals, "money_inducement", "privacy_request", "off_platform", "urgency_pressure")
    ):
        add_composite(
            "prize_fee_flow",
            "中奖福利组合话术",
            "中奖/福利+邮费/实名/链接",
            16,
            "中奖、免费福利或现金红包叠加支付邮费、实名认证、限时领奖或陌生链接，属于虚假中奖福利常见套路。",
            "不要支付邮费或点击领奖链接，领奖信息应通过官方活动渠道核实。",
        )

    if (
        "romance_investment_flow" not in existing
        and _has_signal(signals, "investment_lure")
        and _has_signal(signals, "high_return", "money_inducement", "secrecy", "urgency_pressure")
    ):
        add_composite(
            "romance_investment_flow",
            "交友投资组合话术",
            "交友信任+投资充值/内部渠道",
            18,
            "网络交友后诱导投资、充值、老师带单或内部渠道，符合杀猪盘常见链路。",
            "不要向陌生投资平台开户或充值，涉及交友投资应立即停止并保存证据。",
        )

    if (
        "investment_fee_flow" not in existing
        and _has_signal(signals, "investment_lure", "high_return")
        and _has_signal(signals, "money_inducement", "urgency_pressure", "secrecy")
    ):
        add_composite(
            "investment_fee_flow",
            "虚假投资理财组合话术",
            "高收益/带单+提现缴费",
            18,
            "稳赚不赔、内部消息、老师带单和提现前缴税或通道费叠加，是虚假投资理财高危信号。",
            "不要相信稳赚不赔或提现前缴费，应通过正规金融机构核验。",
        )

    if (
        "acquaintance_money_flow" not in existing
        and _has_signal(signals, "identity_impersonation", "acquaintance_urgency")
        and _has_signal(signals, "money_inducement", "privacy_request", "urgency_pressure")
    ):
        add_composite(
            "acquaintance_money_flow",
            "冒充熟人借款组合话术",
            "熟人身份+急事借款/代缴",
            18,
            "熟人、老师、学长或同学身份叠加不便通话、换号、急事借款或代缴费用，可能涉及冒充熟人或 AI 换脸/换声诈骗。",
            "涉及转账或代缴必须电话、视频或线下核实本人身份。",
        )


def _risk_level(score: int) -> str:
    if score >= 60:
        return "高风险"
    if score >= 25:
        return "中风险"
    return "低风险"


def _guess_scam_type(text: str, signals: list[dict[str, Any]], rules: dict[str, Any]) -> tuple[str, str]:
    signal_ids = {signal["signal_id"] for signal in signals}
    best_type = ("unknown", "未明确类型")
    best_score = 0

    for scam_type in rules["scam_types"]:
        score = 0
        for keyword in scam_type.get("keywords", []):
            if keyword in text:
                score += 3
        for signal_id in scam_type.get("signals", []):
            if signal_id in signal_ids:
                score += 2
        if score > best_score:
            best_score = score
            best_type = (scam_type["id"], scam_type["label"])

    return best_type


def _highlight_segments(text: str, signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    spans = sorted(
        [
            (item["start"], item["end"], item)
            for item in signals
            if 0 <= item["start"] < item["end"] <= len(text)
        ],
        key=lambda x: (x[0], x[1]),
    )
    if not spans:
        return [{"text": text, "risk": False, "label": "", "signal_id": ""}] if text else []

    merged: list[dict[str, Any]] = []
    for start, end, signal in spans:
        if not merged or start > merged[-1]["end"]:
            merged.append(
                {
                    "start": start,
                    "end": end,
                    "labels": [signal["label"]],
                    "signal_ids": [signal["signal_id"]],
                }
            )
            continue

        current = merged[-1]
        current["end"] = max(current["end"], end)
        if signal["label"] not in current["labels"]:
            current["labels"].append(signal["label"])
        if signal["signal_id"] not in current["signal_ids"]:
            current["signal_ids"].append(signal["signal_id"])

    chunks: list[dict[str, Any]] = []
    cursor = 0
    for item in merged:
        start = item["start"]
        end = item["end"]
        if cursor < start:
            chunks.append({"text": text[cursor:start], "risk": False, "label": "", "signal_id": ""})
        chunks.append(
            {
                "text": text[start:end],
                "risk": True,
                "label": "、".join(item["labels"]),
                "signal_id": ",".join(item["signal_ids"]),
            }
        )
        cursor = end
    if cursor < len(text):
        chunks.append({"text": text[cursor:], "risk": False, "label": "", "signal_id": ""})
    return [item for item in chunks if item["text"]]


def _highlight(text: str, signals: list[dict[str, Any]]) -> str:
    return "".join(item["text"] for item in _highlight_segments(text, signals))


def _score_signals(signals: list[dict[str, Any]], input_type: str) -> int:
    by_id: dict[str, list[dict[str, Any]]] = {}
    for signal in signals:
        by_id.setdefault(signal["signal_id"], []).append(signal)

    score = 0
    for grouped in by_id.values():
        grouped = sorted(grouped, key=lambda item: item["weight"], reverse=True)
        score += grouped[0]["weight"]
        score += min(6, max(0, len(grouped) - 1) * 2)

    if input_type == "link" and score < 25:
        score = 25
    if any(signal_id.startswith("url_model_") for signal_id in by_id) and score < 60:
        score = 60
    if "macbert_finetuned_fraud" in by_id and score < 25:
        score = 25
    if "macbert_semantic_match" in by_id and score < 25:
        score = 25
    return min(100, score)


def _summarize_signals(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for signal in signals:
        item = summary.setdefault(
            signal["signal_id"],
            {
                "signal_id": signal["signal_id"],
                "label": signal["label"],
                "count": 0,
                "weight": 0,
            },
        )
        item["count"] += 1
        item["weight"] += signal["weight"]
    return sorted(summary.values(), key=lambda item: item["weight"], reverse=True)


def _confidence(score: int, signals: list[dict[str, Any]], scam_type_id: str) -> int:
    signal_kinds = len({signal["signal_id"] for signal in signals})
    base = min(90, score) + min(10, signal_kinds * 2)
    if scam_type_id != "unknown":
        base += 6
    return max(35, min(99, base))


def _append_unique(target: list[str], items: list[str]) -> None:
    for item in items:
        normalized = item.strip()
        if normalized and normalized not in target:
            target.append(normalized)


def _split_qwen_suggestions(text: str) -> list[str]:
    cleaned = re.sub(r"^\s*[-*\d.、）)]+\s*", "", text.strip())
    if not cleaned:
        return []
    parts = [
        re.sub(r"^\s*[-*\d.、）)]+\s*", "", item.strip())
        for item in re.split(r"[\n。；;]+", cleaned)
        if item.strip()
    ]
    return parts[:MAX_SUGGESTIONS] if parts else [cleaned]


def _build_preconfigured_suggestions(
    scam_type_id: str,
    signals: list[dict[str, Any]],
    rules: dict[str, Any],
) -> list[str]:
    suggestions: list[str] = []
    type_actions = SCAM_TYPE_ACTIONS.get(scam_type_id, [])
    _append_unique(suggestions, type_actions)

    if scam_type_id != "unknown":
        for scam_type in rules["scam_types"]:
            if scam_type["id"] == scam_type_id:
                _append_unique(suggestions, [scam_type["suggestion"]])
                break

    signal_suggestions = [item["suggestion"] for item in signals if item.get("suggestion")]
    _append_unique(suggestions, signal_suggestions)
    return suggestions[:MAX_SUGGESTIONS]


def analyze_text(content: str, input_type: str = "text") -> dict[str, Any]:
    text = content.strip()
    rules = _load_rules()
    signals: list[dict[str, Any]] = []
    model_insights: list[dict[str, Any]] = []
    seen = set()

    for signal in rules["risk_signals"]:
        for keyword in signal["keywords"]:
            for start, end in _find_keyword_spans(text, keyword):
                key = (signal["id"], keyword, start, end)
                if key in seen:
                    continue
                seen.add(key)
                signals.append(
                    _make_signal(
                        signal["id"],
                        signal["label"],
                        keyword,
                        start,
                        end,
                        signal["weight"],
                        signal["explanation"],
                        signal["suggestion"],
                    )
                )

    for match in URL_RE.finditer(text):
        signals.append(
            _make_signal(
                "suspicious_link",
                "可疑链接",
                match.group(0),
                match.start(),
                match.end(),
                12,
                "文本中包含外部链接，诈骗话术常通过短链、仿冒域名或陌生下载链接诱导用户跳转。",
                "不要直接点击陌生链接，应通过官方 App、官网或学校渠道核实。",
            )
        )

    for item in classify_urls(text):
        model_insights.append(
            {
                "model": "URL分类模型",
                "status": item["status"],
                "label": item["label"],
                "score": item["confidence"],
                "detail": item["detail"],
            }
        )
        meta = URL_MODEL_LABELS.get(item["label"])
        if not meta:
            continue
        signals.append(
            _make_signal(
                f"url_model_{item['label']}",
                meta["label"],
                item["url"],
                item["start"],
                item["end"],
                meta["weight"],
                f"{meta['explanation']} 模型置信度：{item['confidence']}%。",
                meta["suggestion"],
            )
        )

    for match in AMOUNT_RE.finditer(text):
        signals.append(
            _make_signal(
                "amount",
                "具体金额",
                match.group(0),
                match.start(),
                match.end(),
                5,
                "出现具体金额不必然代表诈骗，但和垫付、保证金、返利、退款等话术组合时风险显著升高。",
                "涉及金额操作时先暂停，核实对方身份和交易渠道。",
            )
        )

    _add_composite_signals(signals)
    initial_score = _score_signals(signals, input_type)
    text_classifier_ran = False
    fast_ocr_analysis = input_type == "screenshot_ocr" and settings.ocr_fast_analysis
    if input_type in {"text", "sms", "screenshot_ocr"} and not fast_ocr_analysis and initial_score < 60 and len(text) >= 8:
        text_classifier_ran = True
        classifier = classify_fraud_text(text)
        model_insights.append(
            {
                "model": "MacBERT微调分类器",
                "status": classifier.get("status", "unknown"),
                "label": classifier.get("label", ""),
                "score": classifier.get("score", 0),
                "detail": classifier.get("detail", ""),
            }
        )
        if (
            classifier.get("status") == "ok"
            and classifier.get("label") == "fraud"
            and classifier.get("score", 0) >= 60
        ):
            signals.append(
                _make_signal(
                    "macbert_finetuned_fraud",
                    "MacBERT微调模型判定涉诈",
                    "领域微调文本分类",
                    -1,
                    -1,
                    10 if classifier.get("score", 0) < 80 else 14,
                    f"基于 ChiFraud 与 TeleAntiFraud 文本样本微调的 MacBERT 将该内容判为涉诈，置信度 {classifier.get('score')}%。",
                    "建议结合规则风险点继续核验，不凭单一模型结果直接做法律定性。",
                )
            )

    if input_type in {"text", "sms", "screenshot_ocr"} and not fast_ocr_analysis and len(signals) <= 1 and len(text) >= 8:
        semantic = semantic_match_text(text)
        model_insights.append(
            {
                "model": "MacBERT语义匹配",
                "status": semantic.get("status", "unknown"),
                "label": semantic.get("label", ""),
                "score": semantic.get("score", 0),
                "detail": semantic.get("detail", ""),
            }
        )
        if semantic.get("status") == "ok" and semantic.get("score", 0) >= 0.82:
            signals.append(
                _make_signal(
                    "macbert_semantic_match",
                    "MacBERT语义风险匹配",
                    semantic.get("label", "相似诈骗语义"),
                    -1,
                    -1,
                    10 if semantic.get("score", 0) < 0.9 else 14,
                    f"MacBERT 将文本语义与“{semantic.get('label')}”风险原型匹配，相似度 {semantic.get('score')}。",
                    "即使未命中明显关键词，也建议按相似诈骗场景核实身份、资金要求和官方渠道。",
                )
            )
    else:
        detail = f"规则/URL信号已足够，初始风险分 {initial_score}"
        if fast_ocr_analysis:
            detail = f"OCR快速分析模式已启用，跳过截图链路的MacBERT语义补充；{detail}"
        if text_classifier_ran:
            detail += "；已先调用微调分类器"
        model_insights.append(
            {
                "model": "MacBERT语义匹配",
                "status": "skipped",
                "label": "",
                "score": 0,
                "detail": detail,
            }
        )

    score = _score_signals(signals, input_type)
    scam_type_id, scam_type_label = _guess_scam_type(text, signals, rules)
    level = _risk_level(score)

    suggestions = _build_preconfigured_suggestions(scam_type_id, signals, rules)

    evidence = [f"{item['label']}：{item['keyword']}" for item in signals[:8]]
    summary = f"系统识别到 {len(signals)} 个风险信号，综合判断为{level}。"
    if scam_type_id != "unknown":
        summary += f" 当前内容疑似涉及“{scam_type_label}”。"

    analysis = {
        "risk_level": level,
        "risk_score": score,
        "confidence": _confidence(score, signals, scam_type_id),
        "scam_type": scam_type_label,
        "scam_type_id": scam_type_id,
        "summary": summary,
        "signals": signals,
        "signal_summary": _summarize_signals(signals),
        "suggestions": suggestions,
        "highlighted_text": _highlight(text, signals),
        "highlighted_segments": _highlight_segments(text, signals),
        "evidence": evidence,
        "model_insights": model_insights,
        "enhanced_advice": "",
    }
    if suggestions:
        analysis["model_insights"].append(
            {
                "model": "Qwen3-4B-Instruct",
                "status": "skipped",
                "label": "增强建议生成",
                "score": 0,
                "detail": "已命中预设处置建议，跳过本地生成模型以提升响应速度。",
            }
        )
    elif fast_ocr_analysis:
        analysis["model_insights"].append(
            {
                "model": "Qwen3-4B-Instruct",
                "status": "skipped",
                "label": "增强建议生成",
                "score": 0,
                "detail": "OCR快速分析模式已启用，截图链路跳过本地生成模型以提升响应速度。",
            }
        )
    else:
        qwen = generate_qwen_advice(text, analysis)
        analysis["model_insights"].append(
            {
                "model": "Qwen3-4B-Instruct",
                "status": qwen.get("status", "unknown"),
                "label": "增强建议生成",
                "score": 0,
                "detail": qwen.get("detail", ""),
            }
        )
        if qwen.get("status") == "ok" and qwen.get("text"):
            analysis["enhanced_advice"] = qwen["text"]
            analysis["suggestions"] = _split_qwen_suggestions(qwen["text"])
    if not analysis["suggestions"]:
        analysis["suggestions"] = ["暂未发现明显高危话术，但仍建议通过官方渠道核实身份和交易信息，不要泄露验证码、密码或银行卡信息。"]
    return analysis
