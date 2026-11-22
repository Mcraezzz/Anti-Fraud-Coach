const api = require("../../utils/api");
const { fail, back } = require("../../utils/page");
Page({
  data: {
    text: "",
    messages: [
      {
        id: "welcome",
        role: "assistant",
        content:
          "同学你好，我是你的 AI 反诈顾问。你在兼职、网购、游戏交易或熟人借款中遇到可疑话术和链接，都可以直接发给我核实。\n\n回答基于校园反诈知识库，仅作安全辅助判断，不作法律定性。",
        references: [{ title: "校园常见电信网络诈骗防范指南", category: "初始指引" }],
      },
    ],
    busy: false,
    error: "",
    scrollTarget: "",
    prompts: [
      "闲鱼买家让我加微信或QQ私下转账安全吗？",
      "兼职群说先交80元服装费/保证金是不是骗局？",
      "自称快递客服让开屏幕共享理赔怎么办？",
      "室友QQ突然发消息借钱，怎么快速核实？",
    ],
  },
  back,
  input(e) {
    this.setData({ text: e.detail.value });
  },
  prompt(e) {
    if (!this.data.busy) {
      this.setData({ text: e.currentTarget.dataset.text });
      this.send();
    }
  },
  async send() {
    if (this.data.busy) return;
    const question = this.data.text.trim();
    if (!question) return;
    const messages = this.data.messages.concat({
      id: "user-" + Date.now(),
      role: "user",
      content: question,
    });
    this.setData({ messages, text: "", busy: true, error: "", scrollTarget: "" }, () =>
      this.setData({ scrollTarget: "conversation-end" }),
    );
    try {
      // The existing knowledge service answers standalone questions.
      // Keep history on screen without resending private or oversized answers.
      const result = await api.qa([{ role: "user", content: question }]);
      this.setData(
        {
          messages: messages.concat({
            id: "answer-" + Date.now(),
            role: "assistant",
            content: result.answer,
            references: result.references,
            engine: result.engine,
          }),
          busy: false,
          scrollTarget: "",
        },
        () => this.setData({ scrollTarget: "conversation-end" }),
      );
    } catch (e) {
      this.setData({ messages: this.data.messages.slice(0, -1), text: question });
      fail(this, e);
    }
  },
});
