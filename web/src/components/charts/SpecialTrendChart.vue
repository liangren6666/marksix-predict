<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent])

const props = defineProps({
  draws: { type: Array, default: () => [] },
  limit: { type: Number, default: 120 },
})

const option = computed(() => {
  const slice = [...props.draws].slice(0, props.limit).reverse()
  return {
    grid: { left: 44, right: 16, top: 20, bottom: 32 },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: slice.map((d) => d.seq),
      axisLabel: { color: '#8b97ab', fontSize: 10 },
      axisLine: { lineStyle: { color: '#2a3344' } },
    },
    yAxis: {
      type: 'value',
      min: 1,
      max: 49,
      axisLabel: { color: '#8b97ab' },
      splitLine: { lineStyle: { color: '#1f2836' } },
    },
    series: [
      {
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        data: slice.map((d) => d.special),
        lineStyle: { color: '#d4a84b', width: 2 },
        itemStyle: { color: '#d4a84b' },
        areaStyle: { color: 'rgba(212,168,75,0.12)' },
      },
    ],
  }
})
</script>

<template>
  <VChart class="chart" :option="option" autoresize />
</template>
