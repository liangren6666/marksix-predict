<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, DataZoomComponent } from 'echarts/components'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent, DataZoomComponent])

const props = defineProps({
  freq: { type: Object, required: true },
  title: { type: String, default: '' },
  highlight: { type: Array, default: () => [] },
})

const option = computed(() => {
  const labels = [...Array(49)].map((_, i) => String(i + 1).padStart(2, '0'))
  const data = labels.map((_, i) => props.freq[i + 1] || 0)
  const hi = new Set(props.highlight)
  return {
    title: props.title ? { text: props.title, left: 0, textStyle: { color: '#8b97ab', fontSize: 13 } } : undefined,
    grid: { left: 40, right: 12, top: props.title ? 36 : 16, bottom: 56 },
    tooltip: { trigger: 'axis' },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 8 }],
    xAxis: {
      type: 'category',
      data: labels,
      axisLabel: { color: '#8b97ab', fontSize: 10, interval: 1 },
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
        data: data.map((v, i) => ({
          value: v,
          itemStyle: {
            color: hi.has(i + 1) ? '#d4a84b' : '#5b8def',
            borderRadius: [3, 3, 0, 0],
            opacity: hi.has(i + 1) ? 1 : 0.85,
          },
        })),
        barMaxWidth: 14,
      },
    ],
  }
})
</script>

<template>
  <div class="chart-wrap">
    <VChart class="chart" :option="option" autoresize />
  </div>
</template>
