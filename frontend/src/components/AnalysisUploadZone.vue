<!-- 运行时必需。拖拽上传区：支持拖放/点击选择视频文件。 -->
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
  >
    <input
      v-if="!file"
      ref="fileInput"
      type="file"
      :accept="accept"
      class="upload-zone__input"
      @change="onFileChange"
    />

    <div v-if="!file" class="upload-zone__empty">
      <span class="upload-zone__crosshair">⌖</span>
      <span class="upload-zone__camera-label">{{ camera === 'left' ? '左机位' : '右机位' }}</span>
      <span class="upload-zone__hint">拖放视频文件或点击选择</span>
      <span class="upload-zone__spec">{{ accept }}</span>
    </div>

    <div v-else class="upload-zone__file-card">
      <span class="upload-zone__file-icon">&#9654;</span>
      <div class="upload-zone__file-info">
        <span class="upload-zone__file-name">{{ file.name }}</span>
        <span class="upload-zone__file-meta">
          {{ formatSize(file.size) }}
          <template v-if="duration > 0"> &middot; {{ formatDuration(duration) }}</template>
        </span>
      </div>
      <button
        type="button"
        class="upload-zone__clear"
        @click.stop="clearFile"
        aria-label="清除文件"
      >&times;</button>
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
