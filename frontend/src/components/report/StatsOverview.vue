<template>
  <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-[1fr_1fr_1fr_1.5fr_1.5fr_1.5fr] gap-3">
    <div v-for="(item, idx) in donutMetrics" :key="idx"
      class="bg-white border border-slate-200 rounded-xl p-3 flex flex-col justify-between relative overflow-hidden glow-border-sky"
      style="animation: glowPulse 3s ease-in-out infinite;">
      <div class="flex items-center justify-between mb-1">
        <span class="text-[11px] text-slate-400 font-medium tracking-wide">{{ item.title }}</span>
        <span :class="item.trendUp ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20' : 'bg-amber-500/10 text-amber-600 border-amber-500/20'" class="text-[10px] px-1.5 py-0.5 rounded-full border font-tech">{{ item.label }}</span>
      </div>
      <div class="flex-1 min-h-0" :ref="el => setDonutRef(el, idx)" style="min-height:80px"></div>
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
import { computed, nextTick, onMounted, watch } from 'vue'
import * as echarts from 'echarts'
import { useECharts } from '../../composables/useECharts.js'

const props = defineProps({
  statsRaw: { type: Object, default: () => ({}) },
  dirPie: { type: Object, default: null },
})

const donutRefs = []
const setDonutRef = (el, idx) => { if (el) donutRefs[idx] = el }
const { initChart, disposeAll } = useECharts()

function speedLabel(v) { if (v <= 0) return '无数据'; if (v >= 2.5) return '优秀'; if (v >= 2.0) return '良好'; return '待提升' }
function symLabel(v) { if (v === 999 || v == null) return '无数据'; if (v <= 0.05) return '优秀'; if (v <= 0.10) return '良好'; return '待提升' }
function activeLabel(v) { if (v <= 0) return '无数据'; if (v >= 80) return '专注'; if (v >= 60) return '正常'; return '偏低' }

const donutMetrics = computed(() => {
  const summary = props.statsRaw?.summary || {}
  const derived = props.statsRaw?.derived || {}
  const quality = props.statsRaw?.quality || {}
  const speed = summary.mean_com_speed_mps ?? 0
  const activeRatio = (quality.analysisActiveRatio ?? 0) * 100
  const asym = derived.clearance_asymmetry_peak_m ?? 999
  const symVal = asym !== 999 && asym != null ? Math.max(0, Math.round((1 - Math.min(asym, 0.3) / 0.3) * 100)) : 0
  return [
    { title: '移动速度', label: speedLabel(speed), val: speed > 0 ? Math.min(95, Math.max(5, Math.round(speed * 30))) : 0,
      centerText: speed > 0 ? `${speed.toFixed(1)}` : '-', centerUnit: 'm/s', trendUp: speed > 1.5 },
    { title: '训练活跃度', label: activeLabel(activeRatio), val: Math.round(activeRatio),
      centerText: activeRatio > 0 ? `${activeRatio.toFixed(0)}` : '-', centerUnit: '%', trendUp: activeRatio > 50 },
    { title: '左右均衡度', label: symLabel(asym), val: symVal,
      centerText: symVal > 0 ? `${symVal}` : '-', centerUnit: '分', trendUp: symVal > 70 },
  ]
})

const textStats = computed(() => {
  const summary = props.statsRaw?.summary || {}
  const derived = props.statsRaw?.derived || {}
  const quality = props.statsRaw?.quality || {}
  const cycleCount = quality.cycleCount ?? 0
  const stepCount = props.statsRaw?.stepCount ?? 0
  const peakSpeed = summary.peak_com_speed_mps ?? derived?.com_speed_p95_mps ?? 0
  const accel = derived.com_accel_abs_p95_mps2 ?? 0
  const duration = derived.duration_s ?? summary.duration_s ?? 0
  return [
    { label: '移动轮次', display: cycleCount > 0 ? `${cycleCount} 轮` : '暂无', isUp: cycleCount > 2, barLength: Math.min(20, Math.max(1, cycleCount)) },
    { label: '总步数', display: stepCount > 0 ? `${stepCount} 步` : '暂无', isUp: stepCount > 5, barLength: Math.min(20, Math.max(1, Math.round(stepCount / 3))) },
    { label: '峰值加速度', display: accel > 0 ? `${accel.toFixed(1)} m/s²` : '暂无', isUp: accel > 4, barLength: Math.min(20, Math.max(1, Math.round(accel))) },
  ]
})

function renderDonuts() {
  disposeAll()
  donutRefs.forEach((dom, idx) => {
    if (!dom) return
    const m = donutMetrics.value[idx]
    if (!m) return
    const colors = ['#38bdf8', '#10b981', '#f59e0b']
    initChart(dom, {
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie', radius: ['75%', '92%'], silent: true,
        label: { show: true, position: 'center',
          formatter: `{big|${m.centerText}}\n{small|${m.centerUnit}}`,
          rich: { big: { fontSize: 22, fontWeight: 'bold', color: '#0f172a', fontFamily: 'Orbitron', lineHeight: 28 }, small: { fontSize: 10, color: '#64748b', lineHeight: 12 } },
        },
        labelLine: { show: false },
        data: [
          { value: m.val, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 1, [{ offset: 0, color: colors[idx] }, { offset: 1, color: colors[idx] + '99' }]), shadowBlur: 10, shadowColor: colors[idx] + '66' } },
          { value: 100 - m.val, itemStyle: { color: '#e2e8f0' } },
        ],
      }],
    })
  })
}

onMounted(() => nextTick(renderDonuts))
watch([donutMetrics], () => nextTick(renderDonuts), { deep: true })
</script>
