const api = require("../../utils/api");
const { go, fail } = require("../../utils/page");
Page({
  closeHandbook() {
    this.setData({ handbook: null });
  },
  data: {
    scenarios: [],
    filtered: [],
    filter: 0,
    report: null,
    loading: true,
    error: "",
    handbook: null,
    filters: [
      { id: 0, label: "全部" },
      { id: 1, label: "入门" },
      { id: 2, label: "进阶" },
      { id: 3, label: "高阶" },
    ],
  },
  go,
  onShow() {
    this.load();
  },
  async load() {
    this.setData({ loading: true, error: "" });
    try {
      const [scenarios, report] = await Promise.all([api.scenarios(), api.report()]);
      const rows = scenarios.map((s) => ({
        ...s,
        level: ["", "入门", "进阶", "高阶"][s.difficulty],
        completed: !!(report.progress[s.id] && report.progress[s.id].completed),
        bestScore: report.progress[s.id] ? report.progress[s.id].bestScore : null,
      }));
      this.setData({ scenarios: rows, report, loading: false });
      this.filterRows();
    } catch (e) {
      fail(this, e);
    }
  },
  filter(e) {
    this.setData({ filter: Number(e.currentTarget.dataset.id) });
    this.filterRows();
  },
  filterRows() {
    this.setData({
      filtered: this.data.scenarios.filter(
        (s) => !this.data.filter || s.difficulty === this.data.filter,
      ),
    });
  },
  handbook(e) {
    const s = this.data.scenarios.find((s) => s.id === e.currentTarget.dataset.id);
    this.setData({
      handbook:
        this.data.handbook && this.data.handbook.title === s.handbook.title ? null : s.handbook,
    });
  },
});
