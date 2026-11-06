let registered = false

function makeCurveAnimation(worklet, animation, animationStatus, curve, reverseCurve) {
  const { derived } = worklet
  return derived(() => {
    'worklet'
    const useForwardCurve = !reverseCurve || animationStatus.value !== 2
    const activeCurve = useForwardCurve ? curve : reverseCurve
    const t = animation.value
    if (!activeCurve || t === 0 || t === 1) return t
    return activeCurve(t)
  })
}

function registerRoutes() {
  if (registered || !wx.router || !wx.worklet) return

  registered = true
  const { Easing } = wx.worklet
  const curves = {
    fastOutSlowIn: Easing.cubicBezier(0.4, 0, 0.2, 1),
    linearToEaseOut: Easing.cubicBezier(0.35, 0.91, 0.33, 0.97),
    easeInToLinear: Easing.cubicBezier(0.67, 0.03, 0.65, 0.09)
  }

  wx.router.addRouteBuilder('afc-card', function AfcCardRouteBuilder(routeContext) {
    const {
      primaryAnimation,
      primaryAnimationStatus,
      secondaryAnimation,
      secondaryAnimationStatus
    } = routeContext
    const { screenHeight } = wx.getWindowInfo()

    const curvedPrimary = makeCurveAnimation(
      wx.worklet,
      primaryAnimation,
      primaryAnimationStatus,
      curves.linearToEaseOut,
      curves.easeInToLinear
    )
    const curvedSecondary = makeCurveAnimation(
      wx.worklet,
      secondaryAnimation,
      secondaryAnimationStatus,
      curves.fastOutSlowIn
    )

    const handlePrimaryAnimation = () => {
      'worklet'
      const t = curvedPrimary.value
      const y = 40 * (1 - t)
      const scale = 0.98 + 0.02 * t
      return {
        opacity: t,
        transform: `translateY(${y}px) scale(${scale})`
      }
    }

    const handleSecondaryAnimation = () => {
      'worklet'
      const t = curvedSecondary.value
      const y = screenHeight * 0.018 * t
      return {
        opacity: 1 - 0.12 * t,
        transform: `translateY(${y}px) scale(${1 - 0.035 * t})`
      }
    }

    return {
      opaque: false,
      popGestureDirection: 'horizontal',
      fullscreenDrag: true,
      handlePrimaryAnimation,
      handleSecondaryAnimation
    }
  })
}

module.exports = {
  registerRoutes
}
