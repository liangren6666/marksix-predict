<script setup>
import BallStrip from './BallStrip.vue'

defineProps({
  draws: { type: Array, default: () => [] },
  limit: { type: Number, default: 12 },
})
</script>

<template>
  <ul class="list">
    <li v-for="d in draws.slice(0, limit)" :key="d.issue">
      <div class="head">
        <span class="issue mono">{{ d.issue }}</span>
        <time v-if="d.openTime">{{ d.openTime }}</time>
      </div>
      <BallStrip :nums="d.all" compact />
    </li>
  </ul>
</template>

<style scoped>
.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  max-height: 380px;
  overflow: auto;
}

.head {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
  font-size: 0.8rem;
}

.issue {
  color: var(--accent);
  font-weight: 600;
}

time {
  color: var(--text-muted);
}
</style>
