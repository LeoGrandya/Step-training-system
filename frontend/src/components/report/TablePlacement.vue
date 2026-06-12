<template>
  <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
    <div class="lg:col-span-8 bg-white border border-slate-200 rounded-xl p-4 shadow-lg glow-border-sky">
      <h3 class="text-slate-800 text-base font-semibold mb-3 flex items-center gap-2">
        <span class="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
        球桌区域步伐落点热力统计
        <span class="text-xs bg-slate-100 text-slate-400 px-2 py-0.5 rounded-full ml-auto">实时轨迹追踪</span>
      </h3>

      <div class="w-full h-60 bg-sky-50 rounded-lg relative overflow-hidden border border-slate-200/60">
        <div class="absolute inset-0 opacity-[0.04]"
             style="background-image: linear-gradient(rgba(255,255,255,.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.1) 1px, transparent 1px); background-size: 16px 16px;"></div>

        <div class="absolute inset-x-[10%] top-[8%] bottom-[12%]">
          <div class="absolute inset-0 rounded-sm"
               style="background: linear-gradient(180deg, rgba(14,165,233,0.12) 0%, rgba(14,165,233,0.04) 100%);
                      border: 1.5px solid rgba(56,189,248,0.35);
                      box-shadow: 0 0 30px rgba(56,189,248,0.1), inset 0 0 20px rgba(56,189,248,0.03);
                      transform: perspective(400px) rotateX(22deg);"></div>
          <div class="absolute left-0 right-0 top-1/2 -translate-y-1/2" style="transform: perspective(400px) rotateX(22deg); z-index: 2;">
            <div class="border-t border-dashed border-sky-400/30 w-full"></div>
          </div>
          <div class="absolute top-0 bottom-0 left-1/2" style="transform: perspective(400px) rotateX(22deg); z-index: 2;">
            <div class="border-l border-dashed border-white/10 h-full"></div>
          </div>
        </div>

        <div ref="tableChartRef" class="absolute inset-0 z-10"></div>

        <div class="absolute top-2 right-3 flex gap-3 text-[10px] z-20">
          <div class="flex items-center gap-1.5 bg-white/90 px-2 py-1 rounded border border-slate-200/60">
            <span class="w-2 h-2 rounded-full bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.6)]"></span>
            <span class="text-slate-700">正手位</span>
          </div>
          <div class="flex items-center gap-1.5 bg-white/90 px-2 py-1 rounded border border-slate-200/60">
            <span class="w-2 h-2 rounded-full bg-amber-500 shadow-[0_0_6px_rgba(245,158,11,0.6)]"></span>
            <span class="text-slate-700">反手位</span>
          </div>
          <div class="flex items-center gap-1.5 bg-white/90 px-2 py-1 rounded border border-slate-200/60">
            <span class="w-2 h-2 rounded-full bg-sky-500 shadow-[0_0_6px_rgba(56,189,248,0.6)]"></span>
            <span class="text-slate-700">台内小球</span>
          </div>
        </div>
      </div>
    </div>

    <div class="lg:col-span-4 bg-white border border-slate-200 rounded-xl p-4 shadow-lg flex flex-col glow-border-emerald">
      <h3 class="text-slate-800 text-base font-semibold mb-3 flex items-center gap-2">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
        AI 步伐动作优化建议
        <span class="text-xs bg-emerald-500/10 text-slate-900 px-1.5 py-0.5 rounded border border-emerald-500/20 ml-auto font-tech">AI 分析</span>
      </h3>

      <div class="flex-1 overflow-y-auto space-y-2.5 pr-1 text-xs">
        <div v-if="!aiItems.length" class="text-center py-8 text-slate-400 text-sm">暂无 AI 建议</div>
        <div v-for="(item, idx) in aiItems" :key="idx"
          :class="['p-3 bg-sky-50 rounded-lg border-l-[3px] relative overflow-hidden', item.borderClass]">
          <div class="absolute right-2 top-2 text-[10px] text-slate-900/40 font-tech">#{{ idx + 1 }}</div>
          <p class="text-slate-800 font-medium text-xs flex items-center gap-1.5">
            <span :class="['w-1.5 h-1.5 rounded-full', item.tagClass.replace('text-', 'bg-')]"></span>
            {{ item.title || '建议' }}
          </p>
          <p class="text-slate-400 text-[10px] mt-1 leading-relaxed">{{ item.text }}</p>
          <div class="mt-2 flex gap-1.5">
            <span :class="['text-xs px-1.5 py-0.5 rounded', item.badgeClass]">{{ item.severityLabel }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, computed } from 'vue'
import * as echarts from 'echarts'
import { tooltipTheme } from '../../utils/chartTheme.js'

const props = defineProps({
  tableScatter: { type: Object, default: null },
  tableHeatmap: { type: Object, default: null },
  aiInsights: { type: Array, default: () => [] },
})

const tableChartRef = ref(null)
let tableChart = null

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
  const forehandData = []; const backhandData = []; const shortData = []
  for (let i = 0; i < 40; i++) {
    forehandData.push([+Math.random().toFixed(2), +(Math.random() * 0.6 + 0.2).toFixed(2)])
    backhandData.push([+(Math.random() * 0.4 + 0.6).toFixed(2), +(Math.random() * 0.6 + 0.2).toFixed(2)])
    shortData.push([+(Math.random() * 0.3 + 0.35).toFixed(2), +(Math.random() * 0.25 + 0.1).toFixed(2)])
  }
  return {
    tooltip: tooltipTheme('item'),
    grid: { top: '8%', bottom: '12%', left: '10%', right: '10%' },
    xAxis: { min: 0, max: 1, show: false },
    yAxis: { min: 0, max: 1, show: false },
    series: [
      { name: '反手位', type: 'effectScatter', data: backhandData, symbolSize: 5, showEffectOn: 'render', rippleEffect: { brushType: 'stroke', scale: 2.5, period: 4 }, itemStyle: { color: '#f59e0b', shadowBlur: 4, shadowColor: '#f59e0b88' } },
      { name: '正手位', type: 'effectScatter', data: forehandData, symbolSize: 5, showEffectOn: 'render', rippleEffect: { brushType: 'stroke', scale: 2.5, period: 4 }, itemStyle: { color: '#ef4444', shadowBlur: 4, shadowColor: '#ef444488' } },
      { name: '台内小球', type: 'effectScatter', data: shortData, symbolSize: 4, showEffectOn: 'render', rippleEffect: { brushType: 'fill', scale: 3, period: 3 }, itemStyle: { color: '#38bdf8', shadowBlur: 4, shadowColor: '#38bdf888' } },
    ],
  }
}

function renderChart(opt) {
  if (!tableChartRef.value) return
  if (!tableChart) tableChart = echarts.init(tableChartRef.value)
  tableChart.setOption(opt || mockOption(), true)
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
