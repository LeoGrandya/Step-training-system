<template>
  <div v-if="hasAnyContent" class="grid grid-cols-1 lg:grid-cols-12 gap-4">
    <div v-if="hasTableData" class="lg:col-span-8 bg-white border border-slate-200 rounded-xl p-4 shadow-lg glow-border-sky">
      <h3 class="text-slate-800 text-base font-semibold mb-3 flex items-center gap-2">
        <span class="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
        球桌区域步伐落点
      </h3>

      <div class="w-full h-60 bg-sky-50 rounded-lg relative overflow-hidden border border-slate-200/60">
        <div ref="tableChartRef" class="absolute inset-0 z-10"></div>

      </div>
    </div>

    <div v-if="aiItems.length" class="lg:col-span-4 bg-white border border-slate-200 rounded-xl p-4 shadow-lg flex flex-col glow-border-emerald">
      <h3 class="text-slate-800 text-base font-semibold mb-3 flex items-center gap-2">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
        训练改进建议
        <span class="text-xs bg-emerald-500/10 text-slate-900 px-1.5 py-0.5 rounded border border-emerald-500/20 ml-auto font-tech">AI 分析</span>
      </h3>

      <div class="flex-1 overflow-y-auto space-y-2.5 pr-1 text-xs">
        <div v-for="(item, idx) in aiItems" :key="idx"
          :class="['p-3 rounded-lg border-l-[3px] relative overflow-hidden', item.borderClass, item.severity === 'warn' ? 'bg-amber-50' : item.severity === 'good' ? 'bg-sky-50' : item.severity === 'excellent' ? 'bg-emerald-50' : 'bg-slate-50']">
          <div class="absolute right-2 top-2 text-[10px] text-slate-900/30 font-tech">#{{ idx + 1 }}</div>
          <p class="text-slate-800 font-semibold text-xs flex items-center gap-1.5">
            <span :class="['w-1.5 h-1.5 rounded-full', item.tagClass.replace('text-', 'bg-')]"></span>
            {{ item.title || '建议' }}
            <span :class="['text-[10px] px-1 py-0 rounded-full ml-auto', item.badgeClass]">{{ item.severityLabel }}</span>
          </p>
          <p class="text-slate-500 text-[10px] mt-1.5 leading-relaxed">{{ item.text }}</p>
          <p v-if="item.action" class="text-sky-700 text-[10px] mt-1.5 leading-relaxed font-medium bg-sky-500/5 px-2 py-1 rounded">🎯 {{ item.action }}</p>
        </div>
        <div class="text-center text-[10px] text-slate-400 pt-1">以上建议基于本次分析数据自动生成，供教练参考</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, computed } from 'vue'
import * as echarts from 'echarts'
import { tooltipTheme } from '../../utils/chartTheme.js'

const isDev = import.meta.env.DEV

const props = defineProps({
  tableScatter: { type: Object, default: null },
  tableHeatmap: { type: Object, default: null },
  aiInsights: { type: Array, default: () => [] },
})

const tableChartRef = ref(null)
let tableChart = null

const hasTableData = computed(() => !!(props.tableScatter || props.tableHeatmap))
const hasAnyContent = computed(() => hasTableData.value || aiItems.value.length > 0)

const severityMap = {
  excellent: { borderClass: 'border-emerald-400', tagClass: 'text-emerald-500', badgeClass: 'bg-emerald-500/10 text-slate-900', severityLabel: '优秀' },
  good: { borderClass: 'border-sky-400', tagClass: 'text-sky-500', badgeClass: 'bg-sky-500/10 text-slate-900', severityLabel: '良好' },
  warn: { borderClass: 'border-amber-400', tagClass: 'text-amber-500', badgeClass: 'bg-amber-500/10 text-slate-900', severityLabel: '待改进' },
  info: { borderClass: 'border-sky-400', tagClass: 'text-violet-500', badgeClass: 'bg-violet-500/10 text-slate-900', severityLabel: '数据' },
}

const aiItems = computed(() => {
  if (!props.aiInsights || !props.aiInsights.length) return []
  return props.aiInsights.slice(0, 6).map((item, idx) => ({
    ...item,
    ...(severityMap[item.severity] || severityMap.info),
    title: item.title || `建议 ${idx + 1}`,
  }))
})

function mockOption() {
  const pts = []; for (let i = 0; i < 50; i++) pts.push([+Math.random().toFixed(3), +Math.random().toFixed(3)])
  return {
    tooltip: tooltipTheme('item'),
    grid: { top: '8%', bottom: '12%', left: '10%', right: '10%' },
    xAxis: { min: 0, max: 1, show: false },
    yAxis: { min: 0, max: 1, show: false },
    series: [{ type: 'effectScatter', data: pts, symbolSize: 5, showEffectOn: 'render', rippleEffect: { brushType: 'stroke', scale: 2.5, period: 4 }, itemStyle: { color: '#38bdf8', shadowBlur: 4, shadowColor: '#38bdf888' } }],
  }
}

function renderChart(opt) {
  if (!tableChartRef.value) return
  if (!tableChart) tableChart = echarts.init(tableChartRef.value)
  if (opt) tableChart.setOption(opt, true)
  else if (isDev) tableChart.setOption(mockOption(), true)
}

onMounted(() => {
  const opt = props.tableScatter || props.tableHeatmap
  renderChart(opt)
})

watch(() => [props.tableScatter, props.tableHeatmap], () => {
  const opt = props.tableScatter || props.tableHeatmap
  renderChart(opt)
})

onBeforeUnmount(() => { tableChart?.dispose() })
</script>
