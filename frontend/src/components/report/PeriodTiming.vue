<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-lg glow-border-sky">
    <h3 class="text-slate-800 text-base font-semibold mb-3 flex items-center gap-2">
      <span class="w-1.5 h-1.5 rounded-full bg-violet-500 animate-pulse"></span>
      一、周期划分与时序分析
      <span class="text-xs bg-slate-100 text-slate-400 px-2 py-0.5 rounded-full ml-auto">步伐周期</span>
    </h3>
    <p class="text-sm text-slate-400 leading-relaxed mb-3 border-l-2 border-violet-500/30 pl-2.5">朱雪毅并步共14个移动段+14个还原段，6个完整周期。周期1移动仅1.03s但还原0.65s效率高；周期5移动最长1.47s。平均变向衔接时间91ms，整体节奏紧凑。建议关注周期5的大跨步动作质量。</p>
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-3">
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2"><p class="text-sm text-slate-400 mb-1 font-medium">步伐周期甘特图（1号步伐）</p><div ref="ganttRef" class="w-full h-48"></div></div>
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2"><p class="text-sm text-slate-400 mb-1 font-medium">重心相平面图（移动/制动动态）</p><div ref="phaseRef" class="w-full h-64"></div></div>
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2"><p class="text-sm text-slate-400 mb-1 font-medium">重心合速度曲线及阶段划分</p><div ref="speedRef" class="w-full h-64"></div></div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { tooltipTheme } from '../../utils/chartTheme.js'
import { phaseSegments as staticPhaseSegments, speedFrames as staticSpeedFrames, displacementFrames as staticDisplacementFrames } from '../../data/bingbuData.js'

const props = defineProps({
  phaseSegments: { type: Array, default: null },
  speedFrames: { type: Array, default: null },
  displacementFrames: { type: Array, default: null },
})

const phaseSegments = computed(() => props.phaseSegments || staticPhaseSegments)
const speedFrames = computed(() => props.speedFrames || staticSpeedFrames)
const displacementFrames = computed(() => props.displacementFrames || staticDisplacementFrames)

const ganttRef = ref(null)
const phaseRef = ref(null)
const speedRef = ref(null)
const charts = []

function dg() { return { top: 20, bottom: 55, left: 105, right: 15 } }
function da() { return { axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#475569', fontSize: 11 }, splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } } } }

onMounted(() => {
  // 甘特图 - 前5个周期的移动/还原段（取前10段确保清晰）
  if (ganttRef.value) {
    const c = echarts.init(ganttRef.value)
    const displaySegs = phaseSegments.value.filter(s => s.phase === 'move' || s.phase === 'restore').slice(0, 10)
    const yLabels = displaySegs.map(s => `C${s.cycle} ${s.phase === 'move' ? '移动' : '还原'}`)
    const colors = ['#6366f1', '#38bdf8', '#f59e0b', '#10b981']
    const ganttData = displaySegs.map((s, i) => [i, s.startT, s.endT, s.dur])
    c.setOption({ tooltip: tooltipTheme('item'), grid: { containLabel: true, top: 10, bottom: 18, left: 72, right: 10 }, xAxis: { type: 'value', name: '时间(s)', nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() }, yAxis: { type: 'category', data: yLabels, inverse: true, axisLabel: { color: '#94a3b8', fontSize: 11 }, axisLine: { lineStyle: { color: '#334155' } } }, series: [{ type: 'bar', data: ganttData, itemStyle: { borderRadius: [0, 4, 4, 0] }, label: { show: true, position: 'insideLeft', formatter: (p) => p.value[2].toFixed(2) + 's', color: '#fff', fontSize: 10 }, encode: { x: [1, 2], y: 0 }, barWidth: 14, color: (p) => colors[p.dataIndex % 4] }] })
    charts.push(c)
  }

  // 相平面图 - 使用真实位移和速度数据 (采样前4秒)
  if (phaseRef.value) {
    const c = echarts.init(phaseRef.value)
    const phaseData = []
    const dFrames = displacementFrames.value.filter(f => f.t <= 5.0)
    const sFrames = speedFrames.value.filter(f => f.t <= 5.0)
    const len = Math.min(dFrames.length, sFrames.length)
    for (let i = 0; i < len; i++) {
      phaseData.push([dFrames[i].cx, sFrames[i].cs])
    }
    c.setOption({ tooltip: tooltipTheme(), grid: dg(), xAxis: { type: 'value', name: '位移X(m)', nameGap: 10, nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() }, yAxis: { type: 'value', name: '合速度(m/s)', nameGap: 10, nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() }, series: [{ type: 'line', data: phaseData, smooth: true, symbol: 'none', lineStyle: { color: '#38bdf8', width: 1.5 }, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#6366f1' }, { offset: 1, color: '#38bdf8' }]) } }, { type: 'line', markLine: { silent: true, symbol: 'none', lineStyle: { color: '#334155', type: 'dashed' }, data: [{ xAxis: 0 }, { yAxis: 0 }] } }] })
    charts.push(c)
  }

  // 合速度曲线 - 使用逐帧真实数据
  if (speedRef.value) {
    const c = echarts.init(speedRef.value)
    const times = speedFrames.value.map(f => f.t)
    const speeds = speedFrames.value.map(f => f.cs)
    // 构建 markArea: 从phaseSegments中筛选移动段和还原段
    const markAreas = []
    const moveSegs = phaseSegments.value.filter(s => s.phase === 'move' && s.startT <= times[times.length - 1])
    const restoreSegs = phaseSegments.value.filter(s => s.phase === 'restore' && s.startT <= times[times.length - 1])
    const phaseColors = { move: 'rgba(56,189,248,0.1)', restore: 'rgba(16,185,129,0.08)', pre_move_stop: 'rgba(99,102,241,0.06)', pre_restore_stop: 'rgba(245,158,11,0.06)' }
    ;[...moveSegs, ...restoreSegs].forEach(s => {
      const tIdx = times.findIndex(t => t >= s.startT)
      const eIdx = times.findIndex(t => t >= s.endT)
      if (tIdx >= 0 && eIdx >= 0 && tIdx < times.length) {
        markAreas.push([{ xAxis: times[tIdx], itemStyle: { color: phaseColors[s.phase] || 'rgba(100,100,100,0.05)' } }, { xAxis: times[Math.min(eIdx, times.length - 1)] }])
      }
    })
    c.setOption({ tooltip: tooltipTheme(), grid: dg(), xAxis: { type: 'category', data: times, axisLabel: { color: '#475569', fontSize: 10, interval: 9 }, ...da() }, yAxis: { type: 'value', name: '合速度(m/s)', nameGap: 10, nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() }, series: [{ type: 'line', data: speeds, smooth: true, symbol: 'none', lineStyle: { color: '#38bdf8', width: 1.5 }, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(56,189,248,0.25)' }, { offset: 1, color: 'rgba(56,189,248,0.02)' }]) }, markArea: { silent: true, data: markAreas.slice(0, 12) } }] })
    charts.push(c)
  }
})

onBeforeUnmount(() => { charts.forEach(c => c.dispose()) })
</script>
