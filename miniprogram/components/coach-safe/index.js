Component({
  properties: { dark: Boolean },
  data: { height: 64 },
  lifetimes: {
    attached() {
      const s = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
      const menu = wx.getMenuButtonBoundingClientRect();
      this.setData({ height: Math.max(s.statusBarHeight + 44, menu.bottom + 8) });
    },
  },
});
