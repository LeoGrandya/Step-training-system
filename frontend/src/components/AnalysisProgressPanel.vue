<!-- 运行时必需。分析进度面板：Linear 风格进度条。 -->
<template>
  <div class="ap-progress analysis-progress" v-if="phase !== 'idle'">
    <div class="ap-progress__head">
      <span class="ap-progress__dot" :data-phase="phase" />
      <span class="ap-progress__file">{{ fileLabel }}</span>
    </div>
    <div class="ap-progress__track">
      <div class="ap-progress__bar" :style="{ width: progress + '%' }" />
    </div>
    <div class="ap-progress__meta">
      <span class="ap-progress__status">{{ statusText }}</span>
      <span class="ap-progress__pct">{{ progress }}%</span>
    </div>
    <div class="ap-progress__actions" v-if="phase === 'running'">
      <button type="button" class="ap-progress__cancel" @click="$emit('cancel')">取消分析</button>
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

<style scoped>
.ap-progress {
  background: #fff;
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 10px;
  padding: 18px 20px;
}
.ap-progress__head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.ap-progress__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  background: #94a3b8;
}
.ap-progress__dot[data-phase="running"] { background: #2563eb; animation: ap-pulse 1.4s ease infinite; }
.ap-progress__dot[data-phase="done"] { background: #16a34a; }
.ap-progress__dot[data-phase="error"] { background: #dc2626; }
@keyframes ap-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.ap-progress__file {
  font-size: 13px;
  font-weight: 500;
  color: #475569;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ap-progress__track {
  height: 6px;
  background: #f1f5f9;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 10px;
}
.ap-progress__bar {
  height: 100%;
  background: #2563eb;
  border-radius: 3px;
  transition: width 0.4s cubic-bezier(0.22, 1, 0.36, 1);
}

.ap-progress__meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.ap-progress__status {
  font-size: 12px;
  color: #64748b;
}
.ap-progress__pct {
  font-size: 12px;
  font-weight: 600;
  color: #1e293b;
}

.ap-progress__actions { margin-top: 10px; }
.ap-progress__cancel {
  border: 1px solid rgba(0,0,0,0.08);
  background: #fff;
  color: #dc2626;
  padding: 6px 16px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.12s;
}
.ap-progress__cancel:hover { background: #fef2f2; }
</style>
