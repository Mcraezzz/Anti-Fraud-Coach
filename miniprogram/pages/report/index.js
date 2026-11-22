const api = require("../../utils/api");
const { go, fail, date } = require("../../utils/page");
Page({
  data: { report: null, error: "", loading: true },
  go,
  onShow() {
    this.load();
  },
  async load() {
    this.setData({ loading: true, error: "" });
    try {
      const report = await api.report();
      report.recentTraining = report.recentTraining.map((t) => ({ ...t, date: date(t.timestamp) }));
      this.setData({ report, loading: false }, () => this.draw());
    } catch (e) {
      fail(this, e);
    }
  },
  draw() {
    if (!this.data.report) return;
    const rows = this.data.report.radar;
    wx.createSelectorQuery()
      .in(this)
      .select("#radar")
      .boundingClientRect((rect) => {
        if (!rect) return;
        const ctx = wx.createCanvasContext("radar", this),
          w = rect.width,
          h = rect.height,
          cx = w / 2,
          cy = h / 2,
          r = Math.min(w * 0.3, h * 0.34);
        const point = (i, scale) => ({
          x: cx + Math.cos(-Math.PI / 2 + (i * Math.PI) / 3) * r * scale,
          y: cy + Math.sin(-Math.PI / 2 + (i * Math.PI) / 3) * r * scale,
        });
        [0.25, 0.5, 0.75, 1].forEach((scale) => {
          ctx.beginPath();
          for (let i = 0; i < 6; i++) {
            const p = point(i, scale);
            i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y);
          }
          ctx.closePath();
          ctx.setStrokeStyle("#DCE7FF");
          ctx.stroke();
        });
        ctx.setFontSize(11);
        ctx.setFillStyle("#52627A");
        ctx.setTextAlign("center");
        rows.forEach((row, i) => {
          const p = point(i, 1.25);
          ctx.fillText(row.label, p.x, p.y + 4);
          const q = point(i, 1);
          ctx.beginPath();
          ctx.moveTo(cx, cy);
          ctx.lineTo(q.x, q.y);
          ctx.stroke();
        });
        ctx.beginPath();
        rows.forEach((row, i) => {
          const p = point(i, (row.score || 0) / 100);
          i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y);
        });
        ctx.closePath();
        ctx.setFillStyle("rgba(30,99,255,.16)");
        ctx.fill();
        ctx.setStrokeStyle("#1E63FF");
        ctx.setLineWidth(2);
        ctx.stroke();
        ctx.draw();
      })
      .exec();
  },
});
