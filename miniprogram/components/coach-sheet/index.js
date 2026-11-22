Component({
  properties: { open: Boolean, title: String, subtitle: String },
  data: { motion: true },
  observers: {
    open(value) {
      if (value) this.setData({ motion: wx.getStorageSync("coachMotion") !== false });
    },
  },
  methods: {
    close() {
      this.triggerEvent("close");
    },
    noop() {},
  },
});
