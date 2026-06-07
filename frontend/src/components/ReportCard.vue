<!-- 运行时必需。报告卡片：指标预览 + 多选/删除/详情。 -->
<template>
  <div class="report-card" :class="{ 'report-card--selected': selected }">
    <div class="report-card__top">
      <label class="report-card__check">
        <input type="checkbox" :checked="selected" @change="$emit('toggle-select', report.id)" />
        <span class="report-card__check-mark"></span>
      </label>
      <span class="report-card__date">{{ report.date }}</span>
      <span class="report-card__mode" :data-mode="report.mode">{{ modeLabel }}</span>
      <button type="button" class="report-card__delete" @click.stop="$emit('delete', report.id)" aria-label="删除">&times;</button>
    </div>

    <h3 class="report-card__step">{{ report.stepName }}</h3>

    <div class="report-card__metrics">
      <div class="report-card__metric">
        <span class="report-card__metric-label">循环数</span>
        <span class="report-card__metric-val">{{ report.summary.loops }}</span>
      </div>
      <div class="report-card__metric">
        <span class="report-card__metric-label">均速</span>
        <span class="report-card__metric-val">{{ report.summary.avgSpeed.toFixed(2) }}<small>m/s</small></span>
      </div>
      <div class="report-card__metric">
        <span class="report-card__metric-label">对称性</span>
        <span class="report-card__metric-val">{{ report.summary.symmetry }}<small>%</small></span>
      </div>
      <div class="report-card__metric">
        <span class="report-card__metric-label">总时长</span>
        <span class="report-card__metric-val">{{ report.summary.totalTime.toFixed(1) }}<small>s</small></span>
      </div>
      <div class="report-card__metric">
        <span class="report-card__metric-label">峰值加速度</span>
        <span class="report-card__metric-val">{{ report.summary.peakAccel.toFixed(2) }}<small>m/s&sup2;</small></span>
      </div>
    </div>

    <div class="report-card__footer">
      <a :href="'/#/report/' + encodeURIComponent(report.jobId)" class="report-card__detail-link">查看详情 &rarr;</a>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  report: { type: Object, required: true },
  selected: { type: Boolean, default: false },
})

defineEmits(['toggle-select', 'delete'])

const modeMap = { eval: '练习评估', practice: '自由练习', test: '能力测试' }
const modeLabel = computed(() => modeMap[props.report.mode] || props.report.mode)
</script>
