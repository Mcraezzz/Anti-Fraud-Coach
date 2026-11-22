const api = require("../../utils/api");
const presets = require("../../utils/presets");
const { fail } = require("../../utils/page");
Page({
  data: {
    mode: "text",
    text: "",
    image: "",
    error: "",
    busy: false,
    presets,
    tabs: [
      { id: "text", label: "文本", icon: "message-square-text" },
      { id: "ocr", label: "截图", icon: "upload" },
      { id: "url", label: "链接", icon: "link-2" },
      { id: "sms", label: "短信", icon: "shield-alert" },
    ],
  },
  onLoad(q) {
    this.setData({
      masking: getApp().globalData.preferences.autoMaskSensitive,
      tabs: this.data.tabs.map((x) => ({
        ...x,
        label: x.id === "ocr" ? "截图" : x.label,
        icon: { text: "message-square-text", ocr: "upload", url: "link-2", sms: "shield-alert" }[
          x.id
        ],
      })),
    });
    if (["text", "ocr", "url", "sms"].includes(q.mode)) this.setData({ mode: q.mode });
  },
  switchMode(e) {
    if (!this.data.busy) this.setData({ mode: e.currentTarget.dataset.mode, error: "" });
  },
  input(e) {
    this.setData({ text: e.detail.value });
  },
  preset(e) {
    if (this.data.busy) return;
    const p = presets.find((p) => p.id === e.currentTarget.dataset.id);
    this.setData({ mode: p.mode, text: p.content, error: "" });
  },
  clear() {
    if (!this.data.busy) this.setData({ text: "", image: "", error: "" });
  },
  choose() {
    if (this.data.busy) return;
    wx.chooseMedia({
      count: 1,
      mediaType: ["image"],
      sizeType: ["compressed"],
      success: (r) => {
        const f = r.tempFiles[0];
        if (f.size > 6 * 1024 * 1024) {
          this.setData({ error: "请选择不超过 6MB 的图片" });
          return;
        }
        this.setData({ image: f.tempFilePath, error: "" });
      },
      fail: (e) => {
        if (!e.errMsg.includes("cancel")) fail(this, new Error("无法选择图片，请检查相册权限"));
      },
    });
  },
  async scan() {
    if (this.data.busy) return;
    this.setData({ busy: true, error: "" });
    try {
      const data = { mode: this.data.mode, text: this.data.text.trim() };
      if (data.mode === "ocr") {
        if (!this.data.image) throw new Error("请先选择聊天截图");
        data.imageBase64 = await new Promise((resolve, reject) =>
          wx.getFileSystemManager().readFile({
            filePath: this.data.image,
            encoding: "base64",
            success: (r) => resolve(r.data),
            fail: () => reject(new Error("无法读取图片")),
          }),
        );
        data.imageMimeType = data.imageBase64.startsWith("iVBOR")
          ? "image/png"
          : data.imageBase64.startsWith("UklGR")
            ? "image/webp"
            : "image/jpeg";
      } else if (!data.text) throw new Error("请输入需要检测的内容");
      const result = await api.scan(data);
      result.imagePreview = this.data.mode === "ocr" ? this.data.image : "";
      getApp().globalData.latestScan = result;
      this.setData({ busy: false });
      wx.navigateTo({ url: "/pages/result/index" });
    } catch (e) {
      fail(this, e);
    }
  },
});
