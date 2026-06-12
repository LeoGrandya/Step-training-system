<template>
  <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-[1fr_1fr_1fr_1.5fr_1.5fr_1.5fr] gap-3">
    <div v-for="(item, idx) in donutMetrics" :key="idx"
      class="bg-white border border-slate-200 rounded-xl p-3 flex flex-col justify-between relative overflow-hidden glow-border-sky"
      style="animation: glowPulse 3s ease-in-out infinite;">
      <div class="flex items-center justify-between mb-1">
        <span class="text-[11px] text-slate-400 font-medium tracking-wide">{{ item.title }}</span>
        <span :class="item.trendUp ? 'text-sky-500' : 'text-rose-400'" class="text-[10px] font-tech">{{ item.trendUp ? '▲' : '▼' }} {{ item.compare }}</span>
      </div>
      <div class="flex-1 min-h-0" :ref="el => setDonutRef(el, idx)" style="min-height:80px"></div>
      <div class="text-center mt-1"><span class="text-[11px] text-slate-400">完成率</span></div>
    </div>

    <div v-for="(stat, sIdx) in textStats" :key="'s-' + sIdx"
      class="bg-white border border-slate-200 rounded-xl p-3 flex flex-col justify-between relative overflow-hidden glow-border-emerald">
      <div class="flex items-center justify-between mb-2">
        <span class="text-[11px] text-slate-400 font-medium">{{ stat.label }}</span>
        <span :class="stat.isUp ? 'bg-emerald-500/10 text-slate-900 border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20'"
              class="text-[10px] px-1.5 py-0.5 rounded border font-tech">{{ stat.isUp ? '▲' : '▼' }} {{ stat.change }}</span>
      </div>
      <div class="flex-1 flex items-center justify-center">
        <span :class="stat.isUp ? 'text-glow-sky' : 'text-glow-emerald'"
              class="text-3xl font-tech font-bold tracking-wider animate-number" style="color: #0f172a;">{{ stat.display }}</span>
      </div>
      <div class="flex justify-center gap-0.5 mt-2 overflow-hidden">
        <div v-for="n in 20" :key="n" class="h-0.5 rounded-full"
             :class="n <= stat.barLength ? 'bg-sky-500' : 'bg-slate-200'" :style="{ width: '8px' }"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  statsRaw: { type: Object, default: () => ({}) },
  dirPie: { type: Object, default: null },
})

const donutRefs = []
const setDonutRef = (el, idx) => { if (el) donutRefs[idx] = el }
let charts = []

const donutMetrics = computed(() => {
  const summary = props.statsRaw?.summary || {}
  const derived = props.statsRaw?.derived || {}
  const quality = props.statsRaw?.quality || {}
  const speed = summary.mean_com_speed_mps ?? 0
  const activeRatio = (quality.analysisActiveRatio ?? 0) * 100
  const asym = derived.clearance_asymmetry_peak_m ?? 999
  const symScore = asym < 0.05 ? 92 : asym < 0.10 ? 78 : 60
  return [
    { title: '移动速度指数', compare: `${Number(speed).toFixed(1)} m/s`, val: Math.min(95, Math.round(speed * 30)), trendUp: speed > 1.5 },
    { title: '有效活动占比', compare: `${activeRatio.toFixed(0)}%`, val: Math.round(activeRatio), trendUp: activeRatio > 50 },
    { title: '对称性评分', compare: `${symScore}分`, val: symScore, trendUp: symScore > 70 },
  ]
})

const textStats = computed(() => {
  const summary = props.statsRaw?.summary || {}
  const derived = props.statsRaw?.derived || {}
  const quality = props.statsRaw?.quality || {}
  const cycleCount = quality.cycleCount ?? 0
  const stepCount = props.statsRaw?.stepCount ?? 0
  const peakSpeed = summary.peak_com_speed_mps ?? derived?.com_speed_p95_mps ?? 0
  return [
    { label: '总移动周期', display: cycleCount ? String(cycleCount) : '-', change: '', isUp: true, barLength: Math.min(20, cycleCount * 2) },
    { label: '总步数', display: stepCount ? String(stepCount) : '-', change: '', isUp: true, barLength: Math.min(20, Math.round(stepCount / 20)) },
    { label: '峰值速度', display: peakSpeed ? `${Number(peakSpeed).toFixed(1)} m/s` : '-', change: '', isUp: true, barLength: Math.min(20, Math.round(peakSpeed * 7)) },
  ]
})

function renderDonuts() {
  charts.forEach(c => c.dispose())
  charts = []
  donutRefs.forEach((dom, idx) => {
    if (!dom) return
    const chart = echarts.init(dom)
    const m = donutMetrics.value[idx]
    if (!m) return
    const colors = ['#38bdf8', '#10b981', '#f59e0b']
    chart.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie', radius: ['75%', '92%'], silent: true,
        label: { show: true, position: 'center',
          formatter: `{big|${m.val}}%\n{small|${m.title}}`,
          rich: { big: { fontSize: 18, fontWeight: 'bold', color: '#0f172a', fontFamily: 'Orbitron', lineHeight: 24 }, small: { fontSize: 11, color: '#64748b', lineHeight: 14 } },
        },
        labelLine: { show: false },
        data: [
          { value: m.val, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 1, [{ offset: 0, color: colors[idx] }, { offset: 1, color: colors[idx] + '99' }]), shadowBlur: 10, shadowColor: colors[idx] + '66' } },
          { value: 100 - m.val, itemStyle: { color: '#e2e8f0' } },
        ],
      }],
    })
    charts.push(chart)
  })
}

onMounted(() => nextTick(renderDonuts))
watch([donutMetrics], () => nextTick(renderDonuts), { deep: true })
onBeforeUnmount(() => charts.forEach(c => c.dispose()))
</script>
