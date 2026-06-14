<template>
  <div v-if="hasData" class="bg-white border border-slate-200 rounded-xl p-4 shadow-lg glow-border-sky">
    <h3 class="text-slate-800 text-base font-semibold mb-3 flex items-center gap-2">
      <span class="w-1.5 h-1.5 rounded-full bg-sky-500 animate-pulse"></span>
      下肢关节负荷分析
      <span class="text-xs text-slate-400 font-normal ml-auto">{{ asymmetryText }}</span>
    </h3>
    <div ref="chartRef" class="w-full" style="height:220px"></div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  muscleLoad: { type: Object, default: null },
})

const chartRef = ref(null)
let chart = null

const hasData = computed(() => {
  if (!props.muscleLoad) return false
  const m = props.muscleLoad
  return !!(m.leftHip || m.rightHip || m.leftKnee || m.rightKnee)
})

const asymmetryText = computed(() => {
  const idx = props.muscleLoad?.asymmetryIdx
  if (idx == null) return ''
  if (idx < 0.1) return '左右均衡'
  if (idx < 0.2) return '轻度不对称'
  return '明显不对称'
})

function buildOption() {
  const m = props.muscleLoad || {}
  const categories = ['左髋', '右髋', '左膝', '右膝']
  const keys = ['leftHip', 'rightHip', 'leftKnee', 'rightKnee']
  const values = keys.map(k => m[k]?.load ?? 0)
  const details = keys.map(k => m[k]?.detail ?? '')

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const i = params[0]?.dataIndex ?? 0
        return `${params[0]?.name}<br/>负荷指数: ${params[0]?.value}<br/>${details[i] || ''}`
      },
    },
    grid: { top: 16, bottom: 20, left: 60, right: 30 },
    xAxis: {
      type: 'value',
      name: '负荷指数',
      max: 100,
      axisLabel: { color: '#94a3b8', fontSize: 10 },
      splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } },
    },
    yAxis: {
      type: 'category',
      data: categories,
      axisLabel: { color: '#475569', fontSize: 11 },
      axisLine: { lineStyle: { color: '#334155' } },
    },
    series: [
      {
        type: 'bar',
        data: values.map((v, i) => ({
          value: v,
          itemStyle: {
            color: i % 2 === 0
              ? new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                  { offset: 0, color: '#38bdf8' }, { offset: 1, color: '#0ea5e9' },
                ])
              : new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                  { offset: 0, color: '#f59e0b' }, { offset: 1, color: '#d97706' },
                ]),
            borderRadius: [0, 4, 4, 0],
          },
        })),
        barWidth: 22,
        label: { show: true, position: 'right', color: '#64748b', fontSize: 10, formatter: '{c}' },
      },
    ],
  }
}

function render() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption(buildOption(), true)
}

onMounted(() => { render() })
watch(() => props.muscleLoad, () => { render() })
onBeforeUnmount(() => { chart?.dispose() })
</script>
