<script setup>
import BallStrip from './BallStrip.vue'

defineProps({
  rows: { type: Array, required: true },
  showMeta: { type: Boolean, default: true },
})

const emit = defineEmits(['select'])
</script>

<template>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>期号</th>
          <th>开奖号码</th>
          <th v-if="showMeta">和值</th>
          <th v-if="showMeta">校验</th>
          <th v-else>开奖时间</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in rows"
          :key="row.issue"
          tabindex="0"
          @click="emit('select', row)"
          @keyup.enter="emit('select', row)"
        >
          <td class="mono issue">{{ row.issue }}</td>
          <td>
            <BallStrip :nums="row.all" :colors="row.colors" compact />
          </td>
          <td v-if="showMeta" class="mono sum">
            {{ row.all.reduce((a, b) => a + b, 0) }}
          </td>
          <td v-if="showMeta" class="verify">
            <span class="tag">{{ row.verifyStatus || '—' }}</span>
          </td>
          <td v-else class="time">{{ row.openTime || '—' }}</td>
        </tr>
      </tbody>
    </table>
    <p v-if="!rows.length" class="empty">没有匹配记录</p>
  </div>
</template>

<style scoped>
.table-wrap {
  overflow: auto;
  max-height: 520px;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}

th,
td {
  padding: 0.65rem 0.75rem;
  text-align: left;
  border-bottom: 1px solid var(--border);
}

th {
  position: sticky;
  top: 0;
  background: var(--panel-raised);
  color: var(--text-muted);
  font-weight: 500;
  z-index: 1;
}

tbody tr {
  cursor: pointer;
  transition: background 0.15s;
}

tbody tr:hover,
tbody tr:focus-visible {
  background: rgba(255, 255, 255, 0.04);
  outline: none;
}

.issue {
  white-space: nowrap;
  font-weight: 500;
}

.sum,
.time {
  color: var(--text-muted);
}

.tag {
  display: inline-block;
  padding: 0.15rem 0.45rem;
  border-radius: 6px;
  font-size: 0.72rem;
  background: var(--accent-dim);
  color: var(--accent);
}

.empty {
  text-align: center;
  padding: 2rem;
  color: var(--text-muted);
}
</style>
