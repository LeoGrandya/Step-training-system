<!-- 运行时必需。分析进度面板：仪表风格进度条 + 阶段描述。 -->
<template>
  <div class="analysis-progress" v-if="phase !== 'idle'">
    <div class="analysis-progress__header">
      <span class="analysis-progress__led" :data-phase="phase"></span>
      <span class="analysis-progress__filename">{{ fileLabel }}</span>
    </div>

    <div class="analysis-progress__track">
      <div class="analysis-progress__bar" :style="{ width: progress + '%' }"></div>
      <div class="analysis-progress__ticks">
        <span v-for="tick in 10" :key="tick" class="analysis-progress__tick" :style="{ left: (tick * 10) + '%' }"></span>
      </div>
    </div>

    <div class="analysis-progress__info">
      <span class="analysis-progress__status">{{ statusText }}</span>
      <div class="analysis-progress__right">
        <span class="analysis-progress__eta">{{ etaText }}</span>
        <span class="analysis-progress__pct">{{ progress }}%</span>
      </div>
    </div>

    <div class="analysis-progress__actions" v-if="phase === 'running'">
      <button type="button" class="analysis-progress__cancel" @click="$emit('cancel')">取消分析</button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  phase: { type: String, default: 'idle' },
  progress: { type: Number, default: 0 },
  statusText: { type: String, default: '' },
  etaText: { type: String, default: '' },
  fileLabel: { type: String, default: '' },
})

defineEmits(['cancel'])
</script>
