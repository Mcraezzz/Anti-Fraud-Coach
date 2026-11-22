const { go } = require("../../utils/page");
function parts(source, highlights) {
  const matches = [];
  highlights.forEach((h, i) => {
    const start = source.indexOf(h.quote),
      end = start + h.quote.length;
    if (start >= 0 && !matches.some((m) => start < m.end && end > m.start))
      matches.push({ start, end, index: i });
  });
  matches.sort((a, b) => a.start - b.start);
  let pos = 0;
  const result = [];
  matches.forEach((m) => {
    if (m.start > pos) result.push({ text: source.slice(pos, m.start), index: -1 });
    result.push({ text: source.slice(m.start, m.end), index: m.index });
    pos = m.end;
  });
  if (pos < source.length) result.push({ text: source.slice(pos), index: -1 });
  return result.map((part, key) => ({ ...part, key }));
}
Page({
  back: require("../../utils/page").back,
  data: { result: null, parts: [], selected: 0, selectedHighlight: null },
  go,
  onLoad() {
    const latest = getApp().globalData.latestScan;
    this.setData({
      scenarioTitle: latest
        ? {
            1: "虚假兼职",
            2: "刷单返利",
            3: "冒充客服",
            4: "游戏交易诈骗",
            5: "校园贷/套路贷",
            6: "冒充熟人",
          }[latest.recommendedScenarioId]
        : "情景",
    });
    const result = getApp().globalData.latestScan;
    if (result)
      this.setData({
        result,
        parts: parts(result.extractedText, result.highlights),
        selectedHighlight: result.highlights[0] || null,
        riskLabel: { high: "高风险", medium: "中风险", low: "低风险" }[result.riskLevel],
      });
  },
  select(e) {
    const selected = Number(e.currentTarget.dataset.index);
    if (selected >= 0)
      this.setData({ selected, selectedHighlight: this.data.result.highlights[selected] });
  },
});
