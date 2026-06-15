<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-lg glow-border-sky">
    <h3 class="text-slate-800 text-base font-semibold mb-3 flex items-center gap-2">
      <span class="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse"></span>
      四、腾空参数分析
      <span class="text-xs bg-slate-100 text-slate-400 px-2 py-0.5 rounded-full ml-auto">腾空检测</span>
    </h3>
    <p class="text-sm text-slate-400 leading-relaxed mb-3 border-l-2 border-rose-500/30 pl-2.5">朱雪毅双脚最大腾空时间0.34s（高度0.075m），左脚最大腾空0.54s（高度0.235m），右脚最大腾空0.53s（高度0.164m）。足底高度曲线表明腾空主要发生在大范围跨步动作中（如第8次移动左脚悬空0.214m），右足尖最大高度达0.154m。建议通过针对性爆发力训练改善左脚起跳协调性。</p>
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <!-- 悬空时间与高度散点图 -->
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">悬空时间 vs 悬空高度</p>
        <div ref="scatterRef" class="w-full h-56"></div>
      </div>
      <!-- 足底高度曲线 -->
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">足底高度曲线及腾空区间</p>
        <div ref="heightRef" class="w-full h-56"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { tooltipTheme } from '../../utils/chartTheme.js'
import { flightFrames as staticFlightFrames, globalStats as staticGlobalStats } from '../../data/bingbuData.js'

const props = defineProps({
  flightFrames: { type: Array, default: null },
  globalStats: { type: Object, default: null },
})

const flightFrames = computed(() => props.flightFrames || staticFlightFrames)
const globalStats = computed(() => props.globalStats || staticGlobalStats)

const scatterRef = ref(null)
const heightRef = ref(null)
const charts = []

function dg() { return { containLabel: true, top: 18, bottom: 32, left: 78, right: 10 } }
function da() { return { axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#475569', fontSize: 11 }, splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } } } }

onMounted(() => {
  // 悬空时间 vs 高度散点图
  if (scatterRef.value) {
    const c = echarts.init(scatterRef.value)
    const left = []
    const right = []
    const both = []
    // Compute flight events from real flightFrames data
    let idx = 0
    for (let i = 0; i < flightFrames.value.length; i++) {
      const f = flightFrames.value[i]
      if (f.support === 'left_airborne') {
        // Find consecutive left_airborne block
        let j = i, maxH = f.lh
        while (j < flightFrames.value.length && flightFrames.value[j].support === 'left_airborne') {
          maxH = Math.max(maxH, flightFrames.value[j].lh)
          j++
        }
        const dur = +(flightFrames.value[j - 1].t - f.t).toFixed(2)
        left.push([dur, +maxH.toFixed(3), ++idx])
        i = j - 1
      } else if (f.support === 'right_airborne') {
        let j = i, maxH = f.rh
        while (j < flightFrames.value.length && flightFrames.value[j].support === 'right_airborne') {
          maxH = Math.max(maxH, flightFrames.value[j].rh)
          j++
        }
        const dur = +(flightFrames.value[j - 1].t - f.t).toFixed(2)
        right.push([dur, +maxH.toFixed(3), ++idx])
        i = j - 1
      } else if (f.support === 'double_airborne') {
        let j = i, maxH = Math.max(f.lh, f.rh)
        while (j < flightFrames.value.length && flightFrames.value[j].support === 'double_airborne') {
          maxH = Math.max(maxH, flightFrames.value[j].lh, flightFrames.value[j].rh)
          j++
        }
        const dur = +(flightFrames.value[j - 1].t - f.t).toFixed(2)
        both.push([dur, +maxH.toFixed(3), ++idx])
        i = j - 1
      }
    }
    c.setOption({ tooltip: tooltipTheme(),
      grid: dg(),
      xAxis: { type: 'value', name: '悬空时间(s)', nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() },
      yAxis: { type: 'value', name: '平均悬空高度(m)', nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() },
      legend: { data: ['左脚', '右脚', '双脚'], textStyle: { color: '#94a3b8', fontSize: 11 }, right: 0, top: 0 },
      series: [
        { name: '左脚', type: 'scatter', data: left, symbolSize: 8, itemStyle: { color: '#38bdf8', shadowBlur: 3, shadowColor: '#38bdf866' } },
        { name: '右脚', type: 'scatter', data: right, symbolSize: 8, itemStyle: { color: '#10b981', shadowBlur: 3, shadowColor: '#10b98166' } },
        { name: '双脚', type: 'scatter', data: both, symbolSize: 10, itemStyle: { color: '#f59e0b', shadowBlur: 3, shadowColor: '#f59e0b66' } }
      ]
    })
    charts.push(c)
  }

  // 足底高度曲线
  if (heightRef.value) {
    const c = echarts.init(heightRef.value)
    const T = flightFrames.value.map(f => f.t)
    const lh = flightFrames.value.map(f => +f.lh.toFixed(3))
    const rh = flightFrames.value.map(f => +f.rh.toFixed(3))
    // Find airborne regions for markArea
    const airborneMarks = []
    let inAir = false, airStart = ''
    for (let i = 0; i < flightFrames.value.length; i++) {
      if (!inAir && flightFrames.value[i].support !== 'double_support') {
        inAir = true
        airStart = T[i].toFixed(1)
      } else if (inAir && flightFrames.value[i].support === 'double_support') {
        inAir = false
        airborneMarks.push([{ xAxis: airStart, itemStyle: { color: 'rgba(239,68,68,0.08)' } }, { xAxis: T[i].toFixed(1) }])
      }
    }
    c.setOption({ tooltip: tooltipTheme(),
      grid: dg(),
      xAxis: { type: 'category', data: T.map(v => v.toFixed(1)), axisLabel: { color: '#475569', fontSize: 10, interval: 9 }, ...da() },
      yAxis: { type: 'value', name: '高度(m)', nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() },
      legend: { data: ['左脚足底高', '右脚足底高', '腾空区间'], textStyle: { color: '#94a3b8', fontSize: 11 }, right: 0, top: 0 },
      series: [
        { name: '左脚足底高', type: 'line', data: lh, smooth: true, symbol: 'none', lineStyle: { color: '#38bdf8', width: 1.5 } },
        { name: '右脚足底高', type: 'line', data: rh, smooth: true, symbol: 'none', lineStyle: { color: '#f59e0b', width: 1.5, type: 'dashed' } },
        { name: '腾空区间', type: 'line', markArea: { silent: true, data: airborneMarks }, data: [], lineStyle: { opacity: 0 }, itemStyle: { opacity: 0 } }
      ]
    })
    charts.push(c)
  }
})

onBeforeUnmount(() => { charts.forEach(c => c.dispose()) })
</script>
