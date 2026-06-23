<!-- 通用资源表单：基于 resource.fields 声明式渲染。表单数据用 ref 管理，reset 时整体替换。 -->
<template>
  <form class="data-management-form" @submit.prevent="$emit('submit', formData)">
    <label v-for="field in resource.fields" :key="field.key" class="data-management-field">
      <span>{{ field.label }}</span>
      <select v-if="field.type === 'select'" v-model="formData[field.key]" :required="field.required">
        <option value="">未选择</option>
        <option v-for="option in fieldOptions(field)" :key="option.value" :value="option.value">
          {{ option.label }}
        </option>
      </select>
      <textarea
        v-else-if="field.type === 'textarea' || field.type === 'json'"
        v-model="formData[field.key]"
        :placeholder="field.placeholder || ''"
        rows="3"
      />
      <input
        v-else
        v-model="formData[field.key]"
        :type="field.type"
        :min="field.min"
        :max="field.max"
        :required="field.required"
        :placeholder="field.placeholder || ''"
      />
    </label>
    <p v-if="validationError" class="data-management-error">{{ validationError }}</p>
    <div class="data-management-form__actions">
      <button type="submit" :disabled="saving">
        <span v-if="saving" class="data-management-saving-indicator"></span>
        {{ saving ? '保存中…' : (editingId ? '保存修改' : '新增记录') }}
      </button>
      <button type="button" class="secondary-button" @click="$emit('cancel')">取消</button>
    </div>
  </form>
</template>

<script setup>
import { computed, ref, watch } from 'vue';

const props = defineProps({
  resource: { type: Object, required: true },
  initialData: { type: Object, default: () => ({}) },
  editingId: { type: String, default: '' },
  saving: { type: Boolean, default: false },
  lookups: { type: Object, default: () => ({}) },
});

const emit = defineEmits(['submit', 'cancel']);

// 核心修复：用 ref 管理表单数据，整体替换而非 delete
const formData = ref({ ...props.initialData });
const validationError = ref('');

// 当 initialData 变化时（如切换编辑项），整体替换
watch(() => props.initialData, (data) => {
  formData.value = { ...data };
  validationError.value = '';
}, { deep: true });

function fieldOptions(field) {
  if (field.options) return field.options;
  if (!field.lookup) return [];
  return (props.lookups[field.lookup] || []).map((item) => ({
    value: item.id || item.jobId,
    label: item.name || item.displayName || item.username || item.code || item.id || item.jobId,
  }));
}

// 前端校验
function validate() {
  validationError.value = '';
  for (const field of props.resource.fields) {
    const value = formData.value[field.key];
    if (field.required && (value === '' || value === null || value === undefined)) {
      validationError.value = `${field.label} 为必填项`;
      return false;
    }
    if (field.type === 'number' && value !== '' && value !== null && value !== undefined) {
      if (isNaN(Number(value))) {
        validationError.value = `${field.label} 必须为数字`;
        return false;
      }
    }
    if (field.type === 'json' && value && typeof value === 'string' && value.trim()) {
      try { JSON.parse(value); } catch {
        validationError.value = `${field.label} 不是合法 JSON`;
        return false;
      }
    }
  }
  return true;
}

// 暴露 validate 供父组件调用
defineExpose({ validate, formData });
</script>
