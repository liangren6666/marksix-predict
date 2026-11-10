<script setup>
import { computed } from 'vue'
import { useLotteryStore } from '../stores/lottery'
import StatCard from '../components/StatCard.vue'
import BallStrip from '../components/BallStrip.vue'
import RecentSpecialList from '../components/RecentSpecialList.vue'
import RecentOpenList from '../components/RecentOpenList.vue'
import ColorDistributionBar from '../components/ColorDistributionBar.vue'
import { frequencyMap, topNumbers, sumStats, colorFreq } from '../lib/stats'

const store = useLotteryStore()

const latest = computed(() => store.filteredDraws[0])
const allFreq = computed(() => frequencyMap(store.filteredDraws, { specialOnly: false }))
const specialFreq = computed(() => frequencyMap(store.filteredDraws, { specialOnly: true }))
const hot = computed(() => topNumbers(allFreq.value, 5))
const hotSpecial = computed(() => topNumbers(specialFreq.value, 3))
const sum = computed(() => sumStats(store.filteredDraws))
const colors = computed(() => (store.meta.hasMeta ? colorFreq(store.filteredDraws) : []))
const showColorPanel = computed(
  () => store.meta.hasMeta && colors.value.some((x) => x.value > 0),
)
</script>

<template>
  <section v-if="latest" class="latest panel">
    <div class="latest-head">
      <div>
        <p class="eyebrow">最新一期</p>
        <h2 class="mono">{{ latest.issue }}</h2>
      </div>
      <BallStrip :nums="latest.all" :colors="latest.colors" />
    </div>
    <p v-if="latest.openTime" class="meta">开奖时间：{{ latest.openTime }}</p>
    <p v-else-if="latest.verifySources" class="meta">校验来源：{{ latest.verifySources }}</p>
  </section>

  <section class="stats">
    <StatCard label="样本期数" :value="store.filteredDraws.length" />
    <StatCard label="和值区间" :value="`${sum.min} — ${sum.max}`" :hint="`平均 ${sum.avg}`" />
    <StatCard
      label="热门号码 TOP1"
      :value="hot[0] ? `${String(hot[0].num).padStart(2, '0')} (${hot[0].count}次)` : '—'"
    />
    <StatCard label="期号范围" :value="store.draws.length ? `${store.draws.at(-1)?.issue} ~ ${store.draws[0]?.issue}` : '—'" />
  </section>

  <section class="grid-2">
    <article class="panel block">
      <h3 class="panel-title">最近 24 期特码</h3>
      <p class="block-hint">列表比折线图更易读；完整走势见「号码分析」。</p>
      <RecentSpecialList :draws="store.filteredDraws" />
    </article>

    <article v-if="showColorPanel" class="panel block">
      <h3 class="panel-title">波色占比（全号位）</h3>
      <ColorDistributionBar :items="colors" />
      <p class="block-hint top-gap">特码热号：{{ hotSpecial.map((x) => String(x.num).padStart(2, '0')).join(' · ') || '—' }}</p>
    </article>

    <article v-else class="panel block">
      <h3 class="panel-title">最近开奖</h3>
      <p class="block-hint">当前彩种无波色字段，仅展示开奖号码与时间。</p>
      <RecentOpenList :draws="store.filteredDraws" />
    </article>
  </section>
</template>

<style scoped>
.latest {
  padding: 1.25rem 1.35rem;
}

.latest-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.eyebrow {
  margin: 0;
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.latest h2 {
  margin: 0.25rem 0 0;
  font-size: 1.75rem;
  color: var(--accent);
}

.meta {
  margin: 0.85rem 0 0;
  font-size: 0.85rem;
  color: var(--text-muted);
}

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.85rem;
}

.grid-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
}

.block {
  padding: 1rem 1.15rem 1.1rem;
  min-height: 200px;
}

.block-hint {
  margin: 0 0 0.75rem;
  font-size: 0.78rem;
  color: var(--text-muted);
  line-height: 1.45;
}

.top-gap {
  margin-top: 1rem;
  margin-bottom: 0;
}

@media (max-width: 900px) {
  .grid-2 {
    grid-template-columns: 1fr;
  }
}
</style>
