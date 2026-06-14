<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-lg glow-border-sky flex flex-col h-full">
    <h3 class="text-slate-800 text-base font-semibold mb-3 flex items-center justify-between">
      <span class="flex items-center gap-2">
        <span class="w-1.5 h-1.5 rounded-full bg-sky-500 animate-pulse"></span>
        综合技巧评估
      </span>
    </h3>

    <!-- 只有一个图表时用单列，两个都有时用双列 -->
    <div class="flex-1 min-h-0" :class="hasBoth ? 'grid grid-cols-2 gap-3' : ''">
      <div v-if="hasRadarData" class="flex flex-col h-full">
        <p class="text-xs text-slate-400 mb-1">能力雷达</p>
        <div ref="radarChartRef" class="flex-1 min-h-0 bg-sky-50 rounded-lg border border-slate-200/60 aspect-square mx-auto w-full" style="max-width:320px"></div>
      </div>

      <div v-if="hasTrendData" class="flex flex-col h-full">
        <p class="text-xs text-slate-400 mb-1">移动速度趋势</p>
        <div class="flex gap-2 text-[10px] mb-1">
          <span class="flex items-center gap-1"><span class="w-2 h-0.5 bg-sky-400"></span>平均移速</span>
          <span class="flex items-center gap-1"><span class="w-2 h-0.5 bg-emerald-400"></span>步频</span>
        </div>
        <div ref="lineChartRef" class="flex-1 min-h-0 bg-sky-50 rounded-lg border border-slate-200/60"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'
import { tooltipTheme } from '../../utils/chartTheme.js'

const isDev = import.meta.env.DEV

const props = defineProps({
  radarOption: Object,
  speedTrendOption: Object,
})

const radarChartRef = ref(null)
const lineChartRef = ref(null)
let radarChart = null
let lineChart = null

const hasRadarData = computed(() => !!props.radarOption)
const hasTrendData = computed(() => !!props.speedTrendOption)
const hasBoth = computed(() => hasRadarData.value && hasTrendData.value)

function mockRadarChart() {
  return {
    tooltip: tooltipTheme('item'),
    radar: {
      center: ['50%', '52%'], radius: '60%',
      indicator: ['爆发力', '速度', '敏捷性', '稳定性', '耐力'].map(name => ({ name, max: 100 })),
      axisName: { color: '#94a3b8', fontSize: 11 },
      axisLine: { lineStyle: { color: '#334155' } },
      splitLine: { lineStyle: { color: '#e2e8f0' } },
      splitArea: { areaStyle: { color: ['#f8fafc', '#f1f5f9'] } },
    },
    series: [{
      type: 'radar', data: [{ value: [85, 78, 92, 69, 81], name: '步伐指标', symbol: 'circle', symbolSize: 4,
        itemStyle: { color: '#38bdf8' }, lineStyle: { color: '#38bdf8', width: 1.5 },
        areaStyle: { color: 'rgba(56,189,248,0.15)' },
      }],
    }],
  }
}

function mockSpeedTrendChart() {
  return {
    tooltip: tooltipTheme(),
    grid: { top: 12, bottom: 28, left: 48, right: 16 },
    xAxis: { type: 'category', data: ['03/01', '03/02', '03/03', '03/04', '03/05'],
      axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#475569', fontSize: 11 }, axisTick: { show: false } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } },
      axisLabel: { color: '#475569', fontSize: 11 }, axisLine: { show: false } },
    series: [
      { name: '平均移速', type: 'line', smooth: true, symbol: 'circle', symbolSize: 4,
        data: [320, 450, 410, 520, 490], itemStyle: { color: '#38bdf8' }, lineStyle: { width: 2 },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(56,189,248,0.25)' }, { offset: 1, color: 'rgba(56,189,248,0.02)' }] } } },
      { name: '步频', type: 'line', smooth: true, symbol: 'circle', symbolSize: 4,
        data: [210, 310, 290, 400, 370], itemStyle: { color: '#10b981' }, lineStyle: { width: 2 },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(16,185,129,0.25)' }, { offset: 1, color: 'rgba(16,185,129,0.02)' }] } } },
    ],
  }
}

function renderCharts() {
  if (radarChartRef.value) {
    if (!radarChart) radarChart = echarts.init(radarChartRef.value)
    if (props.radarOption) radarChart.setOption(props.radarOption, true)
    else if (isDev) radarChart.setOption(mockRadarChart(), true)
  }
  if (lineChartRef.value) {
    if (!lineChart) lineChart = echarts.init(lineChartRef.value)
    if (props.speedTrendOption) lineChart.setOption(props.speedTrendOption, true)
    else if (isDev) lineChart.setOption(mockSpeedTrendChart(), true)
  }
}

onMounted(() => { renderCharts() })
watch(() => [props.radarOption, props.speedTrendOption], () => { renderCharts() })

onBeforeUnmount(() => {
  radarChart?.dispose()
  lineChart?.dispose()
})
</script>
