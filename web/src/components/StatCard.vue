<script setup>
defineProps({
  label: String,
  value: [String, Number],
  hint: String,
})
</script>

<template>
  <article class="stat panel">
    <p class="label">{{ label }}</p>
    <p class="value mono">{{ value }}</p>
    <p v-if="hint" class="hint">{{ hint }}</p>
  </article>
</template>

<style scoped>
.stat {
  padding: 1rem 1.1rem;
}

.label {
  margin: 0;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
}

.value {
  margin: 0.35rem 0 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--accent);
}

.hint {
  margin: 0.4rem 0 0;
  font-size: 0.8rem;
  color: var(--text-muted);
}
</style>
