const { goTab } = require('../../utils/tabs')

Page({
  data: {
    hasResult: false,
    signals: [],
    actions: ['暂停转账或付款', '不提供验证码、身份证、银行卡', '不下载陌生 App，不进行屏幕共享', '保存聊天、链接、转账凭证', '向辅导员、平台客服或公安机关核实']
  },
  onLoad() {
    const channel = this.getOpenerEventChannel()
    this._channel = channel
    this._onAnalysis = result => this.setData({ ...result, hasResult: true })
    if (channel && channel.on) channel.on('analysis', this._onAnalysis)
  },
  onUnload() {
    if (this._channel && this._channel.off) this._channel.off('analysis', this._onAnalysis)
  },
  goTraining() { goTab(2) },
  goDetect() { wx.redirectTo({ url: '/pages/detect/index' }) }
})
