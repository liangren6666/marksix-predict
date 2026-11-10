import { createRouter, createWebHashHistory } from 'vue-router'
import NextReferenceView from '../views/NextReferenceView.vue'

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: '/', alias: '/next', name: 'next', component: NextReferenceView },
    { path: '/overview', name: 'overview', component: () => import('../views/OverviewView.vue') },
    { path: '/history', name: 'history', component: () => import('../views/HistoryView.vue') },
    { path: '/frequency', name: 'frequency', component: () => import('../views/FrequencyView.vue') },
    { path: '/compare', name: 'compare', component: () => import('../views/CompareView.vue') },
    { path: '/models', name: 'models', component: () => import('../views/ModelsView.vue') },
  ],
})

export default router
