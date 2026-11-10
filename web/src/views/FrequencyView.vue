<script setup>
import { computed, ref } from 'vue'
import { useLotteryStore } from '../stores/lottery'
import FreqBarChart from '../components/charts/FreqBarChart.vue'
import ZodiacBarChart from '../components/charts/ZodiacBarChart.vue'
import {
  frequencyMap,
  topNumbers,
  coldNumbers,
  zodiacFreq,
} from '../lib/stats'

const store = useLotteryStore()
const mode = ref('all')

const draws = computed(() => store.filteredDraws)

const freq = computed(() =>
  frequencyMap(draws.value, { specialOnly: mode.value === 'special' }),
)

const hot = computed(() => topNumbers(freq.value, 12))
const cold = computed(() => coldNumbers(freq.value, 12))
const zodiacs = computed(() => (store.meta.hasMeta ? zodiacFreq(draws.value) : []))
</script>

<template>
  <section class="toolbar panel">
    <label>
      <span>统计范围</span>
      <select v-model="mode">
        <option value="all">全部 7 个球位</option>
        <option value="special">仅特码</option>
      </select>
    </label>
    <label v-if="store.years.length">
      <span>年份</span>
      <select v-model="store.yearFilter">
        <option :value="null">全部</option>
        <option v-for="y in store.years" :key="y" :value="y">{{ y }}</option>
      </select>
    </label>
    <p class="hint">基于当前彩种已加载样本；不等于预测概率。</p>
  </section>

  <article class="panel chart-panel">
    <FreqBarChart
      :freq="freq"
      :title="mode === 'special' ? '特码出现次数（01-49）' : '全号位出现次数（01-49）'"
      :highlight="hot.map((x) => x.num)"
    />
  </article>

  <section class="rank-grid">
    <article class="panel rank">
      <h3 class="panel-title">热号 TOP12</h3>
      <ul>
        <li v-for="(x, i) in hot" :key="x.num">
          <span class="idx">{{ i + 1 }}</span>
          <span class="mono num">{{ String(x.num).padStart(2, '0') }}</span>
          <span class="count">{{ x.count }} 次</span>
        </li>
      </ul>
    </article>
    <article class="panel rank">
      <h3 class="panel-title">冷号 TOP12</h3>
      <ul>
        <li v-for="(x, i) in cold" :key="x.num">
          <span class="idx">{{ i + 1 }}</span>
          <span class="mono num">{{ String(x.num).padStart(2, '0') }}</span>
          <span class="count">{{ x.count }} 次</span>
        </li>
      </ul>
    </article>
    <article v-if="store.meta.hasMeta && zodiacs.length" class="panel rank wide">
      <h3 class="panel-title">生肖出现频次</h3>
      <ZodiacBarChart :items="zodiacs.slice(0, 12)" />
    </article>
  </section>
  <p v-if="!store.meta.hasMeta" class="panel note">
    当前彩种无生肖 / 波色元数据，仅展示号码频次与冷热号。
  </p>
</template>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem 1.5rem;
  align-items: flex-end;
  padding: 0.85rem 1rem;
}

label {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.8rem;
  color: var(--text-muted);
}

select {
  padding: 0.4rem 0.55rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--panel-raised);
  color: var(--text);
  min-width: 160px;
}

.hint {
  margin: 0;
  flex: 1;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.chart-panel {
  padding: 1rem 1.1rem 0.5rem;
}

.rank-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
}

.rank {
  padding: 1rem 1.1rem;
}

.rank.wide {
  grid-column: 1 / -1;
}

.rank ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.rank li {
  display: grid;
  grid-template-columns: 1.5rem 3rem 1fr;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.88rem;
}

.idx {
  color: var(--text-muted);
  font-size: 0.75rem;
}

.num {
  font-weight: 600;
  color: var(--accent);
}

.count {
  color: var(--text-muted);
}

.note {
  padding: 0.85rem 1rem;
  color: var(--text-muted);
  font-size: 0.85rem;
  margin: 0;
}

@media (max-width: 768px) {
  .rank-grid {
    grid-template-columns: 1fr;
  }
}
</style>
