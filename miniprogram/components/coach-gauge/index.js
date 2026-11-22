Component({
  properties: {
    score: { type: null, value: null },
    mode: { type: String, value: "ring" },
    size: { type: Number, value: 64 },
    level: { type: String, value: "low" },
  },
  observers: {
    "score,mode,size,level": function () {
      wx.nextTick(() => this.draw());
    },
  },
  lifetimes: {
    ready() {
      this.draw();
    },
  },
  methods: {
    draw() {
      const half = this.data.mode === "half",
        s = this.data.size,
        w = half ? 176 : s,
        h = half ? 98 : s;
      const ctx = wx.createCanvasContext("gauge", this);
      const val = Math.max(0, Math.min(100, Number(this.data.score) || 0));
      ctx.clearRect(0, 0, w, h);
      ctx.setLineWidth(half ? 14 : 5);
      ctx.setLineCap("round");
      const x = half ? 88 : s / 2,
        y = half ? 88 : s / 2,
        r = half ? 72 : (s - 5) / 2,
        start = half ? Math.PI : -Math.PI / 2,
        total = half ? Math.PI : Math.PI * 2;
      ctx.beginPath();
      ctx.arc(x, y, r, start, start + total);
      ctx.setStrokeStyle(half ? "#E2E8F0" : "rgba(255,255,255,.16)");
      ctx.stroke();
      if (val) {
        ctx.beginPath();
        ctx.arc(x, y, r, start, start + (total * val) / 100);
        ctx.setStrokeStyle(
          half
            ? { high: "#FF4D4F", medium: "#FF9F1C", low: "#21C58B" }[this.data.level] || "#21C58B"
            : "#21C58B",
        );
        ctx.stroke();
      }
      ctx.draw();
    },
  },
});
