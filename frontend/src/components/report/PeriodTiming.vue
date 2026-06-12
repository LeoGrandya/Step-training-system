<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-lg glow-border-sky">
    <h3 class="text-slate-800 text-base font-semibold mb-3 flex items-center gap-2">
      <span class="w-1.5 h-1.5 rounded-full bg-violet-500 animate-pulse"></span>
      一、周期划分与时序分析
      <span class="text-xs bg-slate-100 text-slate-400 px-2 py-0.5 rounded-full ml-auto">步伐周期</span>
    </h3>
    <p class="text-sm text-slate-400 leading-relaxed mb-3 border-l-2 border-violet-500/30 pl-2.5">甘特图显示单个步伐周期约4.6s，移动阶段占比最大（1.6s）。相平面图揭示移动与制动阶段呈闭环特征，合速度在阶段切换处出现明显波谷。建议优化移动→还原过渡衔接，进一步缩短周期总时长。</p>
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-3">
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2"><p class="text-sm text-slate-400 mb-1 font-medium">步伐周期甘特图（1号步伐）</p><div ref="ganttRef" class="w-full h-48"></div></div>
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2"><p class="text-sm text-slate-400 mb-1 font-medium">重心相平面图（移动/制动动态）</p><div ref="phaseRef" class="w-full h-48"></div></div>
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2"><p class="text-sm text-slate-400 mb-1 font-medium">重心合速度曲线及阶段划分</p><div ref="speedRef" class="w-full h-48"></div></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'
import { tooltipTheme } from '../../utils/chartTheme.js'

const props = defineProps({
  gantt: Object,
  phasePlane: Object,
  speedOption: Object
})

const ganttRef = ref(null)
const phaseRef = ref(null)
const speedRef = ref(null)
const charts = []

function dg() { return { top: 18, bottom: 22, left: 42, right: 10 } }
function da() { return { axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#475569', fontSize: 11 }, splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } } } }

function mockGantt() {
  const phases = ['移动前停止', '移动', '还原前停止', '还原']
  const colors = ['#6366f1', '#38bdf8', '#f59e0b', '#10b981']
  const data = [[0, 1.2], [1.2, 2.8], [2.8, 3.5], [3.5, 4.6]]
  return {
    tooltip: tooltipTheme('item'),
    grid: { top: 10, bottom: 18, left: 72, right: 10 },
    xAxis: { type: 'value', name: '时间(s)', nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() },
    yAxis: { type: 'category', data: phases, inverse: true, axisLabel: { color: '#94a3b8', fontSize: 11 }, axisLine: { lineStyle: { color: '#334155' } } },
    series: [{
      type: 'bar',
      data: phases.map((_, i) => [i, data[i][0], data[i][1], data[i][1] - data[i][0]]),
      itemStyle: { borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: 'insideLeft', formatter: (p) => p.value[2].toFixed(1) + 's', color: '#fff', fontSize: 11 },
      encode: { x: [1, 2], y: 0 },
      barWidth: 16,
      color: (p) => colors[p.dataIndex]
    }]
  }
}

function mockPhasePlane() {
  const d = []
  let x = 0, y = 0
  for (let i = 0; i < 120; i++) {
    x += (Math.random() - 0.48) * 0.03
    y = Math.sin(i * 0.15) * 0.8 + Math.random() * 0.15
    d.push([+x.toFixed(3), +y.toFixed(3)])
  }
  return {
    tooltip: tooltipTheme(),
    grid: dg(),
    xAxis: { type: 'value', name: '位移(m)', nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() },
    yAxis: { type: 'value', name: '速度(m/s)', nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() },
    series: [
      {
        type: 'line', data: d, smooth: true, symbol: 'none',
        lineStyle: { color: '#38bdf8', width: 1.5 },
        itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#6366f1' }, { offset: 1, color: '#38bdf8' }]) }
      },
      { type: 'line', markLine: { silent: true, symbol: 'none', lineStyle: { color: '#334155', type: 'dashed' }, data: [{ xAxis: 0 }, { yAxis: 0 }] } }
    ]
  }
}

function mockSpeed() {
  const T = Array.from({ length: 100 }, (_, i) => +(i * 0.05).toFixed(2))
  const v = T.map(x => Math.abs(Math.sin(x * 1.5) * 2.5 + Math.cos(x * 0.8) * 0.8 + Math.random() * 0.3))
  return {
    tooltip: tooltipTheme(),
    grid: dg(),
    xAxis: { type: 'category', data: T.map(x => x.toFixed(1)), axisLabel: { color: '#475569', fontSize: 10, interval: 19 }, ...da() },
    yAxis: { type: 'value', name: '合速度(m/s)', nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() },
    series: [{
      type: 'line', data: v, smooth: true, symbol: 'none',
      lineStyle: { color: '#38bdf8', width: 1.5 },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(56,189,248,0.25)' }, { offset: 1, color: 'rgba(56,189,248,0.02)' }]) },
      markArea: {
        silent: true,
        data: [
          [{ xAxis: '0.0', itemStyle: { color: 'rgba(99,102,241,0.08)' } }, { xAxis: '1.2' }],
          [{ xAxis: '1.2', itemStyle: { color: 'rgba(56,189,248,0.08)' } }, { xAxis: '2.8' }],
          [{ xAxis: '2.8', itemStyle: { color: 'rgba(245,158,11,0.08)' } }, { xAxis: '3.5' }],
          [{ xAxis: '3.5', itemStyle: { color: 'rgba(16,185,129,0.08)' } }, { xAxis: '5.0' }]
        ]
      }
    }]
  }
}

function renderCharts() {
  charts.forEach(c => c.dispose())
  charts.length = 0
  if (ganttRef.value) {
    const c = echarts.init(ganttRef.value)
    c.setOption(props.gantt || mockGantt(), true)
    charts.push(c)
  }
  if (phaseRef.value) {
    const c = echarts.init(phaseRef.value)
    c.setOption(props.phasePlane || mockPhasePlane(), true)
    charts.push(c)
  }
  if (speedRef.value) {
    const c = echarts.init(speedRef.value)
    c.setOption(props.speedOption || mockSpeed(), true)
    charts.push(c)
  }
}

onMounted(() => { renderCharts() })
watch(() => [props.gantt, props.phasePlane, props.speedOption], () => { renderCharts() })

onBeforeUnmount(() => { charts.forEach(c => c.dispose()) })
</script>
