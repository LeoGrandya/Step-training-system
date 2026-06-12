<template>
  <div class="min-h-screen bg-sky-50 text-slate-900 flex font-sans selection:bg-sky-500/30 selection:text-white">
    <!-- 侧边栏 -->
    <aside class="w-64 bg-white border-r border-slate-200 hidden lg:flex flex-col justify-between p-3">
      <div>
        <div class="flex items-center gap-2.5 px-2 py-3 mb-5 border-b border-slate-200">
          <div class="w-8 h-8 bg-gradient-to-br from-sky-500 to-sky-600 rounded-lg flex items-center justify-center shadow-[0_0_12px_rgba(56,189,248,0.3)]">
            <span class="text-white font-bold text-sm font-tech">P</span>
          </div>
          <div>
            <span class="font-bold tracking-wide text-sm text-slate-800">慧步乒乓</span>
            <p class="text-[11px] text-slate-400 font-tech">Pose3D 分析报告</p>
          </div>
        </div>

        <nav class="space-y-0.5">
          <a href="#" class="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-sky-500/10 text-sky-400 font-medium text-sm border border-sky-500/10">
            <span class="w-4 h-4 flex items-center justify-center">
              <svg viewBox="0 0 16 16" class="w-3.5 h-3.5 fill-current"><circle cx="8" cy="8" r="6" /><circle cx="8" cy="8" r="2.5" fill="#0f172a"/></svg>
            </span>
            <span>步伐训练分析</span>
          </a>
        </nav>
      </div>

      <div class="text-xs text-slate-400 px-2 text-center">
        <p>{{ subjectDisplay || '暂无受试者' }}</p>
        <p v-if="stepDisplay" class="font-tech text-[10px] mt-0.5">{{ stepDisplay }}</p>
      </div>
    </aside>

    <!-- 主区域 -->
    <main class="flex-1 flex flex-col min-w-0">
      <header class="bg-white/90 backdrop-blur border-b border-slate-200 px-5 py-3 flex flex-wrap items-center justify-between gap-3">
        <div class="flex items-center gap-3">
          <h1 class="text-sm font-bold text-slate-800 tracking-wide">B端乒乓球步伐训练分析中心</h1>
          <span v-if="statusText" class="text-xs bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-500/20 font-tech flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            {{ statusText }}
          </span>
        </div>
      </header>

      <div v-if="loading" class="flex-1 flex items-center justify-center text-slate-400">报告加载中...</div>
      <div v-else-if="errorText" class="flex-1 flex items-center justify-center text-rose-400">{{ errorText }}</div>

      <!-- 内容区 -->
      <div v-else class="p-3 space-y-3 overflow-y-auto flex-1 max-w-[1440px] mx-auto w-full">
        <StatsOverview :statsRaw="statsRaw" :dirPie="charts.dirPie" />

        <FootworkHeatmap />

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <RadarMetrics :radarOption="charts.radar" :speedTrendOption="charts.speedTrend" />
          <FootPressure :data="charts.footPressure" />
        </div>

        <TablePlacement :tableScatter="charts.tableScatter" :tableHeatmap="charts.tableHeatmap" :aiInsights="charts.aiInsights" />

        <PeriodTiming :gantt="charts.gantt" :phasePlane="charts.phasePlane" :speedOption="charts.speed" />

        <DisplacementTrajectory :displacement="charts.displacement" :displacementXY="charts.displacementXY" :cumulativeDist="charts.cumulativeDist" />

        <SpeedAcceleration :speedAccelDual="charts.speedAccelDual" :speedXY="charts.speedXY" :turning="charts.turning" />

        <FlightParameters :airborne="charts.airborne" :footHeight="charts.footHeight" />

        <JointBiomechanics :joint="charts.joint" :jointAngVel="charts.jointAngVel" :jointRomRadar="charts.jointRomRadar"
          :torqueChart="charts.torqueChart" :powerChart="charts.powerChart" :hipAngleChart="charts.hipAngleChart" />

        <EfficiencyEvaluation :assessments="overview.assessments" :efficiency="charts.efficiency" :dtwHeatmap="charts.dtwHeatmap"
          :efficiencyBars="charts.efficiencyBars" :stepEfficiencyBars="charts.stepEfficiencyBars" :energyBars="charts.energyBars" />

        <ComparisonComprehensive :downloads="downloads" :symmetry="charts.symmetry" :parallelCoords="charts.parallelCoords" />
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getAnalysisResult, getReportUi } from '../services/api.js'
import { buildPose3dReportModel } from '../services/reportAdapter.js'
import StatsOverview from '../components/report/StatsOverview.vue'
import FootworkHeatmap from '../components/report/FootworkHeatmap.vue'
import RadarMetrics from '../components/report/RadarMetrics.vue'
import FootPressure from '../components/report/FootPressure.vue'
import TablePlacement from '../components/report/TablePlacement.vue'
import PeriodTiming from '../components/report/PeriodTiming.vue'
import DisplacementTrajectory from '../components/report/DisplacementTrajectory.vue'
import SpeedAcceleration from '../components/report/SpeedAcceleration.vue'
import FlightParameters from '../components/report/FlightParameters.vue'
import JointBiomechanics from '../components/report/JointBiomechanics.vue'
import EfficiencyEvaluation from '../components/report/EfficiencyEvaluation.vue'
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
