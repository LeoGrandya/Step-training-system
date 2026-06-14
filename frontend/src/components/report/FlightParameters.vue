<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-lg glow-border-sky">
    <h3 class="text-slate-800 text-base font-semibold mb-3 flex items-center gap-2">
      <span class="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse"></span>
      四、腾空参数分析
      <span class="text-xs bg-slate-100 text-slate-400 px-2 py-0.5 rounded-full ml-auto">腾空检测</span>
    </h3>
    <p class="text-sm text-slate-400 leading-relaxed mb-3 border-l-2 border-rose-500/30 pl-2.5">腾空高度普遍低于0.08m，悬空时间集中在0.15-0.20s区间。左脚单次最大悬空时间达0.25s但高度仅0.06m，反映该侧蹬伸效率有待提升。足底高度曲线表明腾空主要发生在段3和段5的大范围跨步中。建议通过针对性爆发力训练改善左脚起跳协调性。</p>
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <!-- 悬空时间与高度散点图 -->
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">悬空时间 vs 悬空高度</p>
        <div v-if="hasAirborne" ref="scatterRef" class="w-full h-56"></div>
        <ReportEmptyState v-else text="暂无腾空数据" />
      </div>
      <!-- 足底高度曲线 -->
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">足底高度曲线及腾空区间</p>
        <div v-if="hasFootHeight" ref="heightRef" class="w-full h-56"></div>
        <ReportEmptyState v-else text="暂无足底高度数据" />
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
  airborne: Object,
  footHeight: Object
})

const scatterRef = ref(null)
const heightRef = ref(null)
const charts = []

const hasAirborne = computed(() => !!props.airborne)
const hasFootHeight = computed(() => !!props.footHeight)

function dg() { return { top: 18, bottom: 22, left: 46, right: 10 } }
function da() { return { axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#475569', fontSize: 11 }, splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } } } }

function mockAirborne() {
  const left = [], right = [], both = []
  for (let i = 0; i < 25; i++) {
    left.push([+(0.08 + Math.random() * 0.2).toFixed(2), +(0.02 + Math.random() * 0.08).toFixed(3), i + 1])
    right.push([+(0.1 + Math.random() * 0.22).toFixed(2), +(0.03 + Math.random() * 0.09).toFixed(3), i + 26])
    both.push([+(0.15 + Math.random() * 0.15).toFixed(2), +(0.05 + Math.random() * 0.1).toFixed(3), i + 51])
  }
  return {
    tooltip: tooltipTheme(),
    grid: dg(),
    xAxis: { type: 'value', name: '悬空时间(s)', nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() },
    yAxis: { type: 'value', name: '平均悬空高度(m)', nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() },
    legend: { data: ['左脚', '右脚', '双脚'], textStyle: { color: '#94a3b8', fontSize: 11 }, right: 0, top: 0 },
    series: [
      { name: '左脚', type: 'scatter', data: left, symbolSize: 8, itemStyle: { color: '#38bdf8', shadowBlur: 3, shadowColor: '#38bdf866' } },
      { name: '右脚', type: 'scatter', data: right, symbolSize: 8, itemStyle: { color: '#10b981', shadowBlur: 3, shadowColor: '#10b98166' } },
      { name: '双脚', type: 'scatter', data: both, symbolSize: 10, itemStyle: { color: '#f59e0b', shadowBlur: 3, shadowColor: '#f59e0b66' } }
    ]
  }
}

function mockFootHeight() {
  const T = Array.from({ length: 120 }, (_, i) => +(i * 0.04).toFixed(2))
  const heel = T.map(x => Math.max(0, Math.sin(x * 2.5) * 0.06 + Math.cos(x * 1.8) * 0.04 + Math.random() * 0.01))
  const toe = T.map(x => Math.max(0, Math.sin(x * 2.3) * 0.07 + Math.cos(x * 1.6) * 0.05 + Math.random() * 0.012))
  return {
    tooltip: tooltipTheme(),
    grid: dg(),
    xAxis: { type: 'category', data: T.map(v => v.toFixed(1)), axisLabel: { color: '#475569', fontSize: 10, interval: 29 }, ...da() },
    yAxis: { type: 'value', name: '高度(m)', nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() },
    legend: { data: ['足跟均值', '足尖均值', '腾空区间'], textStyle: { color: '#94a3b8', fontSize: 11 }, right: 0, top: 0 },
    series: [
      { name: '足跟均值', type: 'line', data: heel, smooth: true, symbol: 'none', lineStyle: { color: '#38bdf8', width: 1.5 } },
      { name: '足尖均值', type: 'line', data: toe, smooth: true, symbol: 'none', lineStyle: { color: '#f59e0b', width: 1.5, type: 'dashed' } },
      { name: '腾空区间', type: 'line', markArea: { silent: true, data: [[{ xAxis: '0.8', itemStyle: { color: 'rgba(239,68,68,0.08)' } }, { xAxis: '1.0' }], [{ xAxis: '2.4', itemStyle: { color: 'rgba(239,68,68,0.08)' } }, { xAxis: '2.7' }], [{ xAxis: '3.6', itemStyle: { color: 'rgba(239,68,68,0.08)' } }, { xAxis: '3.9' }]] }, data: [], lineStyle: { opacity: 0 }, itemStyle: { opacity: 0 } }
    ]
  }
}

function renderCharts() {
  charts.forEach(c => c.dispose())
  charts.length = 0
  if (scatterRef.value) {
    const c = echarts.init(scatterRef.value)
    if (props.airborne) c.setOption(props.airborne, true)
    else if (isDev) c.setOption(mockAirborne(), true)
    charts.push(c)
  }
  if (heightRef.value) {
    const c = echarts.init(heightRef.value)
    if (props.footHeight) c.setOption(props.footHeight, true)
    else if (isDev) c.setOption(mockFootHeight(), true)
    charts.push(c)
  }
}

onMounted(() => { renderCharts() })
watch(() => [props.airborne, props.footHeight], () => { renderCharts() })

onBeforeUnmount(() => { charts.forEach(c => c.dispose()) })
</script>
