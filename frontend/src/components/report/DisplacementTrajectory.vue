<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-lg glow-border-sky">
    <h3 class="text-slate-800 text-base font-semibold mb-3 flex items-center gap-2">
      <span class="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-pulse"></span>
      二、位移与轨迹分析
      <span class="text-xs bg-slate-100 text-slate-400 px-2 py-0.5 rounded-full ml-auto">运动轨迹</span>
    </h3>
    <p class="text-sm text-slate-400 leading-relaxed mb-3 border-l-2 border-cyan-500/30 pl-2.5">重心轨迹热力图显示运动员主要沿左右方向移动，前后位移幅度相对较小。X/Y分解曲线存在明显方向切换点，双脚踝累计移动距离均高于重心。建议加强前后方向移动训练，实现更均衡的场地覆盖。</p>
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-3">
      <!-- 重心运动轨迹热力图 -->
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">重心运动轨迹（速度热力图）</p>
        <div ref="trajRef" class="w-full h-52"></div>
      </div>
      <!-- X/Y位移分解 -->
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">X与Y方向位移分解</p>
        <div ref="xyRef" class="w-full h-52"></div>
      </div>
      <!-- 累计距离曲线 -->
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">各部位累计移动距离</p>
        <div ref="cumRef" class="w-full h-52"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'
import { tooltipTheme } from '../../utils/chartTheme.js'

const props = defineProps({
  displacement: Object,
  displacementXY: Object,
  cumulativeDist: Object
})

const trajRef = ref(null)
const xyRef = ref(null)
const cumRef = ref(null)
const charts = []

function dg() { return { top: 18, bottom: 22, left: 42, right: 10 } }
function da() { return { axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#475569', fontSize: 11 }, splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } } } }

function mockDisplacement() {
  const pts = []
  let px = 0.5, py = 0.5, t = 0
  for (let i = 0; i < 200; i++) {
    t += 0.02; px += Math.sin(t * 2.3) * 0.04 + (Math.random() - 0.5) * 0.015
    py += Math.cos(t * 1.7) * 0.03 + (Math.random() - 0.5) * 0.012
    const v = 1.5 + Math.abs(Math.sin(t * 2.3)) * 2 + Math.random() * 0.5
    pts.push([+px.toFixed(3), +py.toFixed(3), +v.toFixed(2)])
  }
  return {
    tooltip: tooltipTheme(),
    grid: dg(),
    xAxis: { type: 'value', name: 'X 左右(m)', nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() },
    yAxis: { type: 'value', name: 'Y 前后(m)', nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() },
    visualMap: { min: 0.5, max: 4, inRange: { color: ['#3b82f6', '#22c55e', '#eab308', '#ef4444'] }, text: ['高速', '低速'], textStyle: { color: '#94a3b8', fontSize: 10 }, right: 2, top: 5, calculable: false, dimension: 2 },
    series: [
      { type: 'scatter', data: pts, symbolSize: 3, itemStyle: { shadowBlur: 2, shadowColor: '#38bdf866' } },
      { type: 'line', markLine: { silent: true, symbol: 'none', lineStyle: { color: '#334155', type: 'dashed' }, data: [{ xAxis: 0.333 }, { xAxis: 0.667 }, { yAxis: 0.333 }, { yAxis: 0.667 }] } }
    ]
  }
}

function mockDisplacementXY() {
  const T = Array.from({ length: 100 }, (_, i) => +(i * 0.05).toFixed(2))
  const xd = [], yd = []
  let sx = 0, sy = 0
  T.forEach(ti => { sx += (Math.sin(ti * 2) * 0.06 + (Math.random() - 0.5) * 0.02); xd.push(+sx.toFixed(3)); sy += (Math.cos(ti * 1.5) * 0.05 + (Math.random() - 0.5) * 0.015); yd.push(+sy.toFixed(3)) })
  return {
    tooltip: tooltipTheme(),
    grid: dg(),
    xAxis: { type: 'category', data: T.map(v => v.toFixed(1)), axisLabel: { color: '#475569', fontSize: 10, interval: 19 }, ...da() },
    yAxis: { type: 'value', name: '位移(m)', nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() },
    legend: { data: ['X位移', 'Y位移'], textStyle: { color: '#94a3b8', fontSize: 11 }, right: 0, top: 0 },
    series: [
      { name: 'X位移', type: 'line', data: xd, smooth: true, symbol: 'none', lineStyle: { color: '#3b82f6', width: 1.5 } },
      { name: 'Y位移', type: 'line', data: yd, smooth: true, symbol: 'none', lineStyle: { color: '#ef4444', width: 1.5 } }
    ]
  }
}

function mockCumulativeDist() {
  const T2 = Array.from({ length: 100 }, (_, i) => +(i * 0.05).toFixed(2))
  let cm = 0, cl = 0, cr = 0
  const dm = [], dl = [], dr = []
  T2.forEach(() => { cm += 0.035 + Math.random() * 0.02; cl += 0.04 + Math.random() * 0.025; cr += 0.038 + Math.random() * 0.022; dm.push(+cm.toFixed(2)); dl.push(+cl.toFixed(2)); dr.push(+cr.toFixed(2)) })
  return {
    tooltip: tooltipTheme(),
    grid: dg(),
    xAxis: { type: 'category', data: T2.map(v => v.toFixed(1)), axisLabel: { color: '#475569', fontSize: 10, interval: 19 }, ...da() },
    yAxis: { type: 'value', name: '距离(m)', nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() },
    legend: { data: ['重心', '左脚踝', '右脚踝'], textStyle: { color: '#94a3b8', fontSize: 11 }, right: 0, top: 0 },
    series: [
      { name: '重心', type: 'line', data: dm, smooth: true, symbol: 'none', lineStyle: { color: '#38bdf8', width: 1.5 } },
      { name: '左脚踝', type: 'line', data: dl, smooth: true, symbol: 'none', lineStyle: { color: '#10b981', width: 1.5 } },
      { name: '右脚踝', type: 'line', data: dr, smooth: true, symbol: 'none', lineStyle: { color: '#f59e0b', width: 1.5 } }
    ]
  }
}

function renderCharts() {
  charts.forEach(c => c.dispose())
  charts.length = 0
  if (trajRef.value) {
    const c = echarts.init(trajRef.value)
    c.setOption(props.displacement || mockDisplacement(), true)
    charts.push(c)
  }
  if (xyRef.value) {
    const c = echarts.init(xyRef.value)
    c.setOption(props.displacementXY || mockDisplacementXY(), true)
    charts.push(c)
  }
  if (cumRef.value) {
    const c = echarts.init(cumRef.value)
    c.setOption(props.cumulativeDist || mockCumulativeDist(), true)
    charts.push(c)
  }
}

onMounted(() => { renderCharts() })
watch(() => [props.displacement, props.displacementXY, props.cumulativeDist], () => { renderCharts() })

onBeforeUnmount(() => { charts.forEach(c => c.dispose()) })
</script>
