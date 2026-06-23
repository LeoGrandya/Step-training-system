<!-- 自定义跑动序列专用表单：九宫格选点 + 路线属性。表单数据用 ref 管理。 -->
<template>
  <form class="data-management-form" @submit.prevent="handleSubmit">
    <label class="data-management-field data-management-field--wide">
      <span>名称</span>
      <input v-model="form.name" type="text" required placeholder="例如：正手两点" />
    </label>
    <label class="data-management-field">
      <span>关联步伐</span>
      <select v-model="form.footworkTypeId">
        <option value="">未选择</option>
        <option v-for="opt in footworkOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
      </select>
    </label>
    <label class="data-management-field">
      <span>起始格</span>
      <select v-model.number="form.startCell">
        <option v-for="n in 9" :key="n" :value="n">{{ n }}</option>
      </select>
    </label>
    <div class="data-management-field data-management-field--wide">
      <span>走位序列</span>
      <div class="ft-sequence-area">
        <div class="ft-grid">
          <button
            v-for="n in 9" :key="n" type="button"
            class="ft-grid-cell"
            :class="{ 'is-start': n === (form.startCell || 5), 'is-last': ftSeq.length && n === ftSeq[ftSeq.length - 1] }"
            @click="ftSeq.push(n)"
          >
            {{ n }}
            <span v-if="n === (form.startCell || 5)" class="ft-grid-tag">起点</span>
          </button>
        </div>
        <div class="ft-seq-preview">
          <template v-if="ftSeq.length">
            <span v-for="(cell, i) in ftSeq" :key="i" class="ft-seq-badge" @click="ftSeq.splice(i, 1)">{{ cell }}</span>
          </template>
          <span v-else class="ft-seq-hint">点击九宫格添加步伐点</span>
        </div>
        <button type="button" class="link-button ft-seq-clear" @click="ftSeq.splice(0)">清空序列</button>
      </div>
    </div>
    <label class="data-management-field">
      <span>默认间隔(ms)</span>
      <input v-model.number="form.defaultMs" type="number" min="100" max="5000" placeholder="750" />
    </label>
    <label class="data-management-field data-management-field--wide">
      <span>动作要求</span>
      <textarea v-model="form.actionRequirements" rows="2" placeholder="可选…"></textarea>
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
  initialData: { type: Object, default: () => ({ form: {}, ftSeq: [] }) },
  editingId: { type: String, default: '' },
  saving: { type: Boolean, default: false },
  lookups: { type: Object, default: () => ({}) },
});

const emit = defineEmits(['submit', 'cancel']);

const form = ref({ ...(props.initialData.form || {}) });
const ftSeq = ref([...(props.initialData.ftSeq || [])]);
const validationError = ref('');

const footworkOptions = computed(() => {
  return (props.lookups['footwork-types'] || []).map((item) => ({
    value: item.id || item.jobId,
    label: item.name || item.displayName || item.code || item.id,
  }));
});

watch(() => props.initialData, (data) => {
  form.value = { ...(data.form || {}) };
  ftSeq.value = [...(data.ftSeq || [])];
  validationError.value = '';
}, { deep: true });

function handleSubmit() {
  validationError.value = '';
  if (!(form.value.name || '').trim()) {
    validationError.value = '名称为必填项';
    return;
  }
  emit('submit', { formData: { ...form.value }, ftSeqArr: [...ftSeq.value] });
}
</script>
