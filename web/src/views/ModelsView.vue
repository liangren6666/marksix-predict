<script setup>
import { computed, onMounted, ref } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, MarkLineComponent } from 'echarts/components'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent, LegendComponent, MarkLineComponent])

const summary = ref(null)
const error = ref('')

const testRows = computed(() => summary.value?.test_ranking ?? [])
const theory = computed(() => summary.value?.random_top1_theory ?? 1 / 49)

onMounted(async () => {
  try {
    const res = await fetch('/data/model_benchmark.json')
    if (!res.ok) throw new Error('缺少 model_benchmark.json，请先运行: python -m ml.run_benchmark')
    summary.value = await res.json()
  } catch (e) {
    error.value = e.message
  }
})

const chartOption = computed(() => {
  const rows = testRows.value
  if (!rows.length) return {}
  const names = rows.map((r) => r.model)
  const pct = (v) => Math.round(v * 1000) / 10
  return {
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, textStyle: { color: '#8b97ab' } },
    grid: { left: 48, right: 16, top: 24, bottom: 52 },
    xAxis: {
      type: 'category',
      data: names,
      axisLabel: { color: '#8b97ab', interval: 0, fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: '命中率 %',
      max: Math.max(15, ...rows.map((r) => r.top5 * 100 + 5)),
      axisLabel: { color: '#8b97ab', formatter: '{value}%' },
      splitLine: { lineStyle: { color: '#1f2836' } },
    },
    series: [
      {
        name: 'Top-1',
        type: 'bar',
        data: rows.map((r) => pct(r.top1)),
        itemStyle: { color: '#d4a84b' },
        barMaxWidth: 36,
        markLine: {
          silent: true,
          data: [{ yAxis: pct(theory.value), name: '理论随机' }],
          lineStyle: { color: '#5b8def', type: 'dashed' },
          label: { formatter: '理论随机 Top-1 ≈ {c}%', color: '#5b8def' },
        },
      },
      {
        name: 'Top-5',
        type: 'bar',
        data: rows.map((r) => pct(r.top5)),
        itemStyle: { color: '#5b8def' },
        barMaxWidth: 36,
      },
    ],
  }
})

function pct(v) {
  return `${(v * 100).toFixed(2)}%`
}

function kindLabel(k) {
  return { baseline: '统计基线', ml: '机器学习' }[k] || k
}
</script>

<template>
  <p v-if="error" class="panel err">{{ error }}</p>

  <template v-else-if="summary">
    <section class="intro panel">
      <h2>{{ summary.title }}</h2>
      <p>
        预测目标：<strong>下一期特码</strong>（49 选 1）。封存测试
        <strong>{{ summary.split.test }}</strong> 期（{{ summary.issues_test_range?.join(' — ') }}），训练过程未使用。
      </p>
      <p class="conclusion">{{ summary.conclusion_zh }}</p>
    </section>

    <section class="cards">
      <article
        v-for="m in summary.models_meta"
        :key="m.id"
        class="panel card"
        :class="{ top: summary.best_on_test_top1 === m.model }"
      >
        <div class="card-head">
          <span class="tag" :data-k="m.kind">{{ kindLabel(m.kind) }}</span>
          <span v-if="summary.best_on_test_top1 === m.model" class="badge">测试 Top-1 最高</span>
        </div>
        <h3>{{ m.model }}</h3>
        <p class="desc">{{ m.desc }}</p>
        <dl v-if="testRows.find((r) => r.id === m.id)">
          <div>
            <dt>测试 Top-1</dt>
            <dd class="mono big">{{ pct(testRows.find((r) => r.id === m.id).top1) }}</dd>
          </div>
          <div>
            <dt>测试 Top-5</dt>
            <dd class="mono">{{ pct(testRows.find((r) => r.id === m.id).top5) }}</dd>
          </div>
        </dl>
      </article>
    </section>

    <article class="panel chart-panel">
      <h3 class="panel-title">测试集命中率对比</h3>
      <p class="hint">虚线为理论随机 Top-1（约 2.04%）。柱高接近表示无有效规律。</p>
      <div class="chart-wrap">
        <VChart class="chart" :option="chartOption" autoresize />
      </div>
    </article>

    <p class="foot panel">{{ summary.recommendation_zh }}</p>
  </template>

  <p v-else class="panel note">加载模型对比…</p>
</template>

<style scoped>
.intro h2 {
  margin: 0 0 0.5rem;
  font-size: 1.15rem;
}

.intro p {
  margin: 0.35rem 0;
  color: var(--text-muted);
  font-size: 0.9rem;
  line-height: 1.55;
}

.conclusion {
  margin-top: 0.75rem !important;
  padding: 0.65rem 0.75rem;
  border-left: 3px solid var(--accent);
  color: var(--text) !important;
  background: var(--accent-dim);
  border-radius: 0 8px 8px 0;
}

.cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.85rem;
}

.card {
  padding: 1rem 1.05rem;
}

.card.top {
  border-color: rgba(212, 168, 75, 0.45);
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
}

.tag {
  font-size: 0.72rem;
  padding: 0.15rem 0.45rem;
  border-radius: 6px;
  background: var(--panel-raised);
  color: var(--text-muted);
}

.tag[data-k='ml'] {
  color: #5b8def;
}

.badge {
  font-size: 0.68rem;
  color: var(--accent);
}

.card h3 {
  margin: 0 0 0.35rem;
  font-size: 1rem;
}

.desc {
  margin: 0 0 0.75rem;
  font-size: 0.8rem;
  color: var(--text-muted);
  line-height: 1.45;
  min-height: 2.9em;
}

dl {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
  margin: 0;
}

dt {
  font-size: 0.72rem;
  color: var(--text-muted);
}

dd {
  margin: 0.15rem 0 0;
}

.big {
  font-size: 1.35rem;
  color: var(--accent);
  font-weight: 700;
}

.chart-panel {
  padding: 1rem 1.05rem 0.25rem;
  margin-top: 0.85rem;
}

.hint {
  margin: 0 0 0.5rem;
  font-size: 0.82rem;
  color: var(--text-muted);
}

.foot {
  margin-top: 0.85rem;
  padding: 0.85rem 1rem;
  font-size: 0.85rem;
  color: var(--text-muted);
  line-height: 1.5;
}

.panel {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

.err {
  padding: 1rem;
  color: #ffb4b4;
}

.note {
  padding: 1rem;
  color: var(--text-muted);
}

@media (max-width: 900px) {
  .cards {
    grid-template-columns: 1fr;
  }
}
</style>
