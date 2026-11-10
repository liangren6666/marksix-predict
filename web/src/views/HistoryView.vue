<script setup>
import { computed, ref } from 'vue'
import { useLotteryStore } from '../stores/lottery'
import IssueTable from '../components/IssueTable.vue'
import BallStrip from '../components/BallStrip.vue'

const store = useLotteryStore()
const pageSize = 40
const page = ref(1)
const selected = ref(null)

const paged = computed(() => {
  const start = (page.value - 1) * pageSize
  return store.filteredDraws.slice(start, start + pageSize)
})

const totalPages = computed(() =>
  Math.max(1, Math.ceil(store.filteredDraws.length / pageSize)),
)

function onSelect(row) {
  selected.value = row
}
</script>

<template>
  <section class="toolbar panel">
    <label class="search">
      <span>期号搜索</span>
      <input v-model="store.searchIssue" type="search" placeholder="如 2026312" />
    </label>
    <label>
      <span>年份</span>
      <select v-model="store.yearFilter">
        <option :value="null">全部</option>
        <option v-for="y in store.years" :key="y" :value="y">{{ y }}</option>
      </select>
    </label>
    <p class="count mono">匹配 {{ store.filteredDraws.length }} 期</p>
  </section>

  <section class="layout">
    <article class="panel table-panel">
      <IssueTable
        :rows="paged"
        :show-meta="store.meta.hasMeta"
        @select="onSelect"
      />
      <footer class="pager">
        <button type="button" :disabled="page <= 1" @click="page--">上一页</button>
        <span class="mono">{{ page }} / {{ totalPages }}</span>
        <button type="button" :disabled="page >= totalPages" @click="page++">下一页</button>
      </footer>
    </article>

    <aside v-if="selected" class="panel detail">
      <p class="eyebrow">期号详情</p>
      <h2 class="mono">{{ selected.issue }}</h2>
      <BallStrip :nums="selected.all" :colors="selected.colors" />
      <dl>
        <div v-if="selected.openTime">
          <dt>开奖时间</dt>
          <dd>{{ selected.openTime }}</dd>
        </div>
        <div>
          <dt>和值</dt>
          <dd class="mono">{{ selected.all.reduce((a, b) => a + b, 0) }}</dd>
        </div>
        <div v-if="selected.verifyStatus">
          <dt>校验状态</dt>
          <dd>{{ selected.verifyStatus }}</dd>
        </div>
        <div v-if="selected.zodiacs.length">
          <dt>生肖</dt>
          <dd>{{ selected.zodiacs.join(' · ') }}</dd>
        </div>
      </dl>
    </aside>
  </section>
</template>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: flex-end;
  padding: 0.85rem 1rem;
}

.search input,
select {
  padding: 0.45rem 0.55rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--panel-raised);
  color: var(--text);
  min-width: 180px;
}

label {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.count {
  margin: 0;
  margin-left: auto;
  color: var(--text-muted);
  font-size: 0.85rem;
}

.layout {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 0.85rem;
  align-items: start;
}

.table-panel {
  padding: 0.5rem 0.75rem 0.75rem;
}

.pager {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border);
  margin-top: 0.5rem;
}

.pager button {
  padding: 0.35rem 0.75rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--panel-raised);
  color: var(--text);
  cursor: pointer;
}

.pager button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.detail {
  padding: 1.1rem;
  position: sticky;
  top: 1rem;
}

.eyebrow {
  margin: 0;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.detail h2 {
  margin: 0.35rem 0 1rem;
  color: var(--accent);
}

dl {
  margin: 1rem 0 0;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

dt {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
}

dd {
  margin: 0.15rem 0 0;
  font-size: 0.9rem;
}

@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }
  .detail {
    position: static;
  }
}
</style>
