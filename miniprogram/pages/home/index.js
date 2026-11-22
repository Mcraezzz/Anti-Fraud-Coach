const api = require("../../utils/api");
const { go, fail } = require("../../utils/page");
Page({
  data: {
    report: null,
    error: "",
    loading: true,
    reminder: true,
    entries: [
      { mode: "text", title: "粘贴文本", sub: "聊天与话术分析", icon: "scan-text" },
      { mode: "ocr", title: "上传截图", sub: "图片 OCR 识诈", icon: "image-up" },
      { mode: "url", title: "查链接", sub: "钓鱼网址研判", icon: "link-2" },
      { mode: "sms", title: "查短信", sub: "通知类骗局核验", icon: "message-square-warning" },
    ],
  },
  go,
  onShow() {
    this.load();
  },
  async load() {
    this.setData({ loading: true, error: "" });
    try {
      const [report, profile] = await Promise.all([api.report(), api.profile()]);
      getApp().globalData.preferences = profile.preferences;
      this.setData({ report, reminder: profile.preferences.weeklyReminder, loading: false });
    } catch (e) {
      fail(this, e);
    }
  },
});
