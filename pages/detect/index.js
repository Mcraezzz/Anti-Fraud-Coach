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

  onLoad(options = {}) {
    const activeType = this.data.tabs.some(tab => tab.key === options.type) ? options.type : 'text'
    this.setData({ activeType })
  },

  cancelScan() {
    if (this._scanTimer != null) clearTimeout(this._scanTimer)
    this._scanTimer = null
    this.setData({ scanning: false })
  },

  onHide() {
    this.cancelScan()
  },

  onUnload() {
    if (this._scanTimer != null) clearTimeout(this._scanTimer)
    this._scanTimer = null
  },

  onTabChange(event) {
    goTab(event.detail.index)
  },

  switchType(event) {
    this.cancelScan()
    this.setData({ activeType: event.currentTarget.dataset.type })
  },

  startScan() {
    if (this.data.scanning) return
    this.setData({
      scanning: true,
      steps: [
        { label: '提取文本', done: true },
        { label: '识别风险信号', done: true },
        { label: '生成处置建议', done: false }
      ]
    })
    this._scanTimer = setTimeout(() => {
      this._scanTimer = null
      wx.navigateTo({
        url: '/pages/result/index',
        routeType: 'afc-card',
        complete: () => this.setData({ scanning: false })
      })
    }, 700)
  }
})
