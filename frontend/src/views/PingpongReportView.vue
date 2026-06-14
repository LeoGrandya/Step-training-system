<template>
  <div class="min-h-screen bg-sky-50 text-slate-900 flex flex-col font-sans selection:bg-sky-500/30 selection:text-white">
    <!-- 顶栏 -->
    <header class="bg-white/90 backdrop-blur border-b border-slate-200 px-5 py-3 flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-3">
        <h1 class="text-sm font-bold text-slate-800 tracking-wide">{{ subjectDisplay || '受试者' }} · 步伐分析报告</h1>
        <span v-if="statusText" class="text-xs bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-500/20 font-tech flex items-center gap-1">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
          {{ statusText }}
        </span>
      </div>
      <div v-if="stepDisplay" class="text-xs text-slate-400 font-tech">{{ stepDisplay }}</div>
    </header>

      <div v-if="loading" class="flex-1 flex items-center justify-center text-slate-400">报告加载中...</div>
      <div v-else-if="errorText" class="flex-1 flex flex-col items-center justify-center gap-3 text-rose-400">
        <p>{{ errorText }}</p>
        <button @click="loadReport()" class="px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm text-slate-700 hover:border-sky-400 hover:text-sky-600 transition-colors">重新加载</button>
      </div>

      <!-- 内容区 + 悬浮目录 -->
      <div v-else class="flex-1 flex min-h-0 relative">
        <div ref="contentScroll" class="p-3 space-y-6 overflow-y-auto flex-1 max-w-[1000px] mx-auto w-full" style="scroll-behavior: smooth;">
          <!-- 集中空状态 -->
          <div v-if="allSectionsEmpty" class="flex items-center justify-center py-20 text-slate-400">
            <div class="text-center">
              <p class="text-lg font-medium mb-2">暂无足量分析数据</p>
              <p class="text-sm">该任务的分析结果不足以生成报告，请检查原始视频质量或重新分析</p>
            </div>
          </div>

          <template v-else>
          <!-- 模块1：核心指标 -->
          <section>
            <h2 class="text-base font-bold text-slate-800 mb-1">核心指标</h2>
            <p class="text-xs text-slate-400 mb-3">移动速度、均衡度、训练专注度等关键数据一览</p>
            <div id="toc-stats"><StatsOverview :statsRaw="statsRaw" :dirPie="charts.dirPie" /></div>
          </section>

          <!-- 模块2：球场覆盖与移动 -->
          <section>
            <h2 class="text-base font-bold text-slate-800 mb-1">球场覆盖与移动</h2>
            <p class="text-xs text-slate-400 mb-3">展示运动员在球桌周围的移动轨迹、速度和加速度表现</p>
            <div id="toc-table" v-if="sectionVis.table"><TablePlacement :tableScatter="charts.tableScatter" :tableHeatmap="charts.tableHeatmap" :aiInsights="charts.aiInsights" /></div>
            <div id="toc-speed" v-if="sectionVis.speed" class="mt-3"><SpeedAcceleration :speedAccelDual="charts.speedAccelDual" :speedXY="charts.speedXY" :turning="charts.turning" /></div>
            <div id="toc-displacement" v-if="sectionVis.displacement" class="mt-3"><DisplacementTrajectory :displacement="charts.displacement" :displacementXY="charts.displacementXY" :cumulativeDist="charts.cumulativeDist" /></div>
          </section>

          <!-- 模块3：左右均衡与训练建议 -->
          <section>
            <h2 class="text-base font-bold text-slate-800 mb-1">左右均衡与训练建议</h2>
            <p class="text-xs text-slate-400 mb-3">对比左右侧发力、支撑分布，提供针对性训练改进方案</p>
            <div id="toc-heatmap" v-if="sectionVis.heatmap"><FootworkHeatmap :muscleLoad="charts.muscleLoad" /></div>
            <div id="toc-radar" v-if="sectionVis.radar" class="mt-3 grid grid-cols-1 lg:grid-cols-2 gap-3">
              <RadarMetrics :radarOption="charts.radar" :speedTrendOption="charts.speedTrend" />
              <FootPressure :data="charts.footPressure" />
            </div>
            <div id="toc-comparison" v-if="sectionVis.comparison" class="mt-3"><ComparisonComprehensive :symmetry="charts.symmetry" :parallelCoords="charts.parallelCoords" :downloads="downloads" /></div>
          </section>
          </template>
        </div>

      </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getAnalysisResult, getReportUi } from '../services/api.js'
import { buildPose3dReportModel } from '../services/reportAdapter.js'
import { hasChartData } from '../composables/useECharts.js'
import StatsOverview from '../components/report/StatsOverview.vue'
import FootworkHeatmap from '../components/report/FootworkHeatmap.vue'
import RadarMetrics from '../components/report/RadarMetrics.vue'
import FootPressure from '../components/report/FootPressure.vue'
import TablePlacement from '../components/report/TablePlacement.vue'
import DisplacementTrajectory from '../components/report/DisplacementTrajectory.vue'
import SpeedAcceleration from '../components/report/SpeedAcceleration.vue'
import ComparisonComprehensive from '../components/report/ComparisonComprehensive.vue'

const route = useRoute()
const loading = ref(false)
const errorText = ref('')
const model = ref(null)

const jobId = computed(() => String(route.params.jobId || '').trim())

const subjectDisplay = computed(() => {
  if (model.value?.config?.subjectName) return model.value.config.subjectName
  return model.value?.config?.subjectId || ''
})
const stepDisplay = computed(() => model.value?.config?.stepName || '')
const statusText = computed(() => {
  if (!model.value) return ''
  return model.value.status === 'done' ? '分析完成' : `状态：${model.value.status}`
})
const statsRaw = computed(() => model.value?.statsRaw || {})
const charts = computed(() => model.value?.charts || {})
const overview = computed(() => model.value?.overview || {})
const downloads = computed(() => model.value?.downloads || [])

// Section visibility: hide sections whose chart data is null or all-zero
const sectionVis = computed(() => {
  const c = charts.value
  return {
    heatmap: hasChartData(c.muscleLoad),
    radar: hasChartData(c.radar) || hasChartData(c.speedTrend) || hasChartData(c.footPressure),
    table: hasChartData(c.tableScatter) || hasChartData(c.tableHeatmap) || (c.aiInsights && c.aiInsights.length > 0),
    displacement: hasChartData(c.displacement) || hasChartData(c.displacementXY) || hasChartData(c.cumulativeDist),
    speed: hasChartData(c.speedAccelDual) || hasChartData(c.speedXY) || hasChartData(c.turning),
    comparison: hasChartData(c.symmetry) || hasChartData(c.parallelCoords),
  }
})

const allSectionsEmpty = computed(() => {
  return !Object.values(sectionVis.value).some(Boolean)
})

const contentScroll = ref(null)

async function loadReport() {
  if (!jobId.value) {
    errorText.value = '缺少分析任务 ID'
    model.value = null
    return
  }
  loading.value = true
  errorText.value = ''
  try {
    const [result, reportUi] = await Promise.all([
      getAnalysisResult(jobId.value),
      getReportUi(jobId.value).catch(() => null),
    ])
    model.value = buildPose3dReportModel({ result, reportUi, jobId: jobId.value })
  } catch (error) {
    model.value = null
    errorText.value = error?.message || '报告加载失败'
  } finally {
    loading.value = false
  }
}

watch(jobId, loadReport)
onMounted(loadReport)
</script>
