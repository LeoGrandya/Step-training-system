<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-lg glow-border-sky">
    <h3 class="text-slate-800 text-base font-semibold mb-3 flex items-center gap-2">
      <span class="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-pulse"></span>
      二、位移与轨迹分析
      <span class="text-xs bg-slate-100 text-slate-400 px-2 py-0.5 rounded-full ml-auto">运动轨迹</span>
    </h3>
    <p class="text-sm text-slate-400 leading-relaxed mb-3 border-l-2 border-cyan-500/30 pl-2.5">朱雪毅并步2-1重心轨迹热力图显示其左右移动范围0.42-1.58m，前后范围0.89-1.90m。X/Y分解曲线存在明显方向切换点，双脚踝累计移动距离（左脚踝23.85m、右脚踝30.86m）均远高于重心（15.70m）。建议加强前后方向移动训练，实现更均衡的场地覆盖。</p>
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
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { tooltipTheme } from '../../utils/chartTheme.js'
import { displacementFrames as staticDisplacementFrames } from '../../data/bingbuData.js'

const props = defineProps({
  displacementFrames: { type: Array, default: null },
})

const displacementFrames = computed(() => props.displacementFrames || staticDisplacementFrames)

const trajRef = ref(null)
const xyRef = ref(null)
const cumRef = ref(null)
const charts = []

function dg() { return { containLabel: true, top: 18, bottom: 32, left: 78, right: 50 } }
function da() { return { axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#475569', fontSize: 11 }, splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } } } }

onMounted(() => {
  // 重心轨迹热力图 (九宫格背景)
  if (trajRef.value) {
    const c = echarts.init(trajRef.value)
    const pts = displacementFrames.value.map(f => [+f.com_x.toFixed(3), +f.com_y.toFixed(3), +f.cp.toFixed(2)])
    c.setOption({ tooltip: tooltipTheme(),
      grid: dg(),
      xAxis: { type: 'value', name: 'X 左右(m)', min: 0.3, max: 1.7, nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() },
      yAxis: { type: 'value', name: 'Y 前后(m)', min: 0.8, max: 1.9, nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() },
      visualMap: { min: 0, max: 16, inRange: { color: ['#3b82f6', '#22c55e', '#eab308', '#ef4444'] }, text: ['高速', '低速'], textStyle: { color: '#94a3b8', fontSize: 10 }, right: 40, top: 5, calculable: false, dimension: 2 },
      series: [{
        type: 'scatter', data: pts, symbolSize: 3,
        itemStyle: { shadowBlur: 2, shadowColor: '#38bdf866' }
      }, {
        type: 'line', markLine: { silent: true, symbol: 'none', lineStyle: { color: '#334155', type: 'dashed' }, data: [{ xAxis: 0.333 }, { xAxis: 0.667 }, { yAxis: 0.333 }, { yAxis: 0.667 }] }
      }]
    })
    charts.push(c)
  }

  // X/Y位移分解
  if (xyRef.value) {
    const c = echarts.init(xyRef.value)
    const T = displacementFrames.value.map(f => f.t)
    const xd = displacementFrames.value.map(f => +f.cx.toFixed(3))
    const yd = displacementFrames.value.map(f => +f.cy.toFixed(3))
    c.setOption({ tooltip: tooltipTheme(),
      grid: dg(),
      xAxis: { type: 'category', data: T.map(v => v.toFixed(1)), axisLabel: { color: '#475569', fontSize: 10, interval: 9 }, ...da() },
      yAxis: { type: 'value', name: '位移(m)', nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() },
      legend: { data: ['X位移', 'Y位移'], textStyle: { color: '#94a3b8', fontSize: 11 }, right: 0, top: 0 },
      series: [
        { name: 'X位移', type: 'line', data: xd, smooth: true, symbol: 'none', lineStyle: { color: '#3b82f6', width: 1.5 } },
        { name: 'Y位移', type: 'line', data: yd, smooth: true, symbol: 'none', lineStyle: { color: '#ef4444', width: 1.5 } }
      ]
    })
    charts.push(c)
  }

  // 累计距离
  if (cumRef.value) {
    const c = echarts.init(cumRef.value)
    const T2 = displacementFrames.value.map(f => f.t)
    const dm = displacementFrames.value.map(f => +f.cp.toFixed(2))
    const dl = displacementFrames.value.map(f => +f.lp.toFixed(2))
    const dr = displacementFrames.value.map(f => +f.rp.toFixed(2))
    c.setOption({ tooltip: tooltipTheme(),
      grid: dg(),
      xAxis: { type: 'category', data: T2.map(v => v.toFixed(1)), axisLabel: { color: '#475569', fontSize: 10, interval: 9 }, ...da() },
      yAxis: { type: 'value', name: '距离(m)', nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() },
      legend: { data: ['重心', '左脚踝', '右脚踝'], textStyle: { color: '#94a3b8', fontSize: 11 }, right: 0, top: 0 },
      series: [
        { name: '重心', type: 'line', data: dm, smooth: true, symbol: 'none', lineStyle: { color: '#38bdf8', width: 1.5 } },
        { name: '左脚踝', type: 'line', data: dl, smooth: true, symbol: 'none', lineStyle: { color: '#10b981', width: 1.5 } },
        { name: '右脚踝', type: 'line', data: dr, smooth: true, symbol: 'none', lineStyle: { color: '#f59e0b', width: 1.5 } }
      ]
    })
    charts.push(c)
  }
})

onBeforeUnmount(() => { charts.forEach(c => c.dispose()) })
</script>
