const { tabbarList, goTab } = require('../../utils/tabs')
const { analyzeText } = require('../../utils/risk')

Page({
  data: {
    currentTab: 0,
    tabbarList,
    activeType: 'text',
    inputText: '',
    scanning: false,
    error: '',
    tabs: [
      { key: 'text', label: '文本识别' },
      { key: 'image', label: '截图 OCR' },
      { key: 'link', label: '链接检测' },
      { key: 'sms', label: '短信分析' }
    ]
  },

  onLoad(options = {}) {
    const activeType = this.data.tabs.some(tab => tab.key === options.type) ? options.type : 'text'
    this.setData({ activeType })
  },
  onTabChange(event) { goTab(event.detail.index) },
  switchType(event) {
    if (this.data.scanning && this._scanTimer == null) return
    const activeType = event.currentTarget.dataset.type
    if (this.data.tabs.some(tab => tab.key === activeType)) {
      this.cancelScan()
      this.setData({ activeType, inputText: '', error: '', scanning: false })
    }
  },
  onInput(event) { this.setData({ inputText: event.detail.value, error: '' }) },
  startScan() {
    if (this.data.scanning) return
    if (this.data.activeType === 'image') {
      this.setData({ error: 'OCR 尚未接入，请切换到文本并粘贴截图中的文字。' })
      return
    }
    let result
    try {
      result = analyzeText(this.data.inputText)
    } catch (error) {
      this.setData({ error: error.message })
      return
    }
    this.setData({ scanning: true, error: '' })
    this._scanTimer = setTimeout(() => {
      this._scanTimer = null
      wx.navigateTo({
        url: '/pages/result/index',
        success: response => response.eventChannel.emit('analysis', result),
        fail: () => this.setData({ error: '无法打开结果页，请重试。' }),
        complete: () => this.setData({ scanning: false })
      })
    }, 200)
  },
  onHide() {
    this.cancelScan()
    this.setData({ scanning: false })
  },
  onUnload() { this.cancelScan() },
  cancelScan() {
    if (this._scanTimer != null) clearTimeout(this._scanTimer)
    this._scanTimer = null
  }
})
