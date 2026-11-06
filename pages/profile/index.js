const { tabbarList, goTab } = require('../../utils/tabs')

Page({
  data: {
    currentTab: 4,
    tabbarList,
    settings: [
      { title: '隐私与脱敏', desc: '自动脱敏、最小化存储、权限控制' },
      { title: '知识库版本', desc: '反诈条目 v1.0，案例库已同步' },
      { title: '训练记录', desc: '查看历史得分与漏识别风险点' }
    ]
  },
  onTabChange(event) {
    goTab(event.detail.index)
  },
  openAdmin() {
    wx.navigateTo({ url: '/pages/admin/index', routeType: 'afc-card' })
  }
})
