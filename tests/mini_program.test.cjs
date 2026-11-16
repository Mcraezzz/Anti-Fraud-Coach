const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const path = require('node:path')

function createPage() {
  let definition
  let nextId = 0
  const timers = new Map()
  const navigations = []
  const sandbox = {
    require: () => ({ tabbarList: [], goTab() {} }),
    Page: value => { definition = value },
    setTimeout: fn => { timers.set(++nextId, fn); return nextId },
    clearTimeout: id => timers.delete(id),
    wx: { navigateTo: options => navigations.push(options) }
  }
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../pages/detect/index.js'), 'utf8'), sandbox)
  const page = { ...definition, data: structuredClone(definition.data), setData(value) { Object.assign(this.data, value) } }
  const tick = () => {
    const callbacks = [...timers.values()]
    timers.clear()
    callbacks.forEach(fn => fn())
  }
  return { page, timers, navigations, tick }
}

test('repeated taps produce one navigation, including while navigation is pending', () => {
  const { page, timers, navigations, tick } = createPage()
  page.startScan()
  page.startScan()
  assert.equal(timers.size, 1)
  tick()
  page.startScan()
  assert.equal(timers.size, 0)
  assert.equal(navigations.length, 1)
  navigations[0].complete()
  assert.equal(page.data.scanning, false)
  page.startScan()
  assert.equal(timers.size, 1)
})

for (const lifecycle of ['onHide', 'onUnload']) {
  test(`${lifecycle} cancels pending navigation`, () => {
    const { page, navigations, tick } = createPage()
    page.startScan()
    page[lifecycle]()
    tick()
    assert.equal(navigations.length, 0)
  })
}

test('switching input mode cancels the previous scan', () => {
  const { page, navigations, tick } = createPage()
  page.startScan()
  page.switchType({ currentTarget: { dataset: { type: 'image' } } })
  tick()
  assert.equal(navigations.length, 0)
  assert.equal(page.data.activeType, 'image')
  assert.equal(page.data.scanning, false)
})

test('unknown launch modes fall back to text', () => {
  const { page } = createPage()
  page.onLoad({ type: 'invalid' })
  assert.equal(page.data.activeType, 'text')
  page.onLoad({ type: 'sms' })
  assert.equal(page.data.activeType, 'sms')
  page.onLoad()
  assert.equal(page.data.activeType, 'text')
})
