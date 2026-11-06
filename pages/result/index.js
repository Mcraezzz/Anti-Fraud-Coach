Page({
  data: {
    signals: [
      { label: '金钱诱导', tone: 'red' },
      { label: '紧迫施压', tone: 'amber' },
      { label: '脱离平台', tone: 'red' },
      { label: '隐私索取', tone: 'red' }
    ],
    actions: ['暂停转账或付款', '不提供验证码、身份证、银行卡', '不下载陌生 App，不进行屏幕共享', '保存聊天、链接、转账凭证', '向辅导员、平台客服或公安机关核实']
  },
  goTraining() {
    wx.redirectTo({ url: '/pages/training/index' })
  }
})
