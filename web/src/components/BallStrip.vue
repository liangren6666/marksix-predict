<script setup>
import { COLOR_MAP } from '../lib/lotteryMeta'

defineProps({
  nums: { type: Array, required: true },
  colors: { type: Array, default: () => [] },
  compact: Boolean,
})

function ballStyle(color, n) {
  const c = COLOR_MAP[color] || 'var(--panel-raised)'
  return {
    '--ball-bg': c,
    '--ball-ring': `${c}55`,
  }
}
</script>

<template>
  <div class="balls" :class="{ compact }">
    <template v-for="(n, i) in nums" :key="`${n}-${i}`">
      <span v-if="i === 6" class="plus">+</span>
      <span
        class="ball"
        :class="{ special: i === 6 }"
        :style="ballStyle(colors[i], n)"
      >
        {{ String(n).padStart(2, '0') }}
      </span>
    </template>
  </div>
</template>

<style scoped>
.balls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
}

.ball {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 2.1rem;
  height: 2.1rem;
  padding: 0 0.35rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
  background: var(--ball-bg, var(--panel-raised));
  box-shadow:
    0 0 0 2px var(--ball-ring, rgba(255, 255, 255, 0.08)),
    0 4px 12px rgba(0, 0, 0, 0.25);
  color: #fff;
}

.ball.special {
  transform: scale(1.05);
}

.plus {
  color: var(--text-muted);
  font-weight: 600;
  padding: 0 0.15rem;
}

.compact .ball {
  min-width: 1.75rem;
  height: 1.75rem;
  font-size: 0.72rem;
}
</style>
