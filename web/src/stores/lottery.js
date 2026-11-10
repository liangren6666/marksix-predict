import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { loadLotteryCsv } from '../lib/csv.js'
import { LOTTERIES } from '../lib/lotteryMeta.js'
import { availableYears, filterByYear } from '../lib/stats.js'

export const useLotteryStore = defineStore('lottery', () => {
  const activeKey = ref('newam6hc')
  const yearFilter = ref(null)
  const searchIssue = ref('')
  const pending = ref({})
  const errors = ref({})
  const inFlight = new Map()
  const loading = computed(() => Object.values(pending.value).some(Boolean))
  const error = computed(() => errors.value[activeKey.value] || '')
  const cache = ref({})

  const meta = computed(() => LOTTERIES[activeKey.value])

  const draws = computed(() => cache.value[activeKey.value] || [])

  const filteredDraws = computed(() => {
    let list = filterByYear(draws.value, yearFilter.value)
    const q = searchIssue.value.trim()
    if (q) {
      list = list.filter((d) => String(d.issue).includes(q))
    }
    return list
  })

  const years = computed(() => availableYears(draws.value))

  function load(key = activeKey.value) {
    const info = LOTTERIES[key]
    if (!Object.hasOwn(LOTTERIES, key)) return Promise.resolve()
    if (Object.hasOwn(cache.value, key)) return Promise.resolve(cache.value[key])
    if (inFlight.has(key)) return inFlight.get(key)
    pending.value[key] = true
    errors.value[key] = ''
    const request = loadLotteryCsv(info.file)
      .then((rows) => {
        cache.value[key] = rows
        return rows
      })
      .catch((e) => {
        errors.value[key] = e instanceof Error ? e.message : String(e)
      })
      .finally(() => {
        pending.value[key] = false
        inFlight.delete(key)
      })
    inFlight.set(key, request)
    return request
  }

  async function setActive(key) {
    if (!Object.hasOwn(LOTTERIES, key)) return
    activeKey.value = key
    yearFilter.value = null
    searchIssue.value = ''
    await load(key)
  }

  async function init() {
    await Promise.all(Object.keys(LOTTERIES).map((k) => load(k)))
  }

  function drawsFor(key) {
    return cache.value[key] || []
  }

  return {
    activeKey,
    yearFilter,
    searchIssue,
    loading,
    error,
    meta,
    draws,
    filteredDraws,
    years,
    setActive,
    init,
    load,
    drawsFor,
    cache,
    LOTTERIES,
  }
})
