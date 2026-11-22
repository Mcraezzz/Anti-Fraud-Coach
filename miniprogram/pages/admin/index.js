const api = require("../../utils/api");
const { fail, date } = require("../../utils/page");
Page({
  back: require("../../utils/page").back,
  data: { username: "", password: "", report: null, busy: false, error: "" },
  input(e) {
    this.setData({ [e.currentTarget.dataset.field]: e.detail.value });
  },
  async load() {
    if (this.data.busy) return;
    this.setData({ busy: true, error: "" });
    try {
      const report = await api.admin(this.data.username, this.data.password);
      report.distribution = report.distribution.map((x) => ({
        ...x,
        ratio: report.scanCount ? Math.round((x.count / report.scanCount) * 100) : 0,
      }));
      report.recent = report.recent.map((e) => ({ ...e, date: date(e.time) }));
      this.setData({ report, busy: false, password: "" });
    } catch (e) {
      fail(this, e);
    }
  },
});
