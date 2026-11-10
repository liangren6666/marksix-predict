<script setup>
import { computed, onMounted } from 'vue'
import { useLotteryStore } from '../stores/lottery'
import BallStrip from '../components/BallStrip.vue'

const store = useLotteryStore()

onMounted(() => store.init())

const snapshots = computed(() => {
  const out = {}
  for (const [key, meta] of Object.entries(store.LOTTERIES)) {
    const list = store.drawsFor(key)
    out[key] = { meta, latest: list[0] || null, count: list.length }
  }
  return out
})
</script>

<template>
  <p class="warn panel">
    三条产品线独立编号、独立开奖号码。相同期号数值<strong>不代表同一期</strong>，请勿混用训练或下注逻辑。
  </p>

  <section class="cards">
    <article v-for="(snap, key) in snapshots" :key="key" class="panel card">
      <header>
        <h3>{{ snap.meta.label }}</h3>
        <p>{{ snap.meta.source }} · {{ snap.count }} 期</p>
      </header>
      <template v-if="snap.latest">
        <p class="issue mono">第 {{ snap.latest.issue }} 期</p>
        <BallStrip :nums="snap.latest.all" :colors="snap.latest.colors" />
        <p v-if="snap.latest.openTime" class="sub">开奖 {{ snap.latest.openTime }}</p>
      </template>
      <p v-else class="sub">数据未同步</p>
    </article>
  </section>

  <article class="panel table-panel">
    <h3 class="panel-title">最新开奖对照</h3>
    <table>
      <thead>
        <tr>
          <th>彩种</th>
          <th>期号</th>
          <th>号码</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(snap, key) in snapshots" :key="key">
          <td>{{ snap.meta.label }}</td>
          <td class="mono">{{ snap.latest?.issue ?? '—' }}</td>
          <td class="mono" v-if="snap.latest">
            {{ snap.latest.nums.map((n) => String(n).padStart(2, '0')).join(' ') }}
            + {{ String(snap.latest.special).padStart(2, '0') }}
          </td>
          <td v-else>—</td>
        </tr>
      </tbody>
    </table>
  </article>
</template>

<style scoped>
.warn {
  padding: 0.85rem 1rem;
  color: var(--text-muted);
  font-size: 0.9rem;
  line-height: 1.55;
  border-left: 3px solid var(--accent);
}

.cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.85rem;
}

.card {
  padding: 1rem 1.11rem;
}

.card header h3 {
  margin: 0;
  font-size: 1rem;
}

.card header p {
  margin: 0.25rem 0 0;
  font-size: 0.78rem;
  color: var(--text-muted);
}

.issue {
  margin: 0.85rem 0 0.5rem;
  color: var(--accent);
  font-weight: 600;
}

.sub {
  margin: 0.75rem 0 0;
  font-size: 0.82rem;
  color: var(--text-muted);
}

.table-panel {
  padding: 1rem 1.1rem;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}

th,
td {
  padding: 0.6rem 0.5rem;
  border-bottom: 1px solid var(--border);
  text-align: left;
}

th {
  color: var(--text-muted);
  font-weight: 500;
}

@media (max-width: 900px) {
  .cards {
    grid-template-columns: 1fr;
  }
}
</style>
