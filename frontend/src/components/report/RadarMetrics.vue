<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-lg glow-border-sky flex flex-col" style="min-height: 420px;">
    <h3 class="text-slate-800 text-base font-semibold mb-3 flex items-center justify-between">
      <span class="flex items-center gap-2">
        <span class="w-1.5 h-1.5 rounded-full bg-sky-500 animate-pulse"></span>
        足技技巧多维评估
      </span>
      <span class="text-xs bg-slate-100 text-slate-400 px-2 py-0.5 rounded-full">5维模型</span>
    </h3>

    <div class="grid grid-cols-2 gap-3 flex-1 min-h-0">
      <!-- 左侧：雷达图 + 指标卡 -->
      <div class="flex flex-col gap-2">
        <div ref="radarChartRef" class="flex-1 min-h-0 bg-sky-50 rounded-lg border border-slate-200/60"></div>
        <div class="grid grid-cols-2 gap-2">
          <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2 text-center">
            <p class="text-[11px] text-slate-400 mb-0.5">移动总距离</p>
            <p class="text-lg font-tech font-bold text-slate-900 text-glow-sky">17.3<span class="text-xs">m</span></p>
          </div>
          <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2 text-center">
            <p class="text-[11px] text-slate-400 mb-0.5">平均变向时间</p>
            <p class="text-lg font-tech font-bold text-slate-900 text-glow-emerald">91<span class="text-xs">ms</span></p>
          </div>
        </div>
      </div>

      <!-- 右侧：趋势图 -->
      <div class="flex flex-col">
        <h4 class="text-[11px] text-slate-400 font-medium mb-1">全员移动目标趋势</h4>
        <div class="flex gap-2 text-[10px] mb-1">
          <span class="flex items-center gap-1"><span class="w-2 h-0.5 bg-sky-400"></span>平均移速</span>
          <span class="flex items-center gap-1"><span class="w-2 h-0.5 bg-emerald-400"></span>步频</span>
        </div>
        <div ref="lineChartRef" class="flex-1 min-h-0 bg-sky-50 rounded-lg border border-slate-200/60"></div>

        <!-- LOTT 数据摘要 -->
        <div class="mt-2 grid grid-cols-3 gap-1 text-center">
          <div class="bg-sky-50 rounded p-1.5 border border-slate-200/60">
            <p class="text-[11px] text-slate-400">最大移速</p>
            <p class="text-xs font-tech text-slate-900">2.05<span class="text-[10px]">m/s</span></p>
          </div>
          <div class="bg-sky-50 rounded p-1.5 border border-slate-200/60">
            <p class="text-[11px] text-slate-400">平均步频</p>
            <p class="text-xs font-tech text-slate-900">121<span class="text-[10px]">步/分</span></p>
          </div>
          <div class="bg-sky-50 rounded p-1.5 border border-slate-200/60">
            <p class="text-[11px] text-slate-400">KLI均值</p>
            <p class="text-xs font-tech text-slate-900">0.30<span class="text-[10px]">%</span></p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import * as echarts from 'echarts'
import { tooltipTheme } from '../../utils/chartTheme.js'
import { radarData as staticRadarData, globalStats as staticGlobalStats } from '../../data/bingbuData.js'

const props = defineProps({
  radarData: { type: Object, default: null },
  globalStats: { type: Object, default: null },
})

const radar = computed(() => props.radarData || staticRadarData)

const radarChartRef = ref(null)
const lineChartRef = ref(null)
let radarChart = null
let lineChart = null

onMounted(() => {
  // 雷达图 - 朱雪毅并步5维评估
  if (radarChartRef.value && radar.value) {
    radarChart = echarts.init(radarChartRef.value)
    radarChart.setOption({ tooltip: tooltipTheme('item'),
      radar: {
        center: ['50%', '52%'],
        radius: '60%',
        indicator: [
          { name: '爆发力', max: 100 },
          { name: '速度', max: 100 },
          { name: '敏捷性', max: 100 },
          { name: '稳定性', max: 100 },
          { name: '耐力', max: 100 }
        ],
        axisName: { color: '#94a3b8', fontSize: 11, fontWeight: '500' },
        axisLine: { lineStyle: { color: '#334155' } },
        splitLine: { lineStyle: { color: '#e2e8f0' } },
        splitArea: {
          areaStyle: { color: ['#0f172a', '#0f172a'] }
        }
      },
      series: [{
        type: 'radar',
        data: [{
          value: [radar.value.power, radar.value.speed, radar.value.agility, radar.value.stability, radar.value.endurance],
          name: '朱雪毅·并步',
          symbol: 'circle',
          symbolSize: 4,
          itemStyle: {
            color: '#38bdf8',
            shadowBlur: 8,
            shadowColor: '#38bdf888'
          },
          lineStyle: { color: '#38bdf8', width: 1.5, shadowBlur: 6, shadowColor: '#38bdf866' },
          areaStyle: {
            color: new echarts.graphic.RadialGradient(0.5, 0.5, 1, [
              { offset: 0, color: 'rgba(56,189,248,0.35)' },
              { offset: 1, color: 'rgba(56,189,248,0.05)' }
            ])
          }
        }]
      }]
    })
  }

  // 趋势折线图 - 4周期真实趋势
  if (lineChartRef.value && radar.value) {
    lineChart = echarts.init(lineChartRef.value)
    lineChart.setOption({ tooltip: tooltipTheme(),
      grid: { containLabel: true, top: 8, bottom: 22, left: 32, right: 8 },
      xAxis: {
        type: 'category',
        data: radar.value.trendLabels,
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: { color: '#475569', fontSize: 11 },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } },
        axisLabel: { color: '#475569', fontSize: 11 },
        axisLine: { show: false }
      },
      series: [
        {
          name: '平均移速',
          type: 'line',
          smooth: true,
          symbol: 'circle',
          symbolSize: 4,
          data: radar.value.trendSpeed,
          itemStyle: { color: '#38bdf8' },
          lineStyle: { width: 2, shadowBlur: 6, shadowColor: '#38bdf866' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(56,189,248,0.25)' },
              { offset: 1, color: 'rgba(56,189,248,0.02)' }
            ])
          }
        },
        {
          name: '步频',
          type: 'line',
          smooth: true,
          symbol: 'circle',
          symbolSize: 4,
          data: radar.value.trendCadence,
          itemStyle: { color: '#10b981' },
          lineStyle: { width: 2, shadowBlur: 6, shadowColor: '#10b98166' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(16,185,129,0.25)' },
              { offset: 1, color: 'rgba(16,185,129,0.02)' }
            ])
          }
        }
      ]
    })
  }
})

onBeforeUnmount(() => {
  radarChart?.dispose()
  lineChart?.dispose()
})
</script>
