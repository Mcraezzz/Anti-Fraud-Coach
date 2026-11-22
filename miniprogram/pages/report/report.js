const api = require("../../utils/api");

const DEFAULT_RADAR = {
  "风险识别": 82,
  "核实意识": 76,
  "证据保存": 72,
  "隐私保护": 80,
  "平台意识": 74
};

const RADAR_ORDER = ["风险识别", "核实意识", "证据保存", "隐私保护", "平台意识"];

function clampScore(value) {
  const score = Number(value);
  if (Number.isNaN(score)) return 0;
  return Math.max(0, Math.min(100, Math.round(score)));
}

function normalizeRadar(rawRadar) {
  const radar = { ...DEFAULT_RADAR, ...(rawRadar || {}) };
  return RADAR_ORDER.map((label) => ({
    label,
    value: clampScore(radar[label])
  }));
}

function abilityLevel(score) {
  const normalized = clampScore(score);
  if (normalized >= 90) return { label: "反诈尖兵", className: "excellent" };
  if (normalized >= 80) return { label: "安全练习生", className: "good" };
  if (normalized >= 70) return { label: "稳步提升", className: "mid" };
  return { label: "重点强化", className: "low" };
}

function normalizeDashboard(raw) {
  const dashboard = raw || {};
  const topErrors = Array.isArray(dashboard.top_error_types)
    ? dashboard.top_error_types
    : Array.isArray(dashboard.weak_types)
      ? dashboard.weak_types.map((item) => ({ label: item.label, value: item.count }))
      : Array.isArray(dashboard.top_scam_types)
        ? dashboard.top_scam_types.map((item) => ({ label: item.label, value: item.count }))
        : [];

  const averageScore = dashboard.average_score != null ? dashboard.average_score : 82;
  const level = abilityLevel(averageScore);
  return {
    ...dashboard,
    average_score: averageScore,
    training_count: dashboard.training_count != null ? dashboard.training_count : dashboard.training_attempts || 0,
    high_risk_cases: dashboard.high_risk_cases != null ? dashboard.high_risk_cases : dashboard.high_risk_count || 0,
    top_error_types: topErrors,
    radarItems: normalizeRadar(dashboard.radar),
    ability_level: level.label,
    ability_level_class: level.className
  };
}

Page({
  data: {
    dashboard: {
      average_score: 82,
      training_count: 0,
      high_risk_cases: 0,
      top_error_types: [],
      radarItems: normalizeRadar(DEFAULT_RADAR)
    },
    resources: null,
    error: "",
    loading: false
  },

  onLoad() {
    this.loadData();
  },

  onReady() {
    this.drawRadarChart();
  },

  async loadData(silent = false) {
    if (!silent) {
      this.setData({ loading: true, error: "" });
    } else {
      this.setData({ error: "" });
    }
    try {
      const token = getApp().globalData.authToken || wx.getStorageSync("authToken");
      const dashboardRequest = token
        ? api.getAccountStats().catch(() => api.getDashboard())
        : api.getDashboard();
      const [dashboardRaw, resources] = await Promise.all([
        dashboardRequest,
        api.getResources()
      ]);
      this.setData({
        dashboard: normalizeDashboard(dashboardRaw),
        resources: { models: [], ...(resources || {}) }
      }, () => this.drawRadarChart());
    } catch (err) {
      this.setData({
        error: api.getErrorMessage(err, "报告服务未连接，请先启动后端服务。"),
        dashboard: normalizeDashboard(this.data.dashboard)
      }, () => this.drawRadarChart());
    } finally {
      if (!silent) {
        this.setData({ loading: false });
      }
    }
  },

  async onPullDownRefresh() {
    await this.loadData(true);
    wx.stopPullDownRefresh();
  },

  drawRadarChart() {
    const items = (this.data.dashboard && this.data.dashboard.radarItems && this.data.dashboard.radarItems.length)
      ? this.data.dashboard.radarItems
      : normalizeRadar(DEFAULT_RADAR);

    const query = wx.createSelectorQuery().in(this);
    query.select("#abilityRadar").fields({ node: true, size: true }).exec((res) => {
      const canvasInfo = res && res[0];
      if (canvasInfo && canvasInfo.node) {
        this.drawRadarWithNode(canvasInfo.node, canvasInfo.width, canvasInfo.height, items);
      } else {
        this.drawRadarLegacy(items);
      }
    });
  },

  drawRadarWithNode(canvas, width, height, items) {
    const ctx = canvas.getContext("2d");
    const dpr = wx.getSystemInfoSync().pixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);
    this.paintRadar(ctx, width, height, items);
  },

  drawRadarLegacy(items) {
    const ctx = wx.createCanvasContext("abilityRadar", this);
    this.paintRadar(ctx, 330, 320, items);
    ctx.draw();
  },

  paintRadar(ctx, width, height, items) {
    const count = items.length;
    const centerX = width / 2;
    const centerY = height * 0.53;
    const radius = Math.min(width * 0.3, height * 0.27);
    const labelRadius = Math.min(radius + 24, height * 0.4);
    const levels = 5;
    const edgeGap = 12;

    ctx.clearRect(0, 0, width, height);
    ctx.lineWidth = 1;
    ctx.font = "600 14px sans-serif";

    const pointAt = (index, score = 100, baseRadius = radius) => {
      const angle = -Math.PI / 2 + (Math.PI * 2 * index) / count;
      const distance = baseRadius * (score / 100);
      return {
        x: centerX + Math.cos(angle) * distance,
        y: centerY + Math.sin(angle) * distance,
        angle
      };
    };

    for (let level = levels; level >= 1; level -= 1) {
      const score = (level / levels) * 100;
      ctx.beginPath();
      for (let index = 0; index < count; index += 1) {
        const point = pointAt(index, score);
        if (index === 0) ctx.moveTo(point.x, point.y);
        else ctx.lineTo(point.x, point.y);
      }
      ctx.closePath();
      ctx.strokeStyle = level === levels ? "#DBEAFE" : "#EAF1FF";
      ctx.stroke();
    }

    for (let index = 0; index < count; index += 1) {
      const edge = pointAt(index);
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.lineTo(edge.x, edge.y);
      ctx.strokeStyle = "#E8EFFC";
      ctx.stroke();
    }

    ctx.beginPath();
    items.forEach((item, index) => {
      const point = pointAt(index, item.value);
      if (index === 0) ctx.moveTo(point.x, point.y);
      else ctx.lineTo(point.x, point.y);
    });
    ctx.closePath();
    ctx.fillStyle = "rgba(37, 99, 235, 0.18)";
    ctx.fill();
    ctx.strokeStyle = "#2563EB";
    ctx.lineWidth = 2.5;
    ctx.stroke();

    items.forEach((item, index) => {
      const point = pointAt(index, item.value);
      ctx.beginPath();
      ctx.arc(point.x, point.y, 3.5, 0, Math.PI * 2);
      ctx.fillStyle = "#10B981";
      ctx.fill();
    });

    items.forEach((item, index) => {
      const labelPoint = pointAt(index, 100, labelRadius);
      const labelText = item.label;
      const valueText = `${item.value}`;
      ctx.font = "600 14px sans-serif";
      const labelWidth = ctx.measureText ? ctx.measureText(labelText).width : labelText.length * 14;
      ctx.font = "700 16px sans-serif";
      const valueWidth = ctx.measureText ? ctx.measureText(valueText).width : valueText.length * 16;
      const blockWidth = Math.max(labelWidth, valueWidth);
      const padding = 4;
      let x = labelPoint.x;
      let y = labelPoint.y;
      const cos = Math.cos(labelPoint.angle);
      const sin = Math.sin(labelPoint.angle);

      if (cos > 0.25) {
        x = Math.min(labelPoint.x + padding, width - blockWidth - edgeGap);
        ctx.textAlign = "left";
      } else if (cos < -0.25) {
        x = Math.max(labelPoint.x - padding, blockWidth + edgeGap);
        ctx.textAlign = "right";
      } else {
        x = Math.max(blockWidth / 2 + edgeGap, Math.min(labelPoint.x, width - blockWidth / 2 - edgeGap));
        ctx.textAlign = "center";
      }

      if (sin > 0.55) y += 4;
      if (sin < -0.55) y = Math.max(18, y - 18);

      ctx.font = "600 14px sans-serif";
      ctx.fillStyle = "#475569";
      ctx.fillText(labelText, x, y);
      ctx.font = "700 16px sans-serif";
      ctx.fillStyle = "#2563EB";
      ctx.fillText(valueText, x, y + 22);
    });
  }
});
