<!-- 运行时必需。拖拽上传区：Linear 风格干净卡面。 -->
<template>
  <div
    class="upload-zone"
    :class="{
      'upload-zone--dragover': dragOver,
      'upload-zone--has-file': file,
      'upload-zone--invalid': invalid,
    }"
    @dragover.prevent="onDragOver"
    @dragleave.prevent="onDragLeave"
    @drop.prevent="onDrop"
    @click="clickInput"
  >
    <input
      v-if="!file"
      ref="fileInput"
      type="file"
      :accept="accept"
      class="upload-zone__input"
      @change="onFileChange"
    />

    <!-- 空状态 -->
    <div v-if="!file" class="upload-zone__empty">
      <span class="upload-zone__cam-icon">{{ camera === 'left' ? '●' : '●' }}</span>
      <span class="upload-zone__camera-label">{{ camera === 'left' ? '左机位' : '右机位' }}</span>
      <span class="upload-zone__hint">拖放视频文件或点击选择</span>
    </div>

    <!-- 已选文件 -->
    <div v-else class="upload-zone__file-card">
      <svg class="upload-zone__file-check" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
      <div class="upload-zone__file-info">
        <span class="upload-zone__file-name">{{ file.name }}</span>
        <span class="upload-zone__file-meta">
          {{ formatSize(file.size) }}
          <template v-if="duration > 0"> &middot; {{ formatDuration(duration) }}</template>
        </span>
      </div>
      <button type="button" class="upload-zone__clear" @click.stop="clearFile" aria-label="清除">&times;</button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  camera: { type: String, required: true, validator: v => ['left', 'right'].includes(v) },
  accept: { type: String, default: 'video/*' },
  modelValue: { type: File, default: null },
})

const emit = defineEmits(['update:modelValue', 'update:duration'])

const fileInput = ref(null)
const dragOver = ref(false)
const invalid = ref(false)
const file = ref(props.modelValue)
const duration = ref(0)

watch(() => props.modelValue, (val) => {
  file.value = val
  if (val) probeDuration(val)
  else duration.value = 0
})

function probeDuration(videoFile) {
  const url = URL.createObjectURL(videoFile)
  const video = document.createElement('video')
  video.preload = 'metadata'
  video.onloadedmetadata = () => {
    duration.value = video.duration || 0
    emit('update:duration', video.duration || 0)
    URL.revokeObjectURL(url)
  }
  video.onerror = () => {
    duration.value = 0
    emit('update:duration', 0)
    URL.revokeObjectURL(url)
  }
  video.src = url
}

function clickInput() {
  if (!file.value && fileInput.value) fileInput.value.click()
}

function onDragOver(e) {
  dragOver.value = true
  invalid.value = false
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'
}

function onDragLeave() {
  dragOver.value = false
  invalid.value = false
}

function onDrop(e) {
  dragOver.value = false
  invalid.value = false
  const files = e.dataTransfer?.files
  if (!files || !files.length) return
  const videoFile = files[0]
  if (!videoFile.type.startsWith('video/')) {
    invalid.value = true
    return
  }
  setFile(videoFile)
}

function onFileChange(e) {
  const selected = e.target.files?.[0]
  if (!selected) return
  setFile(selected)
}

function setFile(f) {
  file.value = f
  invalid.value = false
  emit('update:modelValue', f)
  probeDuration(f)
}

function clearFile() {
  file.value = null
  invalid.value = false
  duration.value = 0
  emit('update:modelValue', null)
  emit('update:duration', 0)
}

function formatSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDuration(sec) {
  if (!sec || sec < 0) return ''
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return m + ':' + String(s).padStart(2, '0')
}
</script>

<style scoped>
.upload-zone {
  position: relative;
  background: #fff;
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 10px;
  min-height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
}
.upload-zone:hover {
  border-color: rgba(0,0,0,0.14);
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.upload-zone--dragover {
  border-color: #2563eb;
  background: #f0f5ff;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.08);
}
.upload-zone--has-file {
  border-color: rgba(0,0,0,0.06);
  cursor: default;
}
.upload-zone--invalid {
  border-color: #dc2626;
  background: #fef2f2;
}

.upload-zone__input { position: absolute; opacity: 0; pointer-events: none; }

.upload-zone__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 28px 20px;
}
.upload-zone__cam-icon {
  font-size: 22px;
  color: #2563eb;
  opacity: 0.6;
  margin-bottom: 2px;
}
.upload-zone__camera-label {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  letter-spacing: 0.02em;
}
.upload-zone__hint {
  font-size: 12px;
  color: #94a3b8;
}

.upload-zone__file-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 18px;
  width: 100%;
}
.upload-zone__file-check { flex-shrink: 0; }
.upload-zone__file-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.upload-zone__file-name {
  font-size: 14px;
  font-weight: 500;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.upload-zone__file-meta {
  font-size: 12px;
  color: #94a3b8;
}

.upload-zone__clear {
  flex-shrink: 0;
  border: none;
  background: transparent;
  font-size: 20px;
  color: #94a3b8;
  cursor: pointer;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: color 0.12s, background 0.12s;
}
.upload-zone__clear:hover { color: #dc2626; background: #fef2f2; }
</style>
