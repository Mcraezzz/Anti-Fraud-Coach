const fallback = {
  risk_level: "高风险",
  risk_score: 87,
  confidence: 92,
  scam_type: "刷单返利 / 虚假兼职",
  summary: "发现先垫付、保证金、脱离平台和紧迫施压等高频风险信号。",
  highlighted_text: "需要你先垫付 300 元保证金，完成任务后马上返现，不要告诉其他人。",
  signals: [
    { label: "金钱诱导", keyword: "保证金", explanation: "先支付费用是刷单、兼职、贷款类骗局的高频特征。" },
    { label: "紧迫施压", keyword: "马上", explanation: "限时话术会压缩核实时间。" },
    { label: "脱离平台", keyword: "加微信", explanation: "脱离官方平台后维权难度上升。" }
  ],
  suggestions: ["暂停转账或付款", "不提供验证码、身份证、银行卡", "不下载陌生 App，不进行屏幕共享", "保存聊天、链接、转账凭证", "向辅导员、平台客服或公安机关核实"],
  model_insights: [],
  enhanced_advice: ""
};

function clampPercent(value, fallbackValue = 0) {
  const score = Number(value);
  if (Number.isNaN(score)) return fallbackValue;
  return Math.max(0, Math.min(100, Math.round(score)));
}

function riskVisual(level, score) {
  const riskLevel = String(level || "");
  const color = riskLevel.includes("低")
    ? "#10B981"
    : riskLevel.includes("中")
      ? "#F59E0B"
      : "#EF4444";
  const angle = clampPercent(score) * 3.6;
  return {
    risk_score: clampPercent(score),
    gaugeStyle: `background: conic-gradient(from -90deg, ${color} 0deg ${angle}deg, rgba(255, 255, 255, 0.15) ${angle}deg 360deg);`,
    riskBadgeStyle: `background: ${color};`
  };
}

function stripRiskMarkers(text) {
  return String(text || "").replace(/【风险:([^】]+)】/g, "$1");
}

function collectSignalSpans(text, signals) {
  const spans = [];
  (signals || []).forEach((signal) => {
    if (Number.isInteger(signal.start) && Number.isInteger(signal.end) && signal.start >= 0 && signal.end > signal.start && signal.end <= text.length) {
      spans.push({
        start: signal.start,
        end: signal.end,
        label: signal.label || "",
        signal_id: signal.signal_id || ""
      });
      return;
    }
    const keyword = signal.keyword || "";
    if (!keyword) return;
    let start = text.indexOf(keyword);
    while (start !== -1) {
      spans.push({
        start,
        end: start + keyword.length,
        label: signal.label || "",
        signal_id: signal.signal_id || ""
      });
      start = text.indexOf(keyword, start + keyword.length);
    }
  });
  return spans.sort((a, b) => a.start - b.start || a.end - b.end);
}

function buildHighlightedSegments(text, signals) {
  const cleanText = stripRiskMarkers(text);
  const spans = collectSignalSpans(cleanText, signals);
  if (!spans.length) {
    return cleanText ? [{ text: cleanText, risk: false, label: "", signal_id: "" }] : [];
  }

  const merged = [];
  spans.forEach((span) => {
    const current = merged[merged.length - 1];
    if (!current || span.start > current.end) {
      merged.push({
        start: span.start,
        end: span.end,
        labels: span.label ? [span.label] : [],
        signalIds: span.signal_id ? [span.signal_id] : []
      });
      return;
    }
    current.end = Math.max(current.end, span.end);
    if (span.label && !current.labels.includes(span.label)) current.labels.push(span.label);
    if (span.signal_id && !current.signalIds.includes(span.signal_id)) current.signalIds.push(span.signal_id);
  });

  const chunks = [];
  let cursor = 0;
  merged.forEach((span) => {
    if (cursor < span.start) {
      chunks.push({ text: cleanText.slice(cursor, span.start), risk: false, label: "", signal_id: "" });
    }
    chunks.push({
      text: cleanText.slice(span.start, span.end),
      risk: true,
      label: span.labels.join("、"),
      signal_id: span.signalIds.join(",")
    });
    cursor = span.end;
  });
  if (cursor < cleanText.length) {
    chunks.push({ text: cleanText.slice(cursor), risk: false, label: "", signal_id: "" });
  }
  return chunks.filter((item) => item.text);
}

function normalizeHighlightedSegments(segments, text, signals) {
  if (Array.isArray(segments) && segments.length) {
    return segments
      .filter((item) => item && item.text)
      .map((item) => ({
        text: stripRiskMarkers(item.text),
        risk: !!item.risk,
        label: item.label || "",
        signal_id: item.signal_id || ""
      }));
  }
  return buildHighlightedSegments(text, signals);
}

function normalizeResult(raw, content) {
  const result = raw || {};
  const signals = Array.isArray(result.signals) ? result.signals : fallback.signals;
  const highlightedText = stripRiskMarkers(result.highlighted_text || content || fallback.highlighted_text);
  const merged = {
    ...fallback,
    ...result
  };
  const visual = riskVisual(merged.risk_level, merged.risk_score);
  return {
    ...merged,
    ...visual,
    confidence: clampPercent(merged.confidence, fallback.confidence),
    highlighted_text: highlightedText,
    highlighted_segments: normalizeHighlightedSegments(result.highlighted_segments, highlightedText, signals),
    signals,
    suggestions: Array.isArray(result.suggestions) ? result.suggestions : fallback.suggestions,
    model_insights: Array.isArray(result.model_insights) ? result.model_insights : [],
    enhanced_advice: result.enhanced_advice || ""
  };
}

Page({
  data: {
    content: fallback.highlighted_text,
    result: normalizeResult(fallback, fallback.highlighted_text),
    ocr: null
  },

  onLoad() {
    const stored = wx.getStorageSync("lastAnalyzeResult");
    if (stored && stored.result) {
      const content = stored.content || fallback.highlighted_text;
      this.setData({ result: normalizeResult(stored.result, content), content, ocr: stored.ocr || null });
    } else {
      this.setData({ result: normalizeResult(fallback, fallback.highlighted_text), content: fallback.highlighted_text, ocr: null });
    }
  },

  goTraining() {
    wx.switchTab({ url: "/pages/train/train" });
  },

  rescan() {
    wx.redirectTo({ url: "/pages/detect/index?type=text" });
  },

  copySuggestions() {
    const suggestions = this.data.result && this.data.result.suggestions ? this.data.result.suggestions : [];
    const text = suggestions.map((item, index) => `${index + 1}. ${item}`).join("\n");
    if (!text) {
      return;
    }
    wx.setClipboardData({
      data: text,
      success: () => wx.showToast({ title: "已复制建议", icon: "success" })
    });
  }
});
