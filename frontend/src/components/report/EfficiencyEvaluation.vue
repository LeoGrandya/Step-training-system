<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-lg glow-border-sky">
    <h3 class="text-slate-800 text-base font-semibold mb-3 flex items-center gap-2">
      <span class="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
      六、效率与评价分析
      <span class="text-xs bg-slate-100 text-slate-400 px-2 py-0.5 rounded-full ml-auto">运动表现</span>
    </h3>
    <p class="text-sm text-slate-400 leading-relaxed mb-3 border-l-2 border-amber-500/30 pl-2.5">KLI指数大部分时段低于0.6安全阈值，DSO在50%-80%区间波动。包络线面积峰值出现在大跨步动作时，步伐3的bq值与步幅耗能比均较优。DTW热力图验证了段间速度模式差异，膝关节承担主要做功（左42%/右44%），建议提升髋关节发力参与度以优化能耗分布。</p>
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-3">
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2 flex flex-col">
        <p class="text-sm text-slate-400 mb-1 font-medium">KLI与DSO趋势</p>
        <div ref="kliRef" class="w-full flex-1 min-h-[160px]"></div>
      </div>
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2 flex flex-col">
        <p class="text-sm text-slate-400 mb-1 font-medium">包络线面积与翼展比</p>
        <div ref="envRef" class="w-full flex-1 min-h-[160px]"></div>
      </div>
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2 flex flex-col">
        <p class="text-sm text-slate-400 mb-1 font-medium">步伐发力效率对比</p>
        <div ref="effRef" class="w-full flex-1 min-h-[160px]"></div>
      </div>
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2 flex flex-col">
        <p class="text-sm text-slate-400 mb-1 font-medium">速度曲线相似度热力图</p>
        <div ref="dtwRef" class="w-full flex-1 min-h-[160px]"></div>
      </div>
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2 flex flex-col">
        <p class="text-sm text-slate-400 mb-1 font-medium">下肢关节能耗占比</p>
        <div ref="pieRef" class="w-full flex-1 min-h-[160px]"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'
import { tooltipTheme } from '../../utils/chartTheme.js'
import ReportEmptyState from './ReportEmptyState.vue'

const isDev = import.meta.env.DEV

const props = defineProps({
  assessments: { type: Object, default: () => ({}) },
  efficiency: Object,
  dtwHeatmap: Object,
  efficiencyBars: Object,
  stepEfficiencyBars: Object,
  energyBars: Object
})

const kliRef = ref(null)
const envRef = ref(null)
const effRef = ref(null)
const dtwRef = ref(null)
const pieRef = ref(null)
const charts = []

const hasEfficiency = computed(() => !!props.efficiency)
const hasEfficiencyBars = computed(() => !!props.efficiencyBars)
const hasStepBars = computed(() => !!props.stepEfficiencyBars)
const hasDtw = computed(() => !!props.dtwHeatmap)
const hasEnergy = computed(() => !!props.energyBars)

const entries = computed(() => Object.entries(props.assessments))

function ds() { return { top: 16, bottom: 20, left: 42, right: 42 } }
function db() { return { axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#475569', fontSize: 10 }, splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } } } }

function mockEfficiency() {
  const T = Array.from({ length: 100 }, (_, i) => +(i * 0.05).toFixed(2))
  const kli = T.map(x => 0.3 + Math.sin(x * 1.4) * 0.2 + Math.random() * 0.05)
  const dso = T.map(x => 60 + Math.cos(x * 1.3) * 20 + Math.random() * 5)
  return {
    tooltip: tooltipTheme(),
    grid: ds(),
    xAxis: { type: 'category', data: T.map(v => v.toFixed(1)), axisLabel: { color: '#475569', fontSize: 10, interval: 24 }, ...db() },
    yAxis: [
      { type: 'value', name: 'KLI', nameTextStyle: { color: '#38bdf8', fontSize: 10 }, ...db() },
      { type: 'value', name: 'DSO(%)', nameTextStyle: { color: '#10b981', fontSize: 10 }, ...db() }
    ],
    legend: { data: ['KLI', 'DSO'], textStyle: { color: '#94a3b8', fontSize: 10 }, right: 0, top: 0 },
    series: [
      { name: 'KLI', type: 'line', data: kli, smooth: true, symbol: 'none', lineStyle: { color: '#38bdf8', width: 1.5 } },
      { name: 'DSO', type: 'line', yAxisIndex: 1, data: dso, smooth: true, symbol: 'none', lineStyle: { color: '#10b981', width: 1.5 } },
      { type: 'line', markLine: { silent: true, symbol: 'none', lineStyle: { color: '#ef4444', type: 'dashed', width: 1 }, label: { color: '#ef4444', fontSize: 10, formatter: '阈值0.6' }, data: [{ yAxis: 0.6 }] }, data: [], lineStyle: { opacity: 0 }, itemStyle: { opacity: 0 } }
    ]
  }
}

function mockEfficiencyBars() {
  const T = Array.from({ length: 80 }, (_, i) => +(i * 0.06).toFixed(2))
  const area = T.map(x => 0.8 + Math.sin(x * 1.2) * 0.4 + Math.random() * 0.15)
  const ratio = T.map(x => 1.5 + Math.cos(x * 1.1) * 0.6 + Math.random() * 0.1)
  return {
    tooltip: tooltipTheme(),
    grid: ds(),
    xAxis: { type: 'category', data: T.map(v => v.toFixed(1)), axisLabel: { color: '#475569', fontSize: 10, interval: 19 }, ...db() },
    yAxis: [
      { type: 'value', name: '面积(m²)', nameTextStyle: { color: '#38bdf8', fontSize: 10 }, ...db() },
      { type: 'value', name: '翼展比', nameTextStyle: { color: '#f59e0b', fontSize: 10 }, ...db() }
    ],
    legend: { data: ['包络线面积', '翼展比'], textStyle: { color: '#94a3b8', fontSize: 10 }, right: 0, top: 0 },
    series: [
      { name: '包络线面积', type: 'line', data: area, smooth: true, symbol: 'none', lineStyle: { color: '#38bdf8', width: 1.5 }, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(56,189,248,0.2)' }, { offset: 1, color: 'rgba(56,189,248,0.02)' }]) } },
      { name: '翼展比', type: 'line', yAxisIndex: 1, data: ratio, smooth: true, symbol: 'none', lineStyle: { color: '#f59e0b', width: 1.5 } }
    ]
  }
}

function mockStepEfficiencyBars() {
  const steps = ['步伐1', '步伐2', '步伐3', '步伐4', '步伐5', '步伐6']
  const bq = steps.map(() => +(55 + Math.random() * 30).toFixed(0))
  const ratio2 = steps.map(() => +(0.3 + Math.random() * 0.5).toFixed(2))
  return {
    tooltip: tooltipTheme(),
    grid: ds(),
    xAxis: { type: 'category', data: steps, axisLabel: { color: '#94a3b8', fontSize: 10 }, ...db() },
    yAxis: [
      { type: 'value', name: 'bq(%)', nameTextStyle: { color: '#38bdf8', fontSize: 10 }, ...db() },
      { type: 'value', name: 'm/J', nameTextStyle: { color: '#10b981', fontSize: 10 }, ...db() }
    ],
    legend: { data: ['bq', '步幅/耗能比'], textStyle: { color: '#94a3b8', fontSize: 10 }, right: 0, top: 0 },
    series: [
      { name: 'bq', type: 'bar', data: bq, itemStyle: { color: '#38bdf8', borderRadius: [3, 3, 0, 0] } },
      { name: '步幅/耗能比', type: 'line', yAxisIndex: 1, data: ratio2, symbol: 'circle', symbolSize: 6, lineStyle: { color: '#10b981', width: 1.5 }, itemStyle: { color: '#10b981' } }
    ]
  }
}

function mockDtwHeatmap() {
  const n = 8
  const hm = []
  for (let i = 0; i < n; i++) { const row = []; for (let j = 0; j < n; j++) { row.push(i === j ? 0 : +(Math.abs(i - j) * 0.08 + Math.random() * 0.15).toFixed(2)) } hm.push(row) }
  return {
    tooltip: tooltipTheme('item'),
    grid: { top: 16, bottom: 20, left: 42, right: 20 },
    xAxis: { type: 'category', data: Array.from({ length: n }, (_, i) => '段' + (i + 1)), axisLabel: { color: '#94a3b8', fontSize: 10 }, ...db() },
    yAxis: { type: 'category', data: Array.from({ length: n }, (_, i) => '段' + (i + 1)), axisLabel: { color: '#94a3b8', fontSize: 10 }, ...db() },
    visualMap: { min: 0, max: 1, inRange: { color: ['#1e293b', '#3b82f6', '#22c55e', '#eab308', '#ef4444'] }, text: ['大', '小'], textStyle: { color: '#94a3b8', fontSize: 10 }, right: 2, top: 2, calculable: false, orient: 'vertical', itemWidth: 8, itemHeight: 60 },
    series: [{ type: 'heatmap', data: hm.flatMap((row, i) => row.map((v, j) => [j, i, v])), label: { show: false, color: '#e2e8f0', fontSize: 10 } }]
  }
}

function mockEnergyBars() {
  return {
    tooltip: tooltipTheme('item'),
    legend: { data: ['髋关节', '膝关节', '踝关节'], textStyle: { color: '#94a3b8', fontSize: 10 }, bottom: 0 },
    series: [
      { name: '左侧', type: 'pie', radius: ['40%', '55%'], center: ['28%', '45%'], label: { color: '#94a3b8', fontSize: 10, formatter: '{b}\n{d}%' }, silent: true, data: [{ value: 38, name: '髋关节', itemStyle: { color: '#6366f1' } }, { value: 42, name: '膝关节', itemStyle: { color: '#38bdf8' } }, { value: 20, name: '踝关节', itemStyle: { color: '#10b981' } }] },
      { name: '右侧', type: 'pie', radius: ['40%', '55%'], center: ['72%', '45%'], label: { color: '#94a3b8', fontSize: 10, formatter: '{b}\n{d}%' }, silent: true, data: [{ value: 35, name: '髋关节', itemStyle: { color: '#6366f1' } }, { value: 44, name: '膝关节', itemStyle: { color: '#38bdf8' } }, { value: 21, name: '踝关节', itemStyle: { color: '#10b981' } }] }
    ]
  }
}

function renderCharts() {
  if (kliRef.value) {
    const c = echarts.init(kliRef.value)
    if (props.efficiency) c.setOption(props.efficiency, true)
    else if (isDev) c.setOption(mockEfficiency(), true)
    charts.push(c)
  }
  if (envRef.value) {
    const c = echarts.init(envRef.value)
    if (props.efficiencyBars) c.setOption(props.efficiencyBars, true)
    else if (isDev) c.setOption(mockEfficiencyBars(), true)
    charts.push(c)
  }
  if (effRef.value) {
    const c = echarts.init(effRef.value)
    if (props.stepEfficiencyBars) c.setOption(props.stepEfficiencyBars, true)
    else if (isDev) c.setOption(mockStepEfficiencyBars(), true)
    charts.push(c)
  }
  if (dtwRef.value) {
    const c = echarts.init(dtwRef.value)
    if (props.dtwHeatmap) c.setOption(props.dtwHeatmap, true)
    else if (isDev) c.setOption(mockDtwHeatmap(), true)
    charts.push(c)
  }
  if (pieRef.value) {
    const c = echarts.init(pieRef.value)
    if (props.energyBars) c.setOption(props.energyBars, true)
    else if (isDev) c.setOption(mockEnergyBars(), true)
    charts.push(c)
  }
}

onMounted(() => { renderCharts() })
watch(() => [props.efficiency, props.dtwHeatmap, props.efficiencyBars, props.stepEfficiencyBars, props.energyBars], () => { renderCharts() })

onBeforeUnmount(() => { charts.forEach(c => c.dispose()) })
</script>
