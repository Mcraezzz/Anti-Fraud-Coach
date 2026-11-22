Component({
  properties: { active: String },
  data: {
    items: [
      { id: "home", label: "首页", icon: "house" },
      { id: "detect", label: "识别", icon: "scan" },
      { id: "qa", label: "问答", icon: "message-square" },
      { id: "training", label: "训练", icon: "target" },
      { id: "report", label: "报告", icon: "chart-no-axes-column" },
      { id: "profile", label: "我的", icon: "user" },
    ],
  },
  methods: {
    open(e) {
      const id = e.currentTarget.dataset.id;
      if (id !== this.data.active) wx.reLaunch({ url: "/pages/" + id + "/index" });
    },
  },
});
