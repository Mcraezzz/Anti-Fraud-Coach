const api = require("../../utils/api");
const { go, fail, date } = require("../../utils/page");
Page({
  data: { rows: [], loading: true, error: "" },
  go,
  onShow() {
    this.load();
  },
  async load() {
    this.setData({ loading: true, error: "" });
    try {
      const rows = (await api.history()).map((r) => ({
        ...r,
        date: date(r.timestamp),
        level: { high: "高风险", medium: "中风险", low: "低风险" }[r.riskLevel],
      }));
      this.setData({ rows, loading: false });
    } catch (e) {
      fail(this, e);
    }
  },
  open(e) {
    getApp().globalData.latestScan = this.data.rows.find(
      (r) => r.id === e.currentTarget.dataset.id,
    );
    wx.navigateTo({ url: "/pages/result/index" });
  },
  clear() {
    wx.showModal({
      title: "清除识别记录",
      content: "将删除当前设备会话在后端保存的全部识别记录，训练记录保留。是否继续？",
      success: async (r) => {
        if (!r.confirm) return;
        try {
          await api.clearHistory();
          getApp().globalData.latestScan = null;
          this.load();
        } catch (e) {
          fail(this, e);
        }
      },
    });
  },
});
