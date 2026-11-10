<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { COLOR_MAP } from '../../lib/lotteryMeta'

use([CanvasRenderer, PieChart, TooltipComponent, LegendComponent])

const props = defineProps({
  items: { type: Array, default: () => [] },
})

const option = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0, textStyle: { color: '#8b97ab' } },
  series: [
    {
      type: 'pie',
      radius: ['42%', '68%'],
      label: { color: '#eef1f7' },
      data: props.items.map((x) => ({
        name: { red: '红', blue: '蓝', green: '绿' }[x.name] || x.name,
        value: x.value,
        itemStyle: { color: COLOR_MAP[x.name] || '#666' },
      })),
    },
  ],
}))
</script>

<template>
  <div class="chart-wrap">
    <VChart class="chart" :option="option" autoresize />
  </div>
</template>
