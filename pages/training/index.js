const { tabbarList, goTab } = require('../../utils/tabs')

Page({
  data: {
    currentTab: 2,
    tabbarList,
    scenarios: [
      { title: '刷单返利', level: '高频', done: 80, tone: 'red' },
      { title: '冒充客服', level: '中等', done: 60, tone: 'amber' },
      { title: '虚假兼职', level: '高频', done: 45, tone: 'red' },
      { title: '校园贷', level: '进阶', done: 30, tone: 'blue' },
      { title: '游戏交易', level: '常见', done: 55, tone: 'amber' },
      { title: '冒充熟人', level: '基础', done: 70, tone: 'blue' }
    ]
  },
  onTabChange(event) {
    goTab(event.detail.index)
  }
})
