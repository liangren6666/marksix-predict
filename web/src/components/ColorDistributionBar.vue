<script setup>
import { computed } from 'vue'
import { COLOR_MAP } from '../lib/lotteryMeta'

const props = defineProps({
  items: { type: Array, default: () => [] },
})

const LABEL = { red: '红波', blue: '蓝波', green: '绿波' }

const rows = computed(() => {
  const total = props.items.reduce((s, x) => s + x.value, 0) || 1
  return props.items
    .filter((x) => COLOR_MAP[x.name])
    .map((x) => ({
      key: x.name,
      label: LABEL[x.name] || x.name,
      value: x.value,
      pct: Math.round((x.value / total) * 1000) / 10,
      color: COLOR_MAP[x.name],
    }))
    .sort((a, b) => b.value - a.value)
})
</script>

<template>
  <div v-if="rows.length" class="bars">
    <div v-for="row in rows" :key="row.key" class="row">
      <span class="label">{{ row.label }}</span>
      <div class="track">
        <div class="fill" :style="{ width: `${row.pct}%`, background: row.color }" />
      </div>
      <span class="pct mono">{{ row.pct }}%</span>
      <span class="count mono">{{ row.value }}</span>
    </div>
  </div>
  <p v-else class="empty">无波色统计数据</p>
</template>

<style scoped>
.bars {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  padding: 0.25rem 0;
}

.row {
  display: grid;
  grid-template-columns: 3rem 1fr 3rem 3.5rem;
  gap: 0.65rem;
  align-items: center;
  font-size: 0.85rem;
}

.label {
  color: var(--text-muted);
}

.track {
  height: 8px;
  border-radius: 999px;
  background: var(--panel-raised);
  overflow: hidden;
}

.fill {
  height: 100%;
  border-radius: 999px;
  min-width: 2px;
}

.pct {
  text-align: right;
  color: var(--accent);
  font-weight: 600;
}

.count {
  text-align: right;
  color: var(--text-muted);
  font-size: 0.8rem;
}

.empty {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.88rem;
  padding: 1rem 0;
}
</style>
