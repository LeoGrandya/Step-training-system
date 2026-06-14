<template>
  <div v-if="hasAnyData" class="bg-white border border-slate-200 rounded-xl p-4 shadow-lg glow-border-sky">
    <h3 class="text-slate-800 text-base font-semibold mb-3 flex items-center gap-2">
      <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
      对称性 · 数据下载
    </h3>

    <!-- 数据下载 -->
    <div v-if="downloadLinks.length" class="mb-3 bg-sky-50 rounded-lg border border-slate-200/60 p-3">
      <p class="text-sm text-slate-400 mb-2 font-medium">数据下载</p>
      <div class="flex flex-wrap gap-2">
        <a v-for="item in downloadLinks" :key="item.key" :href="item.url"
           class="inline-flex items-center gap-1 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs text-slate-700 hover:border-sky-400 hover:text-sky-600 transition-colors">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          {{ item.label }}
        </a>
      </div>
    </div>

    <!-- 图表区 — 只有有数据才渲染 -->
    <div class="grid grid-cols-1 gap-3" :class="chartCols">
      <div v-if="hasParallelCoords" class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">各移动轮次参数对比</p>
        <div ref="paraRef" class="w-full h-64"></div>
      </div>
      <div v-if="hasSymmetry" class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">左右腿对称性</p>
        <div ref="symRef" class="w-full aspect-square mx-auto" style="height:300px; max-width:350px"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'
import { tooltipTheme } from '../../utils/chartTheme.js'

const isDev = import.meta.env.DEV

const props = defineProps({
  downloads: { type: Array, default: () => [] },
  symmetry: Object,
  parallelCoords: Object,
})

const paraRef = ref(null)
const symRef = ref(null)
const charts = []

const downloadLinks = computed(() => {
  if (!props.downloads || !props.downloads.length) return []
  const labelMap = { frame_metrics_csv: '逐帧指标 CSV', session_summary_csv: '会话汇总 CSV', step_metrics_csv: '步伐指标 CSV', unit_metrics_csv: '单元指标 CSV' }
  return props.downloads.map(d => ({ key: d.key, url: d.url, label: labelMap[d.key] || d.key }))
})

const hasParallelCoords = computed(() => !!props.parallelCoords)
const hasSymmetry = computed(() => !!props.symmetry)
const hasAnyData = computed(() => hasParallelCoords.value || hasSymmetry.value)
const chartCols = computed(() => {
  const n = (hasParallelCoords.value ? 1 : 0) + (hasSymmetry.value ? 1 : 0)
  return n === 2 ? 'lg:grid-cols-2' : ''
})

function renderCharts() {
  if (hasParallelCoords.value && paraRef.value) {
    const c = echarts.init(paraRef.value)
    c.setOption(props.parallelCoords, true)
    charts.push(c)
  }
  if (hasSymmetry.value && symRef.value) {
    const c = echarts.init(symRef.value)
    c.setOption(props.symmetry, true)
    charts.push(c)
  }
}

onMounted(() => { renderCharts() })
watch(() => [props.symmetry, props.parallelCoords], () => { renderCharts() })

onBeforeUnmount(() => { charts.forEach(c => c.dispose()) })
</script>
