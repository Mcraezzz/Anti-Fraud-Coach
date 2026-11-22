const api = require("../../utils/api");
const { go, fail } = require("../../utils/page");
Page({
  activeSheet: "",
  async openSheet(e) {
    const activeSheet = e.currentTarget.dataset.sheet;
    const meta = {
      history: ["我的识别记录", "点击任意历史记录可重新查看完整拆解报告"],
      privacy: ["隐私保护设置", "管理敏感信息保护与识别记录"],
      preferences: ["系统偏好设置", "自定义交互反馈与数据管理"],
    };
    this.setData({
      activeSheet,
      sheetTitle: meta[activeSheet][0],
      sheetSubtitle: meta[activeSheet][1],
      motion: wx.getStorageSync("coachMotion") !== false,
    });
    if (activeSheet === "history") {
      try {
        this.setData({ history: await api.history() });
      } catch (error) {
        wx.showToast({ title: error.message, icon: "none" });
      }
    }
  },
  closeSheet() {
    this.setData({ activeSheet: "" });
  },
  openHistory(e) {
    getApp().globalData.latestScan = this.data.history.find(
      (x) => x.id === e.currentTarget.dataset.id,
    );
    this.closeSheet();
    wx.navigateTo({ url: "/pages/result/index" });
  },
  clearHistory() {
    wx.showModal({
      title: "清空识别记录",
      content: "将删除当前会话的所有识别记录，训练进度保留。是否继续？",
      success: async (r) => {
        if (r.confirm) {
          try {
            await api.clearHistory();
            getApp().globalData.latestScan = null;
            this.closeSheet();
            this.load();
          } catch (error) {
            wx.showToast({ title: error.message, icon: "none" });
          }
        }
      },
    });
  },
  resetTraining() {
    wx.showModal({
      title: "重置训练进度",
      content: "确认将当前会话的训练记录与能力评估恢复为初始状态？",
      success: async (r) => {
        if (r.confirm) {
          try {
            await api.resetTraining();
            this.closeSheet();
            this.load();
          } catch (error) {
            wx.showToast({ title: error.message, icon: "none" });
          }
        }
      },
    });
  },
  toggleMotion(e) {
    wx.setStorageSync("coachMotion", e.detail.value);
    this.setData({ motion: e.detail.value });
    getApp().globalData.motion = e.detail.value;
  },

  data: {
    profile: null,
    report: null,
    error: "",
    loading: true,
    busy: false,
    base: "",
    name: "",
    showSettings: false,
    activeSheet: "",
    history: [],
    motion: true,
  },
  go,
  onShow() {
    this.load();
  },
  async load() {
    this.setData({ loading: true, error: "", base: api.base() });
    try {
      const [profile, report] = await Promise.all([api.profile(), api.report()]);
      getApp().globalData.preferences = profile.preferences;
      this.setData({ profile, report, name: profile.name, loading: false });
    } catch (e) {
      fail(this, e);
    }
  },
  inputName(e) {
    this.setData({ name: e.detail.value });
  },
  inputBase(e) {
    this.setData({ base: e.detail.value });
  },
  settings() {
    this.setData({ showSettings: !this.data.showSettings });
  },
  async save() {
    if (this.data.busy) return;
    this.setData({ busy: true, error: "" });
    try {
      const profile = await api.saveProfile({ name: this.data.name });
      this.setData({ profile, busy: false });
      wx.showToast({ title: "已保存" });
    } catch (e) {
      fail(this, e);
    }
  },
  async preference(e) {
    const key = e.currentTarget.dataset.key;
    try {
      const profile = await api.saveProfile({ preferences: { [key]: e.detail.value } });
      getApp().globalData.preferences = profile.preferences;
      this.setData({ profile });
    } catch (err) {
      fail(this, err);
      this.load();
    }
  },
  saveBase() {
    const base = this.data.base.trim().replace(/\/$/, "");
    if (!/^https?:\/\/[^/\s]+$/.test(base)) {
      this.setData({ error: "请输入有效服务地址，例如 http://127.0.0.1:8000" });
      return;
    }
    api.setBase(base);
    getApp().globalData.latestScan = null;
    this.load();
  },
  reset() {
    wx.showModal({
      title: "重新建立设备会话",
      content: "旧会话的记录不会转入新会话。仅在会话失效时使用，确认继续？",
      success: (r) => {
        if (r.confirm) {
          api.resetSession();
          this.load();
        }
      },
    });
  },
});
