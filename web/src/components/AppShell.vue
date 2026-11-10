<script setup>
import { computed, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useLotteryStore } from '../stores/lottery'

const store = useLotteryStore()
const route = useRoute()
const navigation = [
  { name: 'next', label: '日期预测', icon: 'M4 4h6v6H4z M14 4h6v6h-6z M4 14h6v6H4z M14 14h6v6h-6z' },
  { name: 'overview', label: '开奖总览', icon: 'M4 19V5 M4 19h16 M8 15l4-5 3 2 5-6' },
  { name: 'history', label: '历史查询', icon: 'M4 5h16v15H4z M4 9h16 M8 3v4 M16 3v4 M8 13h3 M13 13h3 M8 16h3' },
  { name: 'frequency', label: '号码分析', icon: 'M5 19v-5h3v5z M10.5 19V9h3v10z M16 19V5h3v14z' },
  { name: 'compare', label: '三彩对比', icon: 'M4 7h16 M4 12h16 M4 17h16 M8 5v4 M15 10v4 M10 15v4' },
  { name: 'models', label: '特码回测', icon: 'M4 18V6 M4 18h16 M8 14l3-3 3 1 5-6 M15 6h4v4' },
]

const title = computed(() => navigation.find((item) => item.name === route.name)?.label || '数据工作台')
const isForecast = computed(() => route.name === 'next')
const usesLottery = computed(() => ['overview', 'history', 'frequency'].includes(route.name))

watch(usesLottery, (needed) => {
  if (needed) store.load()
}, { immediate: true })
</script>

<template>
  <div class="shell">
    <a class="skip-link" href="#main-content">跳转到内容</a>
    <aside class="rail">
      <RouterLink :to="{ name: 'next' }" class="brand">
        <svg class="brand-mark" viewBox="0 0 36 36" aria-hidden="true">
          <rect width="36" height="36" rx="9" fill="currentColor" />
          <circle cx="12" cy="12" r="3.5" /><circle cx="24" cy="12" r="3.5" />
          <circle cx="12" cy="24" r="3.5" /><circle cx="24" cy="24" r="3.5" />
        </svg>
        <span><strong>六合数据台</strong><small>开奖研究</small></span>
      </RouterLink>

      <nav class="nav" aria-label="主导航">
        <RouterLink v-for="item in navigation" :key="item.name" :to="{ name: item.name }" class="nav-link">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="item.icon" /></svg>
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="rail-source">
        <label v-if="usesLottery" class="lottery-label">
          <span>查看彩种</span>
          <select :value="store.activeKey" @change="store.setActive($event.target.value)">
            <option v-for="(info, key) in store.LOTTERIES" :key="key" :value="key">{{ info.label }}</option>
          </select>
        </label>
        <template v-else>
          <span class="source-label">数据来源</span>
          <span class="source-detail">本地校验记录</span>
        </template>
      </div>
    </aside>

    <main id="main-content" class="main" tabindex="-1">
      <header class="topbar">
        <div class="breadcrumb"><span>工作区</span><span aria-hidden="true">/</span><strong>{{ title }}</strong></div>
        <span class="local-indicator"><i aria-hidden="true"></i>本地数据</span>
      </header>
      <div class="content">
        <header v-if="!isForecast" class="page-heading">
          <h1>{{ title }}</h1>
          <p v-if="usesLottery">{{ store.meta.label }}<span v-if="store.draws.length"> · {{ store.draws.length }} 期记录</span></p>
          <p v-if="usesLottery && store.error" role="alert">{{ store.error }} <button type="button" @click="store.load()">重试</button></p>
          <p v-else-if="usesLottery && store.loading" role="status">正在加载开奖记录…</p>
        </header>
        <slot />
      </div>
    </main>
  </div>
</template>

<style scoped>
.shell { display: grid; grid-template-columns: 218px minmax(0, 1fr); min-height: 100vh; }
.rail {
  display: flex; flex-direction: column; min-width: 0; position: sticky; top: 0;
  height: 100dvh; padding: 25px 16px 20px; border-right: 1px solid var(--border); background: var(--bg);
}
.brand { display: flex; align-items: center; gap: 11px; padding: 0 8px; text-decoration: none; color: var(--text); }
.brand-mark { width: 36px; height: 36px; color: var(--accent); flex: none; }
.brand-mark circle { fill: var(--accent-ink); }
.brand strong, .brand small { display: block; }
.brand strong { font-size: 1rem; letter-spacing: .03em; }
.brand small { margin-top: 1px; color: var(--text-muted); font-size: .79rem; }
.nav { display: flex; flex-direction: column; gap: 5px; margin-top: 34px; }
.nav-link {
  display: flex; align-items: center; gap: 11px; padding: 11px 12px; min-height: 44px;
  color: var(--text-muted); text-decoration: none; white-space: nowrap;
  font-size: .92rem; border-radius: 8px; font-weight: 600;
}
.nav-link svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 1.65; stroke-linecap: round; stroke-linejoin: round; flex: none; }
.nav-link:hover { color: var(--text); background: var(--panel-raised); }
.nav-link.router-link-exact-active { background: var(--accent-dim); color: var(--accent); }
.rail-source { margin-top: auto; padding: 16px 8px 4px; border-top: 1px solid var(--border); }
.source-label, .lottery-label > span { display: block; margin-bottom: 5px; color: var(--text-muted); font-size: .8rem; }
.source-detail { color: var(--text); font-size: .87rem; }
.lottery-label select { width: 100%; min-height: 36px; border: 1px solid var(--border); border-radius: 7px; padding: 4px 8px; background: var(--panel-raised); color: var(--text); }
.main { min-width: 0; outline: none; }
.topbar { min-height: 62px; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 34px; border-bottom: 1px solid var(--border); }
.breadcrumb { display: flex; align-items: center; gap: 10px; color: var(--text-muted); font-size: .84rem; }
.breadcrumb strong { color: var(--text); font-weight: 600; }
.local-indicator { display: inline-flex; align-items: center; gap: 7px; color: var(--text-muted); font-size: .81rem; white-space: nowrap; }
.local-indicator i { background: #7fc7a0; border-radius: 50%; width: 6px; height: 6px; }
.content { width: min(100%, 1370px); margin-inline: auto; padding: 27px 34px 36px; display: flex; flex-direction: column; gap: 16px; }
.page-heading h1 { margin: 0; font-size: 1.85rem; letter-spacing: -.025em; }
.page-heading p { margin: 6px 0 0; color: var(--text-muted); }
.page-heading button { border: 0; background: transparent; color: var(--accent); cursor: pointer; }
.skip-link { position: fixed; inset: 8px auto auto 8px; z-index: 10; padding: 8px 14px; background: var(--accent); color: var(--accent-ink); transform: translateY(-150%); }
.skip-link:focus { transform: translateY(0); }

@media (max-width: 980px) {
  .shell { grid-template-columns: 170px minmax(0, 1fr); }
  .rail { padding-inline: 11px; }
  .topbar, .content { padding-inline: 23px; }
}
@media (max-width: 760px) {
  .shell { grid-template-columns: minmax(0, 1fr); }
  .rail { position: static; height: auto; padding: 15px 16px 0; border-right: 0; border-bottom: 1px solid var(--border); }
  .brand { padding: 0; }
  .brand-mark { width: 32px; height: 32px; }
  .brand small { display: none; }
  .nav { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 4px; padding-bottom: 8px; margin: 11px 0 0; }
  .nav-link { justify-content: center; min-height: 40px; gap: 5px; padding-inline: 5px; font-size: .85rem; }
  .nav-link svg { width: 14px; height: 14px; }
  .rail-source { padding: 0; border: 0; }
  .rail-source > span { display: none; }
  .lottery-label { display: flex; align-items: center; gap: 12px; padding: 6px 0 12px; }
  .lottery-label > span { margin: 0; white-space: nowrap; }
  .lottery-label select { max-width: 200px; font-size: 1rem; }
  .topbar { display: none; }
  .topbar, .content { padding-inline: 16px; }
  .content { padding-top: 20px; }
}
</style>
