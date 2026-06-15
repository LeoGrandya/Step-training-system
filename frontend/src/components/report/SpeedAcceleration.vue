<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-lg glow-border-sky">
    <h3 class="text-slate-800 text-base font-semibold mb-3 flex items-center gap-2">
      <span class="w-1.5 h-1.5 rounded-full bg-orange-500 animate-pulse"></span>
      三、速度与加速度分析
      <span class="text-xs bg-slate-100 text-slate-400 px-2 py-0.5 rounded-full ml-auto">运动学</span>
    </h3>
    <p class="text-sm text-slate-400 leading-relaxed mb-3 border-l-2 border-orange-500/30 pl-2.5">朱雪毅合速度峰值2.05m/s（globalStats.comSpeedPeak），合加速度在移动启动瞬间出现明显尖峰（如第4次移动段）。Vx/Vy速度曲线显示左右方向切换频率较高，变向衔接窗口加速度波动明显。各段极值对比表明段4和段7移动速度表现最优（comPeak均约2.0m/s），右脚踝峰值可达15.02-23.62m/s。建议关注制动→再启动转换效率的优化。</p>
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-3">
      <!-- 合速度/加速度 -->
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">重心合速度与合加速度曲线</p>
        <div ref="combRef" class="w-full h-52"></div>
      </div>
      <!-- 分轴速度 -->
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">X与Y方向速度曲线</p>
        <div ref="axisRef" class="w-full h-52"></div>
      </div>
      <!-- 速度极值柱状图 -->
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">各移动段速度极值对比</p>
        <div ref="barRef" class="w-full h-52"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { tooltipTheme } from '../../utils/chartTheme.js'
import { speedFrames as staticSpeedFrames, segmentSpeedPeaks as staticSegmentSpeedPeaks } from '../../data/bingbuData.js'

const props = defineProps({
  speedFrames: { type: Array, default: null },
  segmentSpeedPeaks: { type: Array, default: null },
})

const speedFrames = computed(() => props.speedFrames || staticSpeedFrames)
const segmentSpeedPeaks = computed(() => props.segmentSpeedPeaks || staticSegmentSpeedPeaks)

const combRef = ref(null)
const axisRef = ref(null)
const barRef = ref(null)
const charts = []

function dg() { return { containLabel: true, top: 22, bottom: 32, left: 78, right: 65 } }
function da() { return { axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#475569', fontSize: 11 }, splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } } } }

onMounted(() => {
  // 合速度/加速度 (双Y轴)
  if (combRef.value) {
    const c = echarts.init(combRef.value)
    const T = speedFrames.value.map(f => f.t)
    const v = speedFrames.value.map(f => +f.cs.toFixed(3))
    const a = speedFrames.value.map(f => +f.ca.toFixed(2))
    c.setOption({ tooltip: tooltipTheme(),
      grid: dg(),
      xAxis: { type: 'category', data: T.map(x => x.toFixed(1)), axisLabel: { color: '#475569', fontSize: 10, interval: 9 }, ...da() },
      yAxis: [
        { type: 'value', name: '合速度(m/s)', nameTextStyle: { color: '#38bdf8', fontSize: 11 }, ...da() },
        { type: 'value', name: '合加速度(m/s²)', nameTextStyle: { color: '#f59e0b', fontSize: 11 }, ...da() }
      ],
      legend: { data: ['合速度', '合加速度'], textStyle: { color: '#94a3b8', fontSize: 11 }, right: 0, top: 0 },
      series: [
        { name: '合速度', type: 'line', data: v, smooth: true, symbol: 'none', lineStyle: { color: '#38bdf8', width: 2 } },
        { name: '合加速度', type: 'line', yAxisIndex: 1, data: a, smooth: true, symbol: 'none', lineStyle: { color: '#f59e0b', width: 1.5, type: 'dashed' } }
      ]
    })
    charts.push(c)
  }

  // 分轴速度
  if (axisRef.value) {
    const c = echarts.init(axisRef.value)
    const T = speedFrames.value.map(f => f.t)
    const vx = speedFrames.value.map(f => +f.vx.toFixed(3))
    const vy = speedFrames.value.map(f => +f.vy.toFixed(3))
    c.setOption({ tooltip: tooltipTheme(),
      grid: dg(),
      xAxis: { type: 'category', data: T.map(x => x.toFixed(1)), axisLabel: { color: '#475569', fontSize: 10, interval: 9 }, ...da() },
      yAxis: { type: 'value', name: '速度(m/s)', nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() },
      legend: { data: ['Vx左右', 'Vy前后'], textStyle: { color: '#94a3b8', fontSize: 11 }, right: 0, top: 0 },
      series: [
        { name: 'Vx左右', type: 'line', data: vx, smooth: true, symbol: 'none', lineStyle: { color: '#3b82f6', width: 1.5 } },
        { name: 'Vy前后', type: 'line', data: vy, smooth: true, symbol: 'none', lineStyle: { color: '#ef4444', width: 1.5 } }
      ]
    })
    charts.push(c)
  }

  // 速度极值柱状图
  if (barRef.value) {
    const c = echarts.init(barRef.value)
    const moveRestore = segmentSpeedPeaks.value.filter(s => s.phase === 'move' || s.phase === 'restore')
    const segs = moveRestore.map(s => s.label.replace(/第\d+次/, ''))
    const bary = moveRestore.map(s => +s.comPeak.toFixed(1))
    const lany = moveRestore.map(s => +s.laPeak.toFixed(1))
    const rany = moveRestore.map(s => +s.raPeak.toFixed(1))
    c.setOption({ tooltip: tooltipTheme(),
      grid: { top: 22, bottom: 32, left: 80, right: 10 },
      xAxis: { type: 'category', data: segs, axisLabel: { color: '#94a3b8', fontSize: 11 }, ...da() },
      yAxis: { type: 'value', name: '最大合速度(m/s)', nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() },
      legend: { data: ['重心', '左脚踝', '右脚踝'], textStyle: { color: '#94a3b8', fontSize: 10 }, right: 0, top: 0 },
      series: [
        { name: '重心', type: 'bar', data: bary, itemStyle: { color: '#38bdf8', borderRadius: [3, 3, 0, 0] } },
        { name: '左脚踝', type: 'bar', data: lany, itemStyle: { color: '#10b981', borderRadius: [3, 3, 0, 0] } },
        { name: '右脚踝', type: 'bar', data: rany, itemStyle: { color: '#f59e0b', borderRadius: [3, 3, 0, 0] } }
      ]
    })
    charts.push(c)
  }
})

onBeforeUnmount(() => { charts.forEach(c => c.dispose()) })
</script>
