<template>
  <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-[1fr_1fr_1fr_1.5fr_1.5fr_1.5fr] gap-3">
    <!-- 环形图指标卡 -->
    <div
      v-for="(item, idx) in donutMetrics"
      :key="idx"
      class="bg-white border border-slate-200 rounded-xl p-3 flex flex-col justify-between relative overflow-hidden glow-border-sky min-h-[130px]"
      style="animation: glowPulse 3s ease-in-out infinite;"
    >
      <!-- 顶部标签 -->
      <div class="flex items-center justify-between mb-1">
        <span class="text-[11px] text-slate-400 font-medium tracking-wide">{{ item.title }}</span>
        <span
          :class="item.trendUp ? 'text-slate-900' : 'text-rose-400'"
          class="text-[10px] font-tech"
        >
          {{ item.trendUp ? '▲' : '▼' }} {{ item.compare }}
        </span>
      </div>

      <!-- 环形图 -->
      <div class="flex-1 min-h-0" :ref="el => setDonutRef(el, idx)"></div>

      <!-- 底部标签 -->
      <div class="text-center mt-1">
        <span class="text-[11px] text-slate-400">完成率</span>
      </div>
    </div>

    <!-- 数字指标卡 -->
    <div
      v-for="(stat, sIdx) in textStats"
      :key="'s-' + sIdx"
      class="bg-white border border-slate-200 rounded-xl p-3 flex flex-col justify-between relative overflow-hidden glow-border-emerald min-w-[168px]"
    >
      <!-- 标签 -->
      <div class="flex items-center justify-between mb-2">
        <span class="text-[11px] text-slate-400 font-medium">{{ stat.label }}</span>
        <span
          :class="stat.isUp ? 'bg-emerald-500/10 text-slate-900 border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20'"
          class="text-[10px] px-1.5 py-0.5 rounded border font-tech"
        >
          {{ stat.isUp ? '▲' : '▼' }} {{ stat.change }}
        </span>
      </div>

      <!-- 主数字 -->
      <div class="flex-1 flex items-center justify-center">
        <span
          :class="stat.isUp ? 'text-glow-sky' : 'text-glow-emerald'"
          class="text-3xl font-tech font-bold tracking-wider animate-number"
          style="color: #0f172a;"
        >
          {{ stat.value }}
        </span>
      </div>

      <!-- 底部刻度装饰 -->
      <div class="flex justify-center gap-0.5 mt-2">
        <div v-for="n in 20" :key="n" class="h-0.5 rounded-full"
             :class="n <= stat.barLength ? 'bg-sky-500' : 'bg-slate-700'"
             :style="{ width: '8px' }"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { tooltipTheme } from '../../utils/chartTheme.js'
import { globalStats as staticGlobalStats } from '../../data/bingbuData.js'

defineProps({
  globalStats: { type: Object, default: null },
})

const donutRefs = []
const setDonutRef = (el, idx) => {
  if (el) donutRefs[idx] = el
}

// 朱雪毅 并步 2-1 真实数据
const donutMetrics = [
  { title: '移动步伐配比', compare: '移动占70%', trendUp: true, color: '#38bdf8', val: 70 },
  { title: '并步/滑步转换率', compare: 'bq=923%', trendUp: true, color: '#10b981', val: 76 },
  { title: '启动响应成功率', compare: '均值91ms', trendUp: true, color: '#f59e0b', val: 85 }
]

const textStats = [
  { label: '总训练步数(步)', value: '42', change: '14周期', isUp: true, barLength: 16 },
  { label: '移动启动次数', value: '14', change: '14还原', isUp: false, barLength: 12 },
  { label: '高峰期步频', value: '121', change: '步/分', isUp: true, barLength: 18 }
]

let charts = []

onMounted(() => {
  nextTick(() => {
    donutRefs.forEach((dom, index) => {
      if (!dom) return
      const chart = echarts.init(dom)
      const metric = donutMetrics[index]

      chart.setOption({ tooltip: tooltipTheme('item'),
        series: [{
          type: 'pie',
          radius: ['65%', '85%'],
          avoidLabelOverlap: false,
          label: {
            show: true,
            position: 'center',
            formatter: `{big|${metric.val}}%\n{small|完成}`,
            rich: {
              big: {
                fontSize: 18,
                fontWeight: 'bold',
                color: '#0f172a',
                fontFamily: 'Orbitron',
                lineHeight: 24
              },
              small: {
                fontSize: 11,
                color: '#64748b',
                lineHeight: 14
              }
            }
          },
          labelLine: { show: false },
          silent: true,
          data: [
            {
              value: metric.val,
              itemStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 1, 1, [
                  { offset: 0, color: metric.color },
                  { offset: 1, color: metric.color + '99' }
                ]),
                shadowBlur: 10,
                shadowColor: metric.color + '66'
              }
            },
            {
              value: 100 - metric.val,
              itemStyle: { color: '#e2e8f0' }
            }
          ]
        }]
      })
      charts.push(chart)
    })
  })
})

onBeforeUnmount(() => {
  charts.forEach(c => c.dispose())
})
</script>
