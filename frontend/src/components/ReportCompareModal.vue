<!-- 运行时必需。对比弹窗：Canvas 雷达图 + 图例。 -->
<template>
  <div v-if="open" class="report-compare-overlay" @click.self="$emit('close')">
    <div class="report-compare-dialog">
      <div class="report-compare-dialog__header">
        <h2>报告对比</h2>
        <button type="button" class="report-compare-dialog__close" @click="$emit('close')">&times;</button>
      </div>

      <div class="report-compare-dialog__body">
        <div v-if="loading" class="report-compare__state">加载中...</div>
        <div v-else-if="!data.length" class="report-compare__state">无对比数据</div>
        <template v-else>
          <div class="report-compare__chart">
            <canvas ref="radarCanvas"></canvas>
          </div>
          <div class="report-compare__table">
            <table>
              <thead>
                <tr>
                  <th>指标</th>
                  <th v-for="(r, i) in data" :key="i">
                    <span class="report-compare__dot" :style="{ background: palette[i % palette.length].stroke }"></span>
                    {{ r.stepName || '报告' }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="metric in metrics" :key="metric.key">
                  <td>{{ metric.label }}</td>
                  <td v-for="(r, i) in data" :key="i" class="report-compare__td-val">{{ formatVal(r.summary || {}, metric.key) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { useRadarChart } from '../composables/useRadarChart.js'

const props = defineProps({
  open: { type: Boolean, default: false },
  data: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

defineEmits(['close'])

const radarCanvas = ref(null)
const { draw } = useRadarChart(radarCanvas)

const palette = [
  { stroke: '#2563eb', fill: 'rgba(37,99,235,0.10)' },
  { stroke: '#f59e0b', fill: 'rgba(245,158,11,0.10)' },
  { stroke: '#10b981', fill: 'rgba(16,185,129,0.10)' },
  { stroke: '#8b5cf6', fill: 'rgba(139,92,246,0.10)' },
  { stroke: '#ef4444', fill: 'rgba(239,68,68,0.10)' },
  { stroke: '#ec4899', fill: 'rgba(236,72,153,0.10)' },
]

const metrics = [
  { key: 'avgSpeed', label: '平均速度 (m/s)' },
  { key: 'symmetry', label: '对称性 (%)' },
  { key: 'loops', label: '循环数' },
  { key: 'peakAccel', label: '峰值加速度 (m/s²)' },
  { key: 'totalTime', label: '总时长 (s)' },
]

watch(() => [props.open, props.data], async () => {
  if (props.open && props.data.length) {
    await nextTick()
    draw(props.data)
  }
})

function formatVal(summary, key) {
  const v = Number(summary[key])
  if (!Number.isFinite(v)) return '-'
  if (key === 'avgSpeed' || key === 'peakAccel') return v.toFixed(2)
  if (key === 'totalTime') return v.toFixed(1)
  return String(v)
}
</script>
