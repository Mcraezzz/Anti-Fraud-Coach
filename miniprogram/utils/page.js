function go(e) {
  const url = e.currentTarget.dataset.url;
  if (url) wx.navigateTo({ url });
}
function fail(page, error) {
  page.setData({ error: error.message || "操作失败，请重试", loading: false, busy: false });
}
function date(timestamp) {
  const d = new Date(timestamp);
  return (
    [d.getFullYear(), d.getMonth() + 1, d.getDate()].join("/") +
    " " +
    String(d.getHours()).padStart(2, "0") +
    ":" +
    String(d.getMinutes()).padStart(2, "0")
  );
}
module.exports = { go, fail, date };

module.exports.back = function () {
  const pages = getCurrentPages();
  if (pages.length > 1) wx.navigateBack();
  else wx.reLaunch({ url: "/pages/home/index" });
};
