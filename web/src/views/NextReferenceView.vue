<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'

const forecast = shallowRef(null)
const benchmark = shallowRef(null)
const busy = ref(false)
const error = ref('')
const source = ref('')
const mode = ref('regular')
const inspected = ref(null)
const matrix = ref(null)
const targetDate = ref('')
const controller = new AbortController()
const numbers = Array.from({ length: 49 }, (_, i) => i + 1)
const groups = [
  { key: 'regular', label: '正码', limit: 20 },
  { key: 'special', label: '特码', limit: 20 },
]

const latest = computed(() => forecast.value?.last_draw)
const candidates = computed(() => Object.fromEntries(groups.map(({ key, limit }) => [
  key, forecast.value?.[key].ranking.slice(0, limit) ?? [],
])))
const byNumber = computed(() => new Map(
  (forecast.value?.[mode.value].ranking || []).map((item) => [item.num, item]),
))
const selected = computed(() => byNumber.value.get(inspected.value))
const selectedNumbers = computed(() => new Set(candidates.value[mode.value].map(({ num }) => num)))
const benchmarkRows = computed(() => {
  const report = benchmark.value
  if (!report) return []
  return [
    { label: '梯度提升树', value: report.results?.['梯度提升树']?.average_hits, kind: 'model' },
    { label: '近 30 期热号', value: report.results?.['近30期热号']?.average_hits, kind: 'hot' },
    { label: '逻辑回归', value: report.results?.['逻辑回归']?.average_hits, kind: 'logreg' },
    { label: '随机选号', value: report.uniform_expected_hits_per_draw, kind: 'random' },
    { label: 'GRU 神经网络', value: report.results?.GRU?.average_hits, kind: 'gru' },
  ].filter((row) => Number.isFinite(row.value))
})
const benchmarkScale = computed(() => Math.max(1, ...benchmarkRows.value.map((row) => row.value)))
const bounds = computed(() => ({
  min: forecast.value?.selectable_from || '',
  max: forecast.value?.selectable_to || '',
}))
const hitSummary = computed(() => {
  const actual = forecast.value?.actual
  const picks = candidates.value
  if (!actual || !picks.regular) return ''
  const regularHits = actual.regular.filter((num) => picks.regular.some((item) => item.num === num)).length
  const specialHit = picks.special.some((item) => item.num === actual.special)
  return `当期已开奖：正码命中 ${regularHits}/6，特码${specialHit ? '在' : '不在'}前 20 名里`
})
const generatedTime = computed(() => {
  const time = forecast.value?.generated_at
  if (!time) return ''
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).format(new Date(time))
})

function numberText(num) {
  return String(num).padStart(2, '0')
}

function isHit(kind, num) {
  const actual = forecast.value?.actual
  if (!actual) return false
  return kind === 'special' ? actual.special === num : actual.regular.includes(num)
}

async function inspect(kind, num) {
  mode.value = kind
  inspected.value = num
  await nextTick()
  matrix.value?.querySelector('[aria-pressed="true"]')?.focus()
}

function validate(payload) {
  const rankCount = numbers.length
  if (!payload?.last_draw?.issue || !Number.isFinite(Date.parse(payload.generated_at))
      || groups.some(({ key }) => payload[key]?.ranking?.length !== rankCount)) {
    throw new Error('预测结果不完整。请重新生成。')
  }
  return payload
}

const catalog = shallowRef(null)
const desktop = ref(false)
const trainLabel = ref('更新并训练')

async function readJson(url) {
  const response = await fetch(url, { signal: controller.signal, cache: 'no-store' })
  const payload = await response.json()
  if (!response.ok) throw new Error(payload.error || '读取数据失败。')
  return payload
}

function applyForecast(payload, nextSource) {
  forecast.value = validate(payload)
  source.value = nextSource
  if (payload.target?.date) targetDate.value = payload.target.date
}

async function generate() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    const dataDir = import.meta.env.BASE_URL + 'data/'
    catalog.value ??= await readJson(dataDir + 'forecasts.json')
    const book = catalog.value
    if (!targetDate.value) targetDate.value = book.default_date
    const page = book.days?.[targetDate.value]
    if (!page) throw new Error(`没有 ${targetDate.value} 的预测。可选范围是 ${book.selectable_from} 到 ${book.selectable_to}。`)
    applyForecast({
      ...page,
      selectable_from: book.selectable_from,
      selectable_to: book.selectable_to,
    }, 'saved')
  } catch (e) {
    if (e.name !== 'AbortError') {
      error.value = e instanceof TypeError ? '预测数据没有加载出来。' : e.message
    }
  } finally {
    busy.value = false
  }
}

async function retrain() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  trainLabel.value = '正在更新…'
  try {
    const response = await fetch(`${import.meta.env.BASE_URL}api/retrain`, { method: 'POST', cache: 'no-store' })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.error || '更新失败。')
    location.reload()
  } catch (e) {
    if (e.name !== 'AbortError') {
      error.value = e instanceof TypeError ? '更新没有完成。' : e.message
    }
    busy.value = false
    trainLabel.value = '更新并训练'
  }
}

onMounted(() => {
  const dataDir = import.meta.env.BASE_URL + 'data/'
  readJson(dataDir + 'regular_benchmark.json').then((payload) => {
    benchmark.value = payload
  }).catch(() => {})
  fetch(`${import.meta.env.BASE_URL}api/desktop`, { cache: 'no-store' })
    .then((response) => (response.ok ? response.json() : null))
    .then((payload) => { desktop.value = Boolean(payload?.desktop) })
    .catch(() => {})
  generate()
})
onBeforeUnmount(() => controller.abort())
</script>

<template>
  <header class="forecast-heading">
    <div>
      <h1>按日期预测</h1>
      <p>新澳门彩<span v-if="forecast?.target"> · 第 <strong>{{ forecast.target.issue }}</strong> 期</span><span v-if="latest"> · 数据截至 <strong>{{ latest.issue }}</strong> 期</span></p>
    </div>
    <div class="heading-actions">
      <label class="date-field">
        <span>预测日期</span>
        <input v-model="targetDate" type="date" :min="bounds.min" :max="bounds.max" :disabled="busy" @change="generate" />
      </label>
      <button v-if="desktop" class="train-button" type="button" :disabled="busy" @click="retrain">
        {{ trainLabel }}
      </button>
      <button class="generate-button" type="button" :disabled="busy" @click="generate">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 10a7 7 0 1 0-1.6 6.5M19 4v6h-6" /></svg>
      {{ busy ? '正在计算…' : '生成预测' }}
    </button>
    </div>
  </header>

  <p v-if="error" class="notice error" role="alert">
    {{ error }}<span v-if="forecast"> 当前显示上次生成的结果。</span>
  </p>

  <section class="panel candidate-panel" aria-labelledby="candidates-title" :aria-busy="busy">
    <div class="section-header">
      <h2 id="candidates-title">{{ forecast?.target?.date || '所选日期' }} 的候选号码</h2>
      <span v-if="forecast" class="result-status" aria-live="polite">
        <i :class="{ live: source === 'live' }" aria-hidden="true"></i>
        {{ source === 'live' ? '本地计算' : '已保存' }} · {{ generatedTime }}
      </span>
    </div>

    <div v-if="forecast" class="candidate-groups">
      <div v-for="group in groups" :key="group.key" :class="group.key + '-group'">
        <div class="group-heading">
          <h3>{{ group.label }} <span>前 {{ group.limit }} 名</span></h3>
          <span>{{ forecast[group.key].model }}</span>
        </div>
        <ol class="candidate-ranking" role="list" :aria-label="group.label + '候选排名'">
          <li v-for="{ num, rank } in candidates[group.key]" :key="num">
            <button type="button" class="candidate-pick" :class="{ hit: isHit(group.key, num) }"
              :aria-label="group.label + '第 ' + rank + ' 名，号码 ' + numberText(num)"
              @click="inspect(group.key, num)">
              <span class="candidate-rank" aria-hidden="true">#{{ rank }}</span>
              <span class="candidate-ball">{{ numberText(num) }}</span>
            </button>
          </li>
        </ol>
      </div>
    </div>

    <div v-else-if="busy" class="skeleton-row" role="status" aria-label="正在生成候选号码">
      <span v-for="n in 7" :key="n"></span>
    </div>
    <p v-else class="empty">暂时没有候选号码。点击「生成预测」重试。</p>
    <p v-if="forecast?.note" class="candidate-note">{{ forecast.note }}</p>
    <p v-if="hitSummary" class="candidate-note hit-summary">{{ hitSummary }}</p>
    <p v-if="forecast?.actual" class="actual-line">
      当期开奖
      <span v-for="num in forecast.actual.regular" :key="'a' + num">{{ numberText(num) }}</span>
      <b>+</b>
      <span class="actual-special">{{ numberText(forecast.actual.special) }}</span>
    </p>
    <p class="candidate-note">正码、特码各自按模型分值列出最可能的 20 个号码，两组号码可以重叠。已开奖时，命中的号码会加一圈。</p>
  </section>

  <div class="workspace">
    <section class="panel matrix-panel" aria-labelledby="matrix-title">
      <div class="section-header matrix-header">
        <div>
          <h2 id="matrix-title">号码分布</h2>
          <p>点选号码查看模型排名</p>
        </div>
        <div class="segments" role="group" aria-label="查看号码类别">
          <button v-for="item in groups"
            :key="item.key" type="button" :aria-pressed="mode === item.key" @click="mode = item.key">{{ item.label }}</button>
        </div>
      </div>

      <div ref="matrix" class="matrix" :class="{ 'special-matrix': mode === 'special' }">
        <button v-for="num in numbers" :key="num" type="button" class="number-tile"
          :class="{ picked: selectedNumbers.has(num) }" :disabled="!forecast"
          :aria-pressed="inspected === num"
          :aria-label="'号码 ' + numberText(num) + (selectedNumbers.has(num) ? '，已入选' : '')"
          @click="inspected = num">
          {{ numberText(num) }}<i v-if="selectedNumbers.has(num)" aria-hidden="true"></i>
        </button>
      </div>

      <div class="matrix-footer" aria-live="polite">
        <span v-if="selected"><strong class="number">{{ numberText(selected.num) }}</strong> · {{ mode === 'regular' ? '正码' : '特码' }}排名第 {{ selected.rank }} · 模型分值 {{ selected.score.toFixed(4) }}</span>
        <span v-else class="matrix-key"><i aria-hidden="true"></i>入选候选</span>
        <span>模型分值仅用于排序</span>
      </div>
    </section>

    <div class="detail-column">
      <section class="panel detail-panel" aria-labelledby="latest-title">
        <div class="section-header"><h2 id="latest-title">最新一期开奖</h2></div>
        <div v-if="latest">
          <p class="issue">第 <strong class="number">{{ latest.issue }}</strong> 期</p>
          <div class="latest-balls" aria-label="最新一期正码与特码">
            <span v-for="num in latest.regular" :key="num">{{ numberText(num) }}</span>
            <b aria-hidden="true">+</b><span class="last-special">{{ numberText(latest.special) }}</span>
          </div>
        </div>
        <p v-else class="empty">等待载入最新一期开奖。</p>
      </section>

      <section class="panel detail-panel" aria-labelledby="benchmark-title">
        <div class="section-header"><h2 id="benchmark-title">正码回测</h2></div>
        <template v-if="benchmarkRows.length">
          <p class="detail-note">{{ benchmark.split.test }} 期测试 · 每期选 6 个正码的平均命中数</p>
          <ul class="bench-list">
            <li v-for="row in benchmarkRows" :key="row.kind">
              <div><span>{{ row.label }}</span><strong class="number">{{ row.value.toFixed(3) }}</strong></div>
              <div class="bench-track" aria-hidden="true"><span :class="row.kind" :style="{ width: (row.value / benchmarkScale * 100) + '%' }"></span></div>
            </li>
          </ul>
          <p class="detail-note benchmark-note">测试期 {{ benchmark.test_issue_range.join('–') }}。能否持续超过随机，仍需用新开奖验证。</p>
        </template>
        <p v-else class="empty">暂无正码回测报告。</p>
      </section>
    </div>
  </div>
</template>

<style scoped>
.forecast-heading { display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 0 0 6px; }
.forecast-heading h1 { margin: 0; font-size: 2.05rem; line-height: 1.2; letter-spacing: -.035em; }
.forecast-heading p { margin: 8px 0 0; font-size: .92rem; color: var(--text-muted); }
.forecast-heading p strong { color: var(--text); font-weight: 650; font-variant-numeric: tabular-nums; }
.heading-actions { display: flex; align-items: flex-end; gap: 10px; flex: none; }
.date-field { display: grid; gap: 4px; color: var(--text-muted); font-size: .78rem; }
.date-field input {
  min-height: 44px; padding: 0 10px; color: var(--text); background: var(--bg);
  border: 1px solid var(--border); border-radius: 8px; color-scheme: dark;
}
.generate-button {
  display: inline-flex; align-items: center; justify-content: center; gap: 7px; min-height: 44px; padding: 0 15px;
  background: var(--accent); color: var(--accent-ink); border: 1px solid transparent; border-radius: 8px;
  white-space: nowrap; font-weight: 700; cursor: pointer; transition: background 160ms;
}
.generate-button svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 1.9; stroke-linecap: round; stroke-linejoin: round; }
.generate-button:hover:not(:disabled) { background: #ffd59a; }
.generate-button:disabled { background: var(--accent-dim); color: var(--accent); cursor: wait; }
.train-button {
  display: inline-flex; align-items: center; justify-content: center; min-height: 44px; padding: 0 15px;
  background: transparent; color: var(--text); border: 1px solid var(--border); border-radius: 8px;
  white-space: nowrap; font-weight: 650; cursor: pointer;
}
.train-button:hover:not(:disabled) { border-color: var(--text-muted); }
.train-button:disabled { color: var(--text-muted); cursor: wait; }
.notice { padding: 11px 14px; border-radius: 9px; border: 1px solid #76444c; margin: 0; color: #ffc1c5; background: #302127; font-size: .9rem; }
.candidate-panel, .matrix-panel, .detail-panel { min-width: 0; padding: 20px 22px; }
.section-header { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.section-header h2 { margin: 0; font-size: 1.08rem; letter-spacing: -.015em; }
.result-status { display: inline-flex; align-items: center; gap: 6px; color: var(--text-muted); font-size: .8rem; font-variant-numeric: tabular-nums; }
.result-status i { width: 6px; height: 6px; border-radius: 50%; background: var(--text-muted); flex: none; }
.result-status i.live { background: #7fc7a0; }
.candidate-groups { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 16px; gap: 20px; }
.special-group { padding-left: 20px; border-left: 1px solid var(--border); }
.group-heading { display: flex; align-items: baseline; gap: 8px 12px; flex-wrap: wrap; margin-bottom: 11px; }
.group-heading h3 { margin: 0; font-size: .95rem; }
.group-heading h3 span { color: var(--text-muted); font-size: .8rem; margin-left: 3px; font-weight: 400; }
.group-heading > span { font-size: .8rem; color: var(--text-muted); }
.candidate-ranking {
  display: grid; grid-template-columns: repeat(10, minmax(0, 1fr)); gap: 9px 7px;
  margin: 0; padding: 0; list-style: none;
}
.candidate-pick {
  display: grid; justify-items: stretch; gap: 2px; width: 100%; min-width: 0; padding: 0;
  border: 0; border-radius: 6px; background: transparent; cursor: pointer;
  font-variant-numeric: tabular-nums;
}
.candidate-rank { color: var(--text-muted); font-size: .75rem; }
.candidate-ball {
  display: grid; place-items: center; aspect-ratio: 1; min-width: 0; border: 1px solid #735631;
  border-radius: 50%; color: var(--accent); background: var(--accent-dim);
  font-size: 1.2rem; font-weight: 700; transition: background 160ms;
}
.candidate-pick:hover .candidate-ball { background: #503a24; }
.candidate-pick.hit .candidate-ball { box-shadow: 0 0 0 2px var(--text); }
.special-group .candidate-ball { color: var(--special); background: var(--special-dim); border-color: #4b6790; }
.special-group .candidate-pick:hover .candidate-ball { background: #334b6d; }
.candidate-note { margin: 15px 0 0; padding-top: 11px; border-top: 1px solid var(--border); font-size: .83rem; color: var(--text-muted); }
.hit-summary { border-top: 0; padding-top: 0; margin-top: 8px; color: var(--text); }
.actual-line { display: flex; flex-wrap: wrap; gap: 5px; align-items: center; margin: 10px 0 0; color: var(--text-muted); font-size: .84rem; }
.actual-line span { width: 28px; height: 28px; display: grid; place-items: center; border-radius: 50%; background: var(--panel-raised); color: var(--text); font-variant-numeric: tabular-nums; }
.actual-line .actual-special { color: var(--special); background: var(--special-dim); font-weight: 700; }
.actual-line b { color: var(--text-muted); font-weight: 500; }
.skeleton-row { display: flex; gap: 9px; margin: 22px 0 14px; }
.skeleton-row span { width: min(12%, 53px); aspect-ratio: 1; background: var(--panel-raised); border-radius: 50%; }
.empty { margin: 14px 0; font-size: .89rem; color: var(--text-muted); }
.workspace { display: grid; grid-template-columns: minmax(0, 1.7fr) minmax(0, 1fr); gap: 16px; align-items: start; }
.detail-column { display: grid; gap: 16px; min-width: 0; }
.matrix-header { margin-bottom: 14px; }
.matrix-header p { margin: 4px 0 0; color: var(--text-muted); font-size: .84rem; }
.segments { display: inline-flex; gap: 3px; padding: 3px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg); flex: none; }
.segments button {
  padding: 5px 10px; min-height: 32px; background: transparent; border: 0; border-radius: 5px;
  color: var(--text-muted); font-size: .84rem; white-space: nowrap; cursor: pointer;
}
.segments button:hover, .segments button[aria-pressed='true'] { background: var(--panel-raised); color: var(--text); }
.matrix { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 6px; }
.number-tile {
  position: relative; display: grid; place-items: center; min-width: 0; min-height: 38px; padding: 0;
  border: 1px solid var(--border); border-radius: 7px; color: var(--text);
  background: var(--bg); font-size: .93rem; font-weight: 600; font-variant-numeric: tabular-nums; cursor: pointer;
}
.number-tile:hover:not(:disabled) { border-color: var(--text-muted); }
.number-tile:disabled { color: var(--text-muted); cursor: default; }
.number-tile[aria-pressed='true'] { outline: 1px solid var(--special); outline-offset: -1px; }
.number-tile:focus-visible { outline-offset: 2px; z-index: 1; }
.number-tile.picked { color: var(--accent); background: var(--accent-dim); border-color: #735631; }
.special-matrix .number-tile.picked { color: var(--special); background: var(--special-dim); border-color: #4b6790; }
.number-tile i { position: absolute; top: 6px; right: 6px; width: 4px; height: 4px; border-radius: 50%; background: currentColor; }
.matrix-footer { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 5px 12px; min-height: 22px; margin-top: 13px; font-size: .8rem; color: var(--text-muted); }
.matrix-footer strong { color: var(--text); }
.matrix-key { display: inline-flex; align-items: center; gap: 6px; }
.matrix-key i { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); }
.matrix-panel:has(.special-matrix) .matrix-key i { background: var(--special); }
.issue { margin: 11px 0; color: var(--text-muted); font-size: .88rem; }
.issue strong { color: var(--text); font-size: 1rem; }
.number { font-variant-numeric: tabular-nums; }
.latest-balls { display: flex; flex-wrap: wrap; gap: 5px; align-items: center; }
.latest-balls span { width: 29px; height: 29px; display: grid; place-items: center; border-radius: 50%; background: var(--panel-raised); font-size: .8rem; font-variant-numeric: tabular-nums; }
.latest-balls .last-special { color: var(--special); background: var(--special-dim); font-weight: 700; }
.latest-balls b { padding: 0 2px; font-size: .8rem; color: var(--text-muted); }
.detail-note { color: var(--text-muted); font-size: .84rem; margin: 6px 0 0; }
.bench-list { display: grid; gap: 12px; padding: 0; margin: 15px 0 0; list-style: none; }
.bench-list li > div:first-child { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; margin-bottom: 4px; font-size: .86rem; }
.bench-list strong { font-size: .94rem; }
.bench-track { height: 4px; background: var(--panel-raised); border-radius: 4px; overflow: hidden; }
.bench-track span { height: 100%; display: block; border-radius: inherit; background: #7a899e; }
.bench-track .model { background: var(--accent); }
.bench-track .hot { background: #8cadd9; }
.benchmark-note { margin-top: 15px; padding-top: 11px; border-top: 1px solid var(--border); font-size: .8rem; }

@media (max-width: 1050px) {
  .workspace { grid-template-columns: minmax(0, 1.45fr) minmax(0, 1fr); }
  .candidate-panel, .matrix-panel, .detail-panel { padding: 17px 16px; }
  .candidate-ranking { grid-template-columns: repeat(5, minmax(0, 1fr)); }
}
@media (max-width: 880px) {
  .workspace { grid-template-columns: minmax(0, 1fr); }
  .detail-column { grid-template-columns: minmax(0, 1fr) minmax(0, 1.15fr); align-items: start; }
}
@media (max-width: 600px) {
  .candidate-groups { grid-template-columns: minmax(0, 1fr); gap: 14px; }
  .special-group { border-left: 0; padding: 12px 0 0; border-top: 1px solid var(--border); }
}
@media (max-width: 540px) {
  .forecast-heading, .heading-actions { align-items: flex-start; flex-wrap: wrap; gap: 12px; }
  .forecast-heading h1 { font-size: 1.7rem; }
  .forecast-heading p { font-size: .86rem; }
  .detail-column { grid-template-columns: minmax(0, 1fr); gap: 14px; }
  .candidate-ranking { gap: 7px 6px; }
  .candidate-ball { font-size: 1.14rem; }
  .result-status { font-size: .73rem; }
  .candidate-panel, .matrix-panel, .detail-panel { padding: 15px; }
  .number-tile { min-height: 40px; }
  .matrix { gap: 5px; }
}
@media (prefers-reduced-motion: reduce) {
  .generate-button, .candidate-ball { transition: none; }
}
</style>
