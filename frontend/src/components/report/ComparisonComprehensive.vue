<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-lg glow-border-sky">
    <h3 class="text-slate-800 text-base font-semibold mb-3 flex items-center gap-2">
      <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
      七、对比与综合分析
      <span class="text-xs bg-slate-100 text-slate-400 px-2 py-0.5 rounded-full ml-auto">综合评估</span>
    </h3>
    <p class="text-sm text-slate-400 leading-relaxed mb-3 border-l-2 border-emerald-500/30 pl-2.5">运动员对比显示个体间差异主要集中在总耗时和最大悬空时间。平行坐标图揭示了不同移动段在各维度的分布特征，部分段在速度与DSO维度出现异常值。对称性散点图中多数指标点靠近对角线，个别点偏离明显提示可能存在双侧不平衡，建议针对偏离指标进行单侧强化训练。</p>
    <!-- 运动员对比仪表板 -->
    <div class="mb-3 bg-sky-50 rounded-lg border border-slate-200/60 p-2">
      <p class="text-sm text-slate-400 mb-1 font-medium">运动员综合指标对比</p>
      <div ref="dashRef" class="w-full h-56"></div>
    </div>
    <!-- Row: 平行坐标 + 对称性 -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">各移动段参数平行坐标图</p>
        <div ref="paraRef" class="w-full h-64"></div>
      </div>
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">左右腿对称性分析</p>
        <div ref="symRef" class="w-full h-64"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'
import { tooltipTheme } from '../../utils/chartTheme.js'

const props = defineProps({
  downloads: { type: Array, default: () => [] },
  symmetry: Object,
  parallelCoords: Object
})

const dashRef = ref(null)
const paraRef = ref(null)
const symRef = ref(null)
const charts = []

function db() { return { axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#475569', fontSize: 10 }, splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } } } }

function mockDownloads() {
  const athletes = ['A', 'B', 'C', 'D', 'E']
  const time = [8.2, 7.6, 9.1, 7.9, 8.5]
  const dist = [16.5, 18.2, 14.8, 17.1, 15.9]
  const avgV = [2.01, 2.39, 1.63, 2.16, 1.87]
  const maxFly = [0.18, 0.22, 0.14, 0.19, 0.16]
  const kliMax = [0.55, 0.48, 0.62, 0.51, 0.58]
  const colors2 = ['#38bdf8', '#10b981', '#f59e0b', '#6366f1', '#ef4444']
  const mk5 = (data) => data.map((v, i) => ({ value: v, itemStyle: { color: colors2[i] } }))
  return {
    tooltip: tooltipTheme(),
    baseOption: {
      timeline: { axisType: 'category', data: ['总耗时', '总距离', '平均速度', '最大悬空', 'KLI最大值'], label: { color: '#94a3b8', fontSize: 11 }, lineStyle: { color: '#334155' }, itemStyle: { color: '#334155' }, checkpointStyle: { color: '#38bdf8' }, controlStyle: { color: '#38bdf8', borderColor: '#38bdf8' } },
      xAxis: { type: 'category', data: athletes, axisLabel: { color: '#94a3b8', fontSize: 10 }, ...db() },
      yAxis: { type: 'value', ...db() },
      grid: { top: 30, bottom: 30, left: 50, right: 10 }
    },
    options: [
      { title: { text: '总耗时(s)', textStyle: { color: '#94a3b8', fontSize: 10 } }, series: [{ type: 'bar', data: mk5(time), barWidth: '40%' }] },
      { title: { text: '移动总距离(m)', textStyle: { color: '#94a3b8', fontSize: 10 } }, series: [{ type: 'bar', data: mk5(dist), barWidth: '40%' }] },
      { title: { text: '平均速度(m/s)', textStyle: { color: '#94a3b8', fontSize: 10 } }, series: [{ type: 'bar', data: mk5(avgV), barWidth: '40%' }] },
      { title: { text: '最大悬空时间(s)', textStyle: { color: '#94a3b8', fontSize: 10 } }, series: [{ type: 'bar', data: mk5(maxFly), barWidth: '40%' }] },
      { title: { text: 'KLI最大值', textStyle: { color: '#94a3b8', fontSize: 10 } }, series: [{ type: 'bar', data: mk5(kliMax), barWidth: '40%' }, { type: 'line', markLine: { silent: true, symbol: 'none', lineStyle: { color: '#ef4444', type: 'dashed' }, label: { color: '#ef4444', fontSize: 10, formatter: '风险阈值0.6' }, data: [{ yAxis: 0.6 }] }, data: [], lineStyle: { opacity: 0 }, itemStyle: { opacity: 0 } }] }
    ]
  }
}

function mockParallelCoords() {
  const pdata = [
    [0.8, 2.5, 2.8, 2.1, 65, 1],
    [0.6, 2.0, 3.5, 2.5, 58, 2],
    [1.0, 3.1, 2.2, 1.8, 72, 3],
    [0.7, 2.3, 3.1, 2.3, 62, 4],
    [0.9, 2.8, 2.6, 2.0, 68, 5],
    [0.5, 1.8, 3.8, 2.7, 55, 6],
    [0.75, 2.6, 2.9, 2.2, 64, 7],
    [0.85, 2.7, 2.4, 1.9, 70, 8]
  ]
  return {
    tooltip: tooltipTheme(),
    parallelAxis: [
      { dim: 0, name: '耗时(s)', nameTextStyle: { color: '#94a3b8', fontSize: 11 }, axisLabel: { color: '#475569', fontSize: 10 }, axisLine: { lineStyle: { color: '#334155' } } },
      { dim: 1, name: '距离(m)', nameTextStyle: { color: '#94a3b8', fontSize: 11 }, axisLabel: { color: '#475569', fontSize: 10 }, axisLine: { lineStyle: { color: '#334155' } } },
      { dim: 2, name: '最大速度(m/s)', nameTextStyle: { color: '#94a3b8', fontSize: 11 }, axisLabel: { color: '#475569', fontSize: 10 }, axisLine: { lineStyle: { color: '#334155' } } },
      { dim: 3, name: '平均速度(m/s)', nameTextStyle: { color: '#94a3b8', fontSize: 11 }, axisLabel: { color: '#475569', fontSize: 10 }, axisLine: { lineStyle: { color: '#334155' } } },
      { dim: 4, name: 'DSO(%)', nameTextStyle: { color: '#94a3b8', fontSize: 11 }, axisLabel: { color: '#475569', fontSize: 10 }, axisLine: { lineStyle: { color: '#334155' } } }
    ],
    parallel: { left: 5, right: 5, top: 20, bottom: 20 },
    series: [{
      type: 'parallel', data: pdata,
      lineStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#3b82f6' }, { offset: 0.5, color: '#38bdf8' }, { offset: 1, color: '#10b981' }]), width: 1.5, opacity: 0.7 }
    }]
  }
}

function mockSymmetry() {
  const symPts = []
  for (let i = 0; i < 20; i++) { const v = +(1 + Math.random() * 8).toFixed(1); const offset = (Math.random() - 0.5) * 1.5; symPts.push([+(v - offset).toFixed(1), +(v + offset).toFixed(1)]) }
  const maxV = 10
  return {
    tooltip: tooltipTheme(),
    grid: { top: 22, bottom: 22, left: 50, right: 15 },
    xAxis: { type: 'value', name: '左腿指标', nameTextStyle: { color: '#64748b', fontSize: 11 }, min: 0, max: maxV, ...db() },
    yAxis: { type: 'value', name: '右腿指标', nameTextStyle: { color: '#64748b', fontSize: 11 }, min: 0, max: maxV, ...db() },
    series: [
      { type: 'scatter', data: symPts, symbolSize: 8, itemStyle: { color: '#38bdf8', shadowBlur: 3, shadowColor: '#38bdf866' } },
      { type: 'line', markLine: { silent: true, symbol: 'none', lineStyle: { color: '#10b981', type: 'dashed', width: 1.5 }, label: { color: '#10b981', fontSize: 10, formatter: '完全对称 y=x', position: 'end' }, data: [[{ coord: [0, 0] }, { coord: [maxV, maxV] }]] }, data: [], lineStyle: { opacity: 0 }, itemStyle: { opacity: 0 } }
    ]
  }
}

function renderCharts() {
  if (dashRef.value) {
    const c = echarts.init(dashRef.value)
    c.setOption(mockDownloads(), true)
    charts.push(c)
  }
  if (paraRef.value) {
    const c = echarts.init(paraRef.value)
    c.setOption(props.parallelCoords || mockParallelCoords(), true)
    charts.push(c)
  }
  if (symRef.value) {
    const c = echarts.init(symRef.value)
    c.setOption(props.symmetry || mockSymmetry(), true)
    charts.push(c)
  }
}

onMounted(() => { renderCharts() })
watch(() => [props.symmetry, props.parallelCoords], () => { renderCharts() })

onBeforeUnmount(() => { charts.forEach(c => c.dispose()) })
</script>
