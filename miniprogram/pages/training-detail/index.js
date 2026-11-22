const api = require("../../utils/api");
const { go, fail } = require("../../utils/page");
Page({
  back: require("../../utils/page").back,
  openHandbook() {
    this.setData({ showHandbook: true });
  },
  closeHandbook() {
    this.setData({ showHandbook: false });
  },
  data: {
    scenario: null,
    turn: null,
    step: 0,
    answers: [],
    selection: "",
    result: null,
    loading: true,
    busy: false,
    error: "",
  },
  go,
  onLoad(q) {
    this.id = q.id || "1";
    this.load();
  },
  async load() {
    this.setData({ loading: true, error: "" });
    try {
      const scenarios = await api.scenarios();
      const scenario = scenarios.find((s) => s.id === this.id);
      if (!scenario) throw new Error("找不到这个训练情景");
      this.setData({ scenario, turn: scenario.turns[0], loading: false });
    } catch (e) {
      fail(this, e);
    }
  },
  choose(e) {
    if (!this.data.busy && !this.data.result)
      this.setData({ selection: e.currentTarget.dataset.id }, () => this.submit());
  },
  async submit() {
    if (!this.data.selection || this.data.busy) return;
    const answers = this.data.answers.concat(this.data.selection);
    if (this.data.step + 1 < this.data.scenario.turns.length) {
      const step = this.data.step + 1;
      this.setData({ answers, step, turn: this.data.scenario.turns[step], selection: "" });
      return;
    }
    this.setData({ busy: true, error: "" });
    try {
      const result = await api.train(this.id, answers);
      this.setData({ result, busy: false });
      wx.pageScrollTo({ scrollTop: 99999, duration: 0 });
    } catch (e) {
      fail(this, e);
    }
  },
  reset() {
    this.setData({
      step: 0,
      turn: this.data.scenario.turns[0],
      answers: [],
      selection: "",
      result: null,
      error: "",
    });
    wx.pageScrollTo({ scrollTop: 0, duration: 0 });
  },
});
