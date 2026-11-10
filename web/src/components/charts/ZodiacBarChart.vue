<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent])

const props = defineProps({
  items: { type: Array, default: () => [] },
})

const option = computed(() => ({
  grid: { left: 48, right: 12, top: 12, bottom: 28 },
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'category',
    data: props.items.map((x) => x.name),
    axisLabel: { color: '#8b97ab' },
    axisLine: { lineStyle: { color: '#2a3344' } },
  },
  yAxis: {
    type: 'value',
    axisLabel: { color: '#8b97ab' },
    splitLine: { lineStyle: { color: '#1f2836' } },
  },
  series: [
    {
      type: 'bar',
      data: props.items.map((x) => x.value),
      itemStyle: { color: '#43c07a', borderRadius: [4, 4, 0, 0] },
      barMaxWidth: 28,
    },
  ],
}))
</script>

<template>
  <div class="chart-wrap">
    <VChart class="chart" :option="option" autoresize />
  </div>
</template>
