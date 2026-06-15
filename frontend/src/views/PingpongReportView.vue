<template>
  <div class="min-h-screen bg-sky-50 text-slate-900 flex flex-col font-sans selection:bg-sky-500/30 selection:text-white">
    <!-- 顶栏 -->
    <header class="bg-white/90 backdrop-blur border-b border-slate-200 px-5 py-3 flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-3">
        <h1 class="text-sm font-bold text-slate-800 tracking-wide">朱雪毅 · 并步步伐分析报告</h1>
        <span class="text-xs bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-500/20 font-tech flex items-center gap-1">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
          分析完成
        </span>
      </div>
      <div class="text-xs text-slate-400 font-tech">并步 2-1 · 14周期 · 42步 · 29.66s</div>
    </header>

    <!-- 内容区 -->
    <div class="p-3 space-y-3 overflow-y-auto flex-1 max-w-[1440px] mx-auto w-full">
      <!-- 1. 核心指标 -->
      <StatsOverview />

      <!-- 2. 下肢热力图 -->
      <FootworkHeatmap />

      <!-- 3. 雷达图 + 足底压力（并排） -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <RadarMetrics />
        <FootPressure />
      </div>

      <!-- 4. 球桌落点 + AI建议 -->
      <TablePlacement />

      <!-- 5. 步伐周期 -->
      <PeriodTiming />

      <!-- 6. 位移轨迹 -->
      <DisplacementTrajectory />

      <!-- 7. 速度与加速度 -->
      <SpeedAcceleration />

      <!-- 8. 腾空参数 -->
      <FlightParameters />

      <!-- 9. 关节运动学 -->
      <JointBiomechanics />

      <!-- 10. 效率评估 -->
      <EfficiencyEvaluation />

      <!-- 11. 综合对比 -->
      <ComparisonComprehensive />
    </div>
  </div>
</template>

<script setup>
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
</script>
