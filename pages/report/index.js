const { tabbarList, goTab } = require('../../utils/tabs')

Page({
  data: {
    currentTab: 3,
    tabbarList,
    weakTypes: ['虚假兼职', '冒充客服', '游戏交易'],
    abilities: [
      { label: '金钱诱导识别', value: 86 },
      { label: '身份核验意识', value: 72 },
      { label: '链接风险判断', value: 78 },
      { label: '隐私保护意识', value: 88 },
      { label: '证据保存意识', value: 67 },
      { label: '求助止损意识', value: 74 }
    ]
  },
  onTabChange(event) {
    goTab(event.detail.index)
  }
})
