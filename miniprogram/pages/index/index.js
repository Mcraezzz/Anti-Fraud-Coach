const api = require("../../utils/api");

const DEFAULT_SAFETY_SCORE = 86;

function clampPercent(value, fallback = DEFAULT_SAFETY_SCORE) {
  const score = Number(value);
  if (Number.isNaN(score)) return fallback;
  return Math.max(0, Math.min(100, Math.round(score)));
}

function buildScoreRingStyle(score) {
  const angle = clampPercent(score) * 3.6;
  return `background: conic-gradient(from -90deg, #34D399 0deg ${angle}deg, rgba(255, 255, 255, 0.15) ${angle}deg 360deg);`;
}

function normalizeOverview(raw) {
  const overview = raw || {};
  const safetyScore = clampPercent(
    overview.safety_index != null
      ? overview.safety_index
      : overview.completion_rate != null
        ? overview.completion_rate
        : overview.average_score != null && overview.average_score > 0
          ? overview.average_score
          : DEFAULT_SAFETY_SCORE
  );

  return {
    safetyScore,
    scoreRingStyle: buildScoreRingStyle(safetyScore),
    identifiedRiskCount: Number(overview.detection_count != null ? overview.detection_count : overview.high_risk_cases || 12),
    trainingProgress: clampPercent(
      overview.weekly_training_progress != null
        ? overview.weekly_training_progress
        : overview.completion_rate != null
          ? overview.completion_rate
          : 70,
      70
    )
  };
}

Page({
  data: {
    content: "同学你好，我们这边是平台客服，你的订单异常可以三倍理赔。请加微信私聊，按提示打开屏幕共享，并提供验证码完成退款。",
    result: null,
    loadingAnalyze: false,
    loadingOverview: false,
    error: "",
    serviceNotice: "",
    safetyScore: DEFAULT_SAFETY_SCORE,
    scoreRingStyle: buildScoreRingStyle(DEFAULT_SAFETY_SCORE),
    identifiedRiskCount: 12,
    trainingProgress: 70,
    scanEntrances: [
      { type: "text", title: "粘贴文本", desc: "聊天话术识别", icon: "../../assets/icons/scan-text.svg" },
      { type: "image", title: "上传截图", desc: "OCR 风险扫描", icon: "../../assets/icons/scan-image.svg" },
      { type: "link", title: "检测链接", desc: "网址与跳转风险", icon: "../../assets/icons/scan-link.svg" },
      { type: "sms", title: "分析短信", desc: "号码与诱导语", icon: "../../assets/icons/scan-sms.svg" }
    ],
    quickFeatures: [
      { title: "反诈知识问答", desc: "基于知识库回答", url: "/pages/qa/index", type: "tab" },
      { title: "情景训练", desc: "六类校园骗局", url: "/pages/train/train", type: "tab" },
      { title: "能力报告", desc: "雷达图与易错项", url: "/pages/report/report", type: "tab" },
      { title: "校园案例库", desc: "相似案例追溯", url: "/pages/qa/index", type: "tab" }
    ]
  },

  onShow() {
    this.loadSafetyOverview();
  },

  async loadSafetyOverview(silent = true) {
    if (!silent) {
      this.setData({ loadingOverview: true });
    }
    try {
      const token = getApp().globalData.authToken || wx.getStorageSync("authToken");
      const overview = token
        ? await api.getAccountStats().catch(() => api.getDashboard())
        : await api.getDashboard();
      this.setData({ ...normalizeOverview(overview), serviceNotice: "" });
    } catch (err) {
      this.setData({
        ...normalizeOverview(this.data),
        serviceNotice: api.getErrorMessage(err, "后端未连接，已显示本地示例数据。")
      });
    } finally {
      if (!silent) {
        this.setData({ loadingOverview: false });
      }
    }
  },

  async onPullDownRefresh() {
    await this.loadSafetyOverview(false);
    wx.stopPullDownRefresh();
  },

  onInput(event) {
    this.setData({ content: event.detail.value });
  },

  useSample() {
    this.setData({
      content: "兼职群任务：先垫付 300 元完成刷单，返利 60 元。名额有限，马上加微信私聊，不要告诉老师。"
    });
  },

  goDetect(event) {
    wx.navigateTo({
      url: `/pages/detect/index?type=${event.currentTarget.dataset.type || "text"}`
    });
  },

  goFeature(event) {
    wx.switchTab({
      url: event.currentTarget.dataset.url
    });
  },

  async analyze() {
    if (this.data.loadingAnalyze) {
      return;
    }
    const content = this.data.content.trim();
    if (!content) {
      wx.showToast({ title: "请输入内容", icon: "none" });
      return;
    }
    this.setData({ loadingAnalyze: true, error: "" });
    try {
      const result = await api.analyze(content);
      wx.setStorageSync("lastAnalyzeResult", { result, content });
      wx.navigateTo({ url: "/pages/result/result" });
    } catch (err) {
      this.setData({ error: api.getErrorMessage(err, "风险识别请求失败，请确认 FastAPI 已启动并允许本地请求。") });
    } finally {
      this.setData({ loadingAnalyze: false });
    }
  }
});
