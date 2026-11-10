<script setup>
import { COLOR_MAP } from '../lib/lotteryMeta'

defineProps({
  draws: { type: Array, default: () => [] },
  limit: { type: Number, default: 24 },
})

function specialColor(draw) {
  const c = draw.colors?.[6]
  return COLOR_MAP[c] || 'var(--text-muted)'
}
</script>

<template>
  <ul class="list">
    <li v-for="d in draws.slice(0, limit)" :key="d.issue">
      <span class="issue mono">{{ d.issue }}</span>
      <span
        class="special-ball mono"
        :style="{ background: specialColor(d), boxShadow: `0 0 0 2px ${specialColor(d)}44` }"
      >
        {{ String(d.special).padStart(2, '0') }}
      </span>
      <span class="sum mono">和 {{ d.all.reduce((a, b) => a + b, 0) }}</span>
    </li>
  </ul>
  <p v-if="!draws.length" class="empty">暂无数据</p>
</template>

<style scoped>
.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  max-height: 360px;
  overflow: auto;
}

li {
  display: grid;
  grid-template-columns: 6.5rem 2.5rem 1fr;
  align-items: center;
  gap: 0.65rem;
  padding: 0.35rem 0.15rem;
  border-bottom: 1px solid var(--border);
  font-size: 0.85rem;
}

.issue {
  color: var(--text-muted);
}

.special-ball {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
  color: #fff;
}

.sum {
  color: var(--text-muted);
  font-size: 0.8rem;
}

.empty {
  margin: 0;
  padding: 1.5rem;
  text-align: center;
  color: var(--text-muted);
}
</style>
