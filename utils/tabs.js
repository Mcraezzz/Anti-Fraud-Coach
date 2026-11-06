const tabbarList = [
  {
    text: '识别',
    url: '/pages/home/index',
    iconPath: '/assets/tabbar/scan-default.svg',
    selectedIconPath: '/assets/tabbar/scan-active.svg'
  },
  {
    text: '问答',
    url: '/pages/qa/index',
    iconPath: '/assets/tabbar/chat-default.svg',
    selectedIconPath: '/assets/tabbar/chat-active.svg'
  },
  {
    text: '训练',
    url: '/pages/training/index',
    iconPath: '/assets/tabbar/train-default.svg',
    selectedIconPath: '/assets/tabbar/train-active.svg'
  },
  {
    text: '报告',
    url: '/pages/report/index',
    iconPath: '/assets/tabbar/report-default.svg',
    selectedIconPath: '/assets/tabbar/report-active.svg'
  },
  {
    text: '我的',
    url: '/pages/profile/index',
    iconPath: '/assets/tabbar/mine-default.svg',
    selectedIconPath: '/assets/tabbar/mine-active.svg'
  }
]

function goTab(index) {
  const target = tabbarList[index]
  if (!target) return

  const pages = getCurrentPages()
  const current = pages.length ? `/${pages[pages.length - 1].route}` : ''
  if (current === target.url) return

  wx.redirectTo({
    url: target.url
  })
}

module.exports = {
  tabbarList,
  goTab
}
