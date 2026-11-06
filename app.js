const { registerRoutes } = require('./utils/routes')

App({
  globalData: {
    brandName: 'Anti-Fraud Coach',
    theme: 'light'
  },

  onLaunch() {
    registerRoutes()
  }
})
