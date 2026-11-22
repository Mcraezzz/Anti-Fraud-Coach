const pendingSessions = new Map();
function base() {
  return (wx.getStorageSync("coachApiBase") || "http://127.0.0.1:8000").replace(/\/$/, "");
}
function key(server = base()) {
  return "coachToken:" + server;
}
function error(data) {
  if (data && typeof data.detail === "string") return data.detail;
  if (data && Array.isArray(data.detail)) return data.detail.map((x) => x.msg).join("；");
  return (data && data.error) || "请求失败，请稍后重试";
}
function raw(path, method, data, token, headers, server = base()) {
  return new Promise((resolve, reject) =>
    wx.request({
      url: server + path,
      method: method || "GET",
      data,
      timeout: 180000,
      header: {
        "content-type": "application/json",
        ...(token ? { Authorization: "Bearer " + token } : {}),
        ...headers,
      },
      success: (r) =>
        r.statusCode >= 200 && r.statusCode < 300
          ? resolve(r.data)
          : reject(Object.assign(new Error(error(r.data)), { status: r.statusCode })),
      fail: (e) =>
        reject(
          new Error(
            e.errMsg && e.errMsg.includes("timeout")
              ? "本地模型处理超时，请稍后重试"
              : "无法连接后端，请检查服务地址和网络",
          ),
        ),
    }),
  );
}
async function session(server = base()) {
  const token = wx.getStorageSync(key(server));
  if (token) return token;
  if (!pendingSessions.has(server)) {
    const pending = raw("/api/coach/session", "POST", {}, undefined, undefined, server)
      .then((r) => {
        // A reset invalidates any session creation already in flight.
        if (pendingSessions.get(server) !== pending)
          throw new Error("设备会话已重置，请重新操作");
        wx.setStorageSync(key(server), r.token);
        return r.token;
      })
      .finally(() => {
        if (pendingSessions.get(server) === pending) pendingSessions.delete(server);
      });
    pendingSessions.set(server, pending);
  }
  return pendingSessions.get(server);
}
async function request(path, method, data) {
  const server = base();
  return raw("/api/coach" + path, method, data, await session(server), undefined, server);
}
module.exports = {
  base,
  request,
  health: () => raw("/api/coach/health"),
  profile: () => request("/profile"),
  saveProfile: (data) => request("/profile", "PATCH", data),
  scan: (data) => request("/scan", "POST", data),
  history: () => request("/history"),
  clearHistory: () => request("/history", "DELETE"),
  qa: (messages) => request("/qa", "POST", { messages }),
  scenarios: () => request("/scenarios"),
  train: (id, answers) => request("/training/" + id, "POST", { answers }),
  report: () => request("/report"),
  setBase(value) {
    wx.setStorageSync("coachApiBase", value);
  },
  resetSession() {
    wx.removeStorageSync(key());
    pendingSessions.delete(base());
  },
  async admin(username, password) {
    const server = base();
    const login = await raw("/api/auth/login", "POST", { username, password }, undefined, undefined, server);
    return raw("/api/coach/admin", "GET", undefined, await session(server), {
      "X-Admin-Token": login.token,
    }, server);
  },
};

module.exports.resetTraining = () => request("/training", "DELETE");
