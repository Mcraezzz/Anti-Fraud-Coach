const api = require("../../utils/api");

const DRAFT_KEY = "trainingDraftAnswers";

function normalizeTrainingResult(raw) {
  const result = raw || {};
  return {
    ...result,
    score: result.score != null ? result.score : 0,
    correct: result.correct != null ? result.correct : 0,
    total: result.total != null ? result.total : 0,
    weak_types: Array.isArray(result.weak_types) ? result.weak_types : [],
    feedback: Array.isArray(result.feedback) ? result.feedback : []
  };
}

function buildProgress(questions, answers) {
  const total = questions.length;
  const answered = questions.filter((item) => answers[item.id]).length;
  const percent = total ? Math.round((answered / total) * 100) : 0;
  return {
    answeredCount: answered,
    unansweredCount: Math.max(0, total - answered),
    answerProgress: percent,
    canSubmit: total > 0 && answered === total
  };
}

Page({
  data: {
    questions: [],
    answers: {},
    result: null,
    taskTarget: 3,
    taskStatus: "待加载",
    answeredCount: 0,
    unansweredCount: 0,
    answerProgress: 0,
    canSubmit: false,
    submitAttempted: false,
    loading: false,
    submitting: false,
    error: ""
  },

  onLoad() {
    this.loadQuestions();
  },

  async loadQuestions() {
    this.setData({ loading: true, error: "" });
    try {
      const questions = await api.getQuestions();
      const normalizedQuestions = Array.isArray(questions) ? questions : [];
      const draft = wx.getStorageSync(DRAFT_KEY) || {};
      const answers = {};
      normalizedQuestions.forEach((question) => {
        if (draft[question.id]) {
          answers[question.id] = draft[question.id];
        }
      });
      this.setData({
        questions: normalizedQuestions,
        answers,
        result: null,
        submitAttempted: false,
        taskTarget: normalizedQuestions.length ? Math.min(3, normalizedQuestions.length) : 3,
        taskStatus: normalizedQuestions.length ? `已加载 ${normalizedQuestions.length} 题` : "待加载",
        ...buildProgress(normalizedQuestions, answers)
      });
    } catch (err) {
      this.setData({ error: api.getErrorMessage(err, "训练题库未连接，请先启动后端服务。") });
    } finally {
      this.setData({ loading: false });
    }
  },

  selectOption(event) {
    const { qid, oid } = event.currentTarget.dataset;
    const answers = { ...this.data.answers, [qid]: oid };
    wx.setStorageSync(DRAFT_KEY, answers);
    this.setData({
      answers,
      submitAttempted: false,
      ...buildProgress(this.data.questions, answers)
    });
  },

  async submit() {
    if (!this.data.questions.length || this.data.submitting) {
      return;
    }
    const progress = buildProgress(this.data.questions, this.data.answers);
    if (progress.unansweredCount > 0) {
      this.setData({ submitAttempted: true, ...progress });
      wx.showToast({ title: `还有 ${progress.unansweredCount} 题未答`, icon: "none" });
      const firstMissing = this.data.questions.find((item) => !this.data.answers[item.id]);
      if (firstMissing) {
        wx.pageScrollTo({ selector: `#question-${firstMissing.id}`, duration: 200 });
      }
      return;
    }
    this.setData({ submitting: true, error: "" });
    try {
      const result = await api.submitTraining(this.data.answers);
      this.setData({ result: normalizeTrainingResult(result) });
      wx.removeStorageSync(DRAFT_KEY);
      wx.pageScrollTo({ scrollTop: 0, duration: 200 });
    } catch (err) {
      this.setData({ error: api.getErrorMessage(err, "提交失败，请检查后端服务。") });
    } finally {
      this.setData({ submitting: false });
    }
  },

  async onPullDownRefresh() {
    await this.loadQuestions();
    wx.stopPullDownRefresh();
  }
});
