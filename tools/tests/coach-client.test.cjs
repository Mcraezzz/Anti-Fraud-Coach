const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../../miniprogram');

function client() {
  const storage = new Map();
  const calls = [];
  const context = {
    module: { exports: {} },
    wx: {
      getStorageSync: key => storage.get(key),
      setStorageSync: (key, value) => storage.set(key, value),
      removeStorageSync: key => storage.delete(key),
      request: options => calls.push(options),
    },
  };
  vm.runInNewContext(fs.readFileSync(path.join(root, 'utils/api.js'), 'utf8'), context);
  return { api: context.module.exports, storage, calls };
}
const reply = (call, data) => call.success({ statusCode: 200, data });
const flush = () => new Promise(resolve => setImmediate(resolve));

test('parallel requests share a session and never mix servers after an address change', async () => {
  const { api, storage, calls } = client();
  api.setBase('http://server-a');
  const first = api.profile(), report = api.report();
  assert.equal(calls.length, 1);
  api.setBase('http://server-b');
  const second = api.profile();
  assert.equal(calls.length, 2);
  reply(calls[1], { token: 'token-b' });
  reply(calls[0], { token: 'token-a' });
  await flush();
  assert.equal(storage.get('coachToken:http://server-a'), 'token-a');
  assert.equal(storage.get('coachToken:http://server-b'), 'token-b');
  for (const call of calls.slice(2)) {
    assert.equal(call.header.Authorization, call.url.startsWith('http://server-a/') ? 'Bearer token-a' : 'Bearer token-b');
    reply(call, {});
  }
  await Promise.all([first, report, second]);
  assert.equal(calls.filter(c => c.url.startsWith('http://server-a/')).length, 3);
});

test('reset during session creation cannot restore the abandoned token', async () => {
  const { api, storage, calls } = client();
  const old = api.profile();
  const rejected = assert.rejects(old, /会话已重置/);
  api.resetSession();
  const fresh = api.profile();
  reply(calls[0], { token: 'abandoned' });
  await rejected;
  assert.equal(storage.size, 0);
  reply(calls[1], { token: 'fresh' });
  await flush();
  assert.equal(calls[2].header.Authorization, 'Bearer fresh');
  reply(calls[2], {});
  await fresh;
});

test('admin login and dashboard stay on the same server', async () => {
  const { api, calls } = client();
  api.setBase('http://server-a');
  const pending = api.admin('admin', 'test-password');
  api.setBase('http://server-b');
  reply(calls[0], { token: 'admin-a' });
  await flush();
  assert.equal(calls[1].url, 'http://server-a/api/coach/session');
  reply(calls[1], { token: 'device-a' });
  await flush();
  assert.equal(calls[2].url, 'http://server-a/api/coach/admin');
  assert.equal(calls[2].header['X-Admin-Token'], 'admin-a');
  reply(calls[2], {});
  await pending;
});

test('a long earlier answer stays on screen without being uploaded again', async () => {
  let page, submitted;
  vm.runInNewContext(fs.readFileSync(path.join(root, 'pages/qa/index.js'), 'utf8'), {
    Page: value => { page = value; },
    require: name => name.endsWith('/api') ? {
      qa: async messages => { submitted = messages; return { answer: 'new answer', references: [] }; },
    } : { back() {}, fail(_page, error) { throw error; } },
  });
  page.setData = function(value, callback) { Object.assign(this.data, value); if (callback) callback(); };
  page.data.messages.push({ id: 'previous', role: 'assistant', content: 'x'.repeat(5000) });
  page.data.text = '新的问题';
  await page.send();
  assert.equal(submitted.length, 1);
  assert.equal(submitted[0].content, '新的问题');
  assert.equal(page.data.messages[1].content.length, 5000);
  assert.equal(page.data.messages.at(-1).content, 'new answer');
  assert.equal(page.data.busy, false);
});
