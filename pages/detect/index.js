const { tabbarList, goTab } = require('../../utils/tabs')

Page({
  data: {
    currentTab: 0,
    tabbarList,
    activeType: 'text',
    scanning: false,
    tabs: [
      { key: 'text', label: '文本识别' },
      { key: 'image', label: '截图 OCR' },
      { key: 'link', label: '链接检测' },
      { key: 'sms', label: '短信分析' }
    ],
    steps: [
      { label: '提取文本', done: false },
      { label: '识别风险信号', done: false },
      { label: '生成处置建议', done: false }
    ]
  },

  onLoad(options) {
    this.setData({ activeType: options.type || 'text' })
  },

  onTabChange(event) {
    goTab(event.detail.index)
  },

  switchType(event) {
    this.setData({ activeType: event.currentTarget.dataset.type })
  },

  startScan() {
    this.setData({
      scanning: true,
      steps: [
        { label: '提取文本', done: true },
        { label: '识别风险信号', done: true },
        { label: '生成处置建议', done: false }
      ]
    })
    setTimeout(() => {
      wx.navigateTo({ url: '/pages/result/index', routeType: 'afc-card' })
      this.setData({ scanning: false })
    }, 700)
  }
})
