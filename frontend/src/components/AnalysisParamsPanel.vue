<!-- 运行时必需。分析参数配置面板：步伐名称选择。 -->
<template>
  <div class="analysis-params">
    <h3 class="analysis-params__title">分析参数</h3>

    <div class="analysis-params__group">
      <span class="analysis-params__label">步伐名称</span>
      <select
        class="analysis-params__select"
        :value="stepDisplayName"
        @change="$emit('update:stepDisplayName', $event.target.value)"
      >
        <option value="">不限</option>
        <optgroup v-if="presetOptions.length" label="预置步伐">
          <option v-for="opt in presetOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </optgroup>
        <optgroup v-if="customOptions.length" label="自定义跑动序列">
          <option v-for="opt in customOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </optgroup>
      </select>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { listFootworkTypes, listCustomFootworks } from '../services/api.js'

defineProps({
  stepDisplayName: { type: String, default: '' },
})

defineEmits(['update:stepDisplayName'])

const presetOptions = ref([])
const customOptions = ref([])

onMounted(async () => {
  try {
    const ftPayload = await listFootworkTypes()
    presetOptions.value = (ftPayload.items || []).map(f => ({
      label: `预置：${f.name}`,
      value: `preset:${f.code}`,
    }))
  } catch { presetOptions.value = [] }

  try {
    const cfPayload = await listCustomFootworks()
    customOptions.value = (cfPayload.items || []).map(r => ({
      label: `自定义：${r.name}`,
      value: `custom:${r.id}`,
    }))
  } catch { customOptions.value = [] }
})
</script>
