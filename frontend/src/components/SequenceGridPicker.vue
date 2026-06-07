<!-- 运行时必需。九宫格序列点选弹窗：可视化选择落点序列。 -->
<template>
  <div v-if="open" class="seq-picker-overlay" @click.self="$emit('close')">
    <div class="seq-picker-dialog">
      <div class="seq-picker-dialog__header">
        <h2>落点序列</h2>
        <button type="button" class="seq-picker-dialog__close" @click="$emit('close')">&times;</button>
      </div>

      <div class="seq-picker-dialog__body">
        <div class="seq-picker__grid">
          <button
            v-for="cell in 9"
            :key="cell"
            type="button"
            class="seq-picker__cell"
            :class="{
              'seq-picker__cell--start': cell === startCellNum,
              'seq-picker__cell--last': sequence.length && sequence[sequence.length - 1] === cell,
            }"
            @click="addCell(cell)"
          >
            <span class="seq-picker__cell-num">{{ cell }}</span>
            <span v-if="cell === startCellNum" class="seq-picker__cell-tag">起点</span>
          </button>
        </div>

        <div class="seq-picker__preview">
          <span class="seq-picker__preview-label">当前序列</span>
          <div class="seq-picker__sequence">
            <span v-if="!sequence.length" class="seq-picker__empty">点击上方九宫格添加落点</span>
            <span
              v-for="(cell, idx) in sequence"
              :key="idx"
              class="seq-picker__badge"
              @click="removeCell(idx)"
              :title="'点击移除 ' + cell"
            >
              {{ cell }}
              <span class="seq-picker__badge-arrow" v-if="idx < sequence.length - 1">&rarr;</span>
            </span>
          </div>
        </div>
      </div>

      <div class="seq-picker-dialog__footer">
        <div class="seq-picker-dialog__footer-left">
          <button type="button" class="secondary-button" @click="undoLast" :disabled="!sequence.length">撤销</button>
          <button type="button" class="secondary-button" @click="clearAll" :disabled="!sequence.length">清空</button>
        </div>
        <button type="button" class="seq-picker-dialog__confirm" @click="confirm" :disabled="!sequence.length">
          确认 ({{ sequence.length }} 步)
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  modelValue: { type: String, default: '' },
  startCell: { type: Number, default: 5 },
})

const emit = defineEmits(['update:modelValue', 'close'])

const sequence = ref([])
const startCellNum = ref(props.startCell)

watch(() => props.open, (isOpen) => {
  if (isOpen) {
    startCellNum.value = props.startCell
    sequence.value = parseSequence(props.modelValue)
  }
})

function parseSequence(raw) {
  return String(raw || '')
    .split(',')
    .map(p => p.trim())
    .filter(p => /^[1-9]$/.test(p))
    .map(Number)
}

function addCell(cell) {
  sequence.value = [...sequence.value, cell]
}

function removeCell(idx) {
  sequence.value = sequence.value.filter((_, i) => i !== idx)
}

function undoLast() {
  sequence.value = sequence.value.slice(0, -1)
}

function clearAll() {
  sequence.value = []
}

function confirm() {
  emit('update:modelValue', sequence.value.join(','))
  emit('close')
}
</script>
