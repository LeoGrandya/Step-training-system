<!-- 运行时必需。分析参数配置面板：步伐名称选择。 -->
<template>
  <div class="ap-params">
    <h3 class="ap-params__title">分析参数</h3>

    <div class="ap-params__field">
      <span class="ap-params__label">训练配置</span>
      <select
        class="ap-params__select"
        :value="trainingConfigId"
        @change="$emit('update:trainingConfigId', $event.target.value)"
      >
        <option value="">不限</option>
        <option v-for="cfg in trainingConfigs" :key="cfg.id" :value="cfg.id">
          {{ cfg.name || cfg.displayName || cfg.id }}
        </option>
      </select>
    </div>

    <div class="ap-params__field">
      <span class="ap-params__label">步伐名称</span>
      <select
        class="ap-params__select"
        :value="stepDisplayName"
        @change="$emit('update:stepDisplayName', $event.target.value)"
      >
        <option value="">不限</option>
        <optgroup v-if="presetOptions.length" label="预置步伐">
          <option v-for="opt in presetOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </optgroup>
        <optgroup v-if="customOptions.length" label="自定义跑动序列">
          <option v-for="opt in customOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </optgroup>
      </select>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { listFootworkTypes, listCustomFootworks, request } from '../services/api.js'

defineProps({
  stepDisplayName: { type: String, default: '' },
  trainingConfigId: { type: String, default: '' },
  analysisProfile: { type: String, default: '快速' },
  trainingMode: { type: String, default: '练习评估' },
})
defineEmits(['update:stepDisplayName', 'update:trainingConfigId'])

const presetOptions = ref([])
const customOptions = ref([])
const trainingConfigs = ref([])

onMounted(async () => {
  try {
    const payload = await request('/api/v1/training-configs?limit=100')
    trainingConfigs.value = Array.isArray(payload.items) ? payload.items : []
  } catch { trainingConfigs.value = [] }
  try {
    const ftPayload = await listFootworkTypes()
    presetOptions.value = (ftPayload.items || []).map(f => ({ label: `预置：${f.name}`, value: `preset:${f.code}` }))
  } catch { presetOptions.value = [] }
  try {
    const cfPayload = await listCustomFootworks()
    customOptions.value = (cfPayload.items || []).map(r => ({ label: `自定义：${r.name}`, value: `custom:${r.id}` }))
  } catch { customOptions.value = [] }
})
</script>

<style scoped>
.ap-params__title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  margin: 0 0 14px;
}
.ap-params__field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.ap-params__label {
  font-size: 12px;
  font-weight: 500;
  color: #94a3b8;
}
.ap-params__select {
  padding: 8px 12px;
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 7px;
  font-size: 14px;
  font-family: inherit;
  color: #1e293b;
  background: #fff;
  outline: none;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.ap-params__select:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.08);
}
</style>
