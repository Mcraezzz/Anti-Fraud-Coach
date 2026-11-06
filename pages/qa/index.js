const { tabbarList, goTab } = require('../../utils/tabs')

Page({
  data: {
    currentTab: 1,
    tabbarList,
    prompts: ['兼职要求先交押金靠谱吗？', '客服让我下载会议 App 怎么办？', '游戏账号私下交易安全吗？']
  },
  onTabChange(event) {
    goTab(event.detail.index)
  }
})
