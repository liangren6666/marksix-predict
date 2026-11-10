import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createPinia, setActivePinia } from 'pinia'
import { parseDrawRow, parseLotteryCsv } from '../src/lib/csv.js'
import { useLotteryStore } from '../src/stores/lottery.js'

const header = 'issue,year,seq,n1,n2,n3,n4,n5,n6,special'
const csv = `${header}\n2026001,2026,1,1,2,3,4,5,6,7\n`
const valid = { issue: '2026001', year: '2026', seq: '1', n1: '1', n2: '2', n3: '3', n4: '4', n5: '5', n6: '6', special: '7' }

test('CSV rejects invalid balls, malformed integers, duplicate issues and HTML fallbacks', () => {
  for (const special of ['', '7x', '7.5', '0', '50', '6']) {
    assert.throws(() => parseDrawRow({ ...valid, special }))
  }
  assert.throws(() => parseLotteryCsv(`${csv}2026001,2026,1,1,2,3,4,5,6,7\n`), /重复期号/)
  assert.throws(() => parseLotteryCsv('<html>missing file</html>'), /CSV/)
  assert.throws(() => parseLotteryCsv(`${header}\n2026001,2026\n`), /CSV/)
})

test('empty datasets are valid; missing metadata does not shift ball colors', () => {
  assert.deepEqual(parseLotteryCsv(`${header}\n`), [])
  assert.deepEqual(parseDrawRow({ ...valid, colors: 'red,,blue' }).colors, ['red', '', 'blue'])
})

test('all bundled lottery CSVs pass the strict parser', async () => {
  for (const file of ['newam6hc_5y_verified.csv', 'am6hc_5y_verified.csv', 'macau6hc_168_verified.csv']) {
    parseLotteryCsv(await readFile(new URL(`../public/data/${file}`, import.meta.url), 'utf8'))
  }
})

function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

function response(text = csv) {
  return { ok: true, text: async () => text }
}

test('concurrent loads are deduplicated and loading lasts until all finish', async (t) => {
  setActivePinia(createPinia())
  const first = deferred(), second = deferred()
  const fetchMock = t.mock.method(globalThis, 'fetch', (url) => url.includes('newam6hc') ? first.promise : second.promise)
  const store = useLotteryStore()
  const a = store.load('newam6hc')
  const same = store.load('newam6hc')
  const b = store.load('am6hc')
  assert.equal(fetchMock.mock.callCount(), 2)
  assert.equal(store.loading, true)
  first.resolve(response())
  await Promise.all([a, same])
  assert.equal(store.loading, true)
  second.resolve(response())
  await b
  assert.equal(store.loading, false)
})

test('empty datasets are cached and invalid keys do not alter active lottery', async (t) => {
  setActivePinia(createPinia())
  const fetchMock = t.mock.method(globalThis, 'fetch', async () => response(`${header}\n`))
  const store = useLotteryStore()
  await store.load('macau6hc_168')
  await store.load('macau6hc_168')
  assert.equal(fetchMock.mock.callCount(), 1)
  await store.setActive('missing')
  assert.equal(store.activeKey, 'newam6hc')
})

test('late failures stay with their lottery and failed requests can be retried', async (t) => {
  setActivePinia(createPinia())
  const first = deferred()
  t.mock.method(globalThis, 'fetch', (url) => url.includes('newam6hc') ? first.promise : Promise.resolve(response()))
  const store = useLotteryStore()
  const old = store.load('newam6hc')
  await store.setActive('am6hc')
  first.reject(new Error('network unavailable'))
  await old
  assert.equal(store.error, '')
  store.activeKey = 'newam6hc'
  assert.match(store.error, /network unavailable/)
  t.mock.method(globalThis, 'fetch', async () => response())
  await store.load()
  assert.equal(store.error, '')
  assert.equal(store.draws.length, 1)
})
