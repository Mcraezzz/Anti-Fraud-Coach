const { tabbarList, goTab } = require('../../utils/tabs')

Page({
  data: {
    currentTab: 0,
    tabbarList,
    scanEntrances: [
      { type: 'text', title: '粘贴文本', desc: '聊天话术识别', icon: 'text' },
      { type: 'image', title: '上传截图', desc: 'OCR 风险扫描', icon: 'image' },
      { type: 'link', title: '检测链接', desc: '网址与跳转风险', icon: 'link' },
      { type: 'sms', title: '分析短信', desc: '号码与诱导语', icon: 'sms' }
    ],
    quickFeatures: [
      { title: 'AI 反诈问答', desc: '基于知识库回答', tab: 1 },
      { title: '情景训练', desc: '六类校园骗局', tab: 2 },
      { title: '能力报告', desc: '雷达图与易错项', tab: 3 },
      { title: '校园案例库', desc: '相似案例追溯', tab: 1 }
    ]
  },

  onTabChange(event) {
    goTab(event.detail.index)
  },

  goDetect(event) {
    wx.navigateTo({
      url: `/pages/detect/index?type=${event.currentTarget.dataset.type || 'text'}`,
      routeType: 'afc-card'
    })
  },

  goFeature(event) {
    goTab(Number(event.currentTarget.dataset.tab))
  }
})
