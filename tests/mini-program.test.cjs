const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const { createRequire } = require('node:module')
const { analyzeText } = require('../utils/risk')
const root = path.resolve(__dirname, '..')

function loadPage(relative, wx = {}) {
  let page
  let timer
  const filename = path.join(root, relative)
  const sandbox = {
    require: createRequire(filename), wx,
    Page(value) { page = value },
    setTimeout(fn) { timer = fn; return 1 },
    clearTimeout() { timer = null }
  }
  vm.runInNewContext(fs.readFileSync(filename, 'utf8'), sandbox)
  page.setData = patch => Object.assign(page.data, patch)
  return { page, runTimer() { if (timer) { const fn = timer; timer = null; fn() } } }
}

test('empty, non-text and excessive input is rejected', () => {
  for (const value of ['', '   ', null, {}, 'a'.repeat(801)]) {
    assert.throws(() => analyzeText(value))
  }
  assert.equal(analyzeText('a'.repeat(800)).count, 0)
})

test('different inputs produce different evidence without retaining personal values', () => {
  const result = analyzeText('先垫付保证金，马上提供验证码 123456，联系 13800138000')
  assert.equal(result.count, 3)
  assert.match(result.evidence, /保证金/)
  assert.doesNotMatch(JSON.stringify(result), /123456|13800138000/)
  assert.equal(analyzeText('明天学校图书馆见').count, 0)
  assert.match(analyzeText('hello').explanation, /未命中不代表安全/)
})

test('case-insensitive matching and repeated words do not inflate counts', () => {
  assert.equal(analyzeText('PASSWORD password Password').count, 1)
})

test('invalid type falls back, empty submission and OCR cannot navigate', () => {
  const { page, runTimer } = loadPage('pages/detect/index.js', { navigateTo() { assert.fail('unexpected navigation') } })
  page.onLoad({ type: 'invalid' })
  assert.equal(page.data.activeType, 'text')
  page.startScan()
  assert.match(page.data.error, /请输入/)
  page.switchType({ currentTarget: { dataset: { type: 'image' } } })
  page.startScan()
  assert.match(page.data.error, /OCR/)
  runTimer()
})

test('double tap navigates once and transfers only analysis results', () => {
  let calls = 0
  let transferred
  const { page, runTimer } = loadPage('pages/detect/index.js', {
    navigateTo(options) {
      calls++
      options.success({ eventChannel: { emit(name, value) { transferred = value } } })
      options.complete()
    }
  })
  page.onInput({ detail: { value: '先垫付押金' } })
  page.startScan()
  page.startScan()
  runTimer()
  assert.equal(calls, 1)
  assert.equal(transferred.count, 1)
  assert.equal(page.data.scanning, false)
})

for (const lifecycle of ['onHide', 'onUnload']) {
  test(lifecycle + ' cancels pending navigation', () => {
    const { page, runTimer } = loadPage('pages/detect/index.js', { navigateTo() { assert.fail('late navigation') } })
    page.onInput({ detail: { value: 'hello' } })
    page.startScan()
    page[lifecycle]()
    runTimer()
  })
}

test('navigation failure clears loading and permits retry', () => {
  const { page, runTimer } = loadPage('pages/detect/index.js', {
    navigateTo(options) { options.fail(); options.complete() }
  })
  page.onInput({ detail: { value: 'hello' } })
  page.startScan()
  runTimer()
  assert.equal(page.data.scanning, false)
  assert.match(page.data.error, /重试/)
  page.startScan()
  assert.equal(page.data.scanning, true)
})

test('switching input types clears stale content and errors', () => {
  const { page } = loadPage('pages/detect/index.js')
  page.setData({ inputText: 'old', error: 'old' })
  page.switchType({ currentTarget: { dataset: { type: 'sms' } } })
  assert.equal(page.data.inputText, '')
  assert.equal(page.data.error, '')
})

test('result page starts empty, receives current result and unregisters its listener', () => {
  const { page } = loadPage('pages/result/index.js')
  let listener
  let removed
  page.getOpenerEventChannel = () => ({
    on(name, fn) { listener = fn }, off(name, fn) { removed = fn }
  })
  page.onLoad()
  assert.equal(page.data.hasResult, false)
  listener(analyzeText('验证码'))
  assert.equal(page.data.hasResult, true)
  assert.equal(page.data.count, 1)
  page.onUnload()
  assert.equal(removed, listener)
})

test('custom tabs reset the stack, ignore double taps and recover after failure', () => {
  let calls = 0
  let pending
  const sandbox = {
    module: { exports: {} },
    getCurrentPages: () => [{ route: 'pages/home/index' }],
    wx: { reLaunch(options) { calls++; pending = options }, showToast() {} }
  }
  vm.runInNewContext(fs.readFileSync(path.join(root, 'utils/tabs.js'), 'utf8'), sandbox)
  const { goTab } = sandbox.module.exports
  goTab(99); goTab(0)
  assert.equal(calls, 0)
  goTab(1); goTab(1)
  assert.equal(calls, 1)
  assert.equal(pending.url, '/pages/qa/index')
  pending.fail(); pending.complete()
  goTab(2)
  assert.equal(calls, 2)
})

test('all mini-program scripts parse and registered pages have complete source files', () => {
  function walk(dir) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const file = path.join(dir, entry.name)
      if (entry.isDirectory()) walk(file)
      else if (file.endsWith('.js')) new vm.Script(fs.readFileSync(file, 'utf8'), { filename: file })
      else if (file.endsWith('.json')) JSON.parse(fs.readFileSync(file, 'utf8'))
    }
  }
  for (const dir of ['pages', 'components', 'utils']) walk(path.join(root, dir))
  const app = JSON.parse(fs.readFileSync(path.join(root, 'app.json'), 'utf8'))
  for (const page of app.pages) {
    for (const ext of ['.js', '.json', '.wxml', '.wxss']) assert.ok(fs.existsSync(path.join(root, page + ext)))
  }
})
