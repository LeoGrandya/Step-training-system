<!-- 基础步伐专用表单：九宫格选点 + 步伐属性。表单数据用 ref 管理。 -->
<template>
  <form class="data-management-form" @submit.prevent="handleSubmit">
    <label class="data-management-field data-management-field--wide">
      <span>名称</span>
      <input v-model="form.name" type="text" required placeholder="例如：正手跨步" :disabled="viewMode" />
    </label>
    <label class="data-management-field">
      <span>分类</span>
      <select v-model="form.category" required :disabled="viewMode">
        <option value="">未选择</option>
        <option value="单一步伐">单一步伐</option>
        <option value="组合步伐">组合步伐</option>
      </select>
    </label>
    <label class="data-management-field">
      <span>起始格</span>
      <select v-model.number="form.defaultStartCell" :disabled="viewMode">
        <option v-for="n in 9" :key="n" :value="n">{{ n }}</option>
      </select>
    </label>
    <div class="data-management-field data-management-field--wide">
      <span>默认序列</span>
      <div class="ft-sequence-area">
        <div class="ft-grid">
          <button
            v-for="n in 9" :key="n" type="button"
            class="ft-grid-cell"
            :class="{ 'is-start': n === form.defaultStartCell, 'is-last': ftSeq.length && n === ftSeq[ftSeq.length - 1] }"
            :disabled="viewMode"
            @click="!viewMode && ftSeq.push(n)"
          >
            {{ n }}
            <span v-if="n === form.defaultStartCell" class="ft-grid-tag">起点</span>
          </button>
        </div>
        <div class="ft-seq-preview">
          <template v-if="ftSeq.length">
            <span v-for="(cell, i) in ftSeq" :key="i" class="ft-seq-badge" @click="!viewMode && ftSeq.splice(i, 1)">{{ cell }}</span>
          </template>
          <span v-else class="ft-seq-hint">{{ viewMode ? '无序列' : '点击九宫格添加步伐点' }}</span>
        </div>
        <button v-if="!viewMode" type="button" class="link-button ft-seq-clear" @click="ftSeq.splice(0)">清空序列</button>
      </div>
    </div>
    <label class="data-management-field data-management-field--wide">
      <span>说明</span>
      <textarea v-model="form.description" rows="2" placeholder="可选…" :disabled="viewMode"></textarea>
    </label>
    <p v-if="validationError" class="data-management-error">{{ validationError }}</p>
    <div class="data-management-form__actions">
      <button v-if="!viewMode" type="submit" :disabled="saving">
        <span v-if="saving" class="data-management-saving-indicator"></span>
        {{ saving ? '保存中…' : (editingId ? '保存修改' : '新增记录') }}
      </button>
      <button type="button" class="secondary-button" @click="$emit('cancel')">{{ viewMode ? '关闭' : '取消' }}</button>
    </div>
  </form>
</template>

<script setup>
import { ref, watch } from 'vue';

const props = defineProps({
  initialData: { type: Object, default: () => ({ form: {}, ftSeq: [] }) },
  editingId: { type: String, default: '' },
  saving: { type: Boolean, default: false },
  viewMode: { type: Boolean, default: false },
});

const emit = defineEmits(['submit', 'cancel']);

// 核心修复：用 ref 管理，整体替换
const form = ref({ ...(props.initialData.form || {}) });
const ftSeq = ref([...(props.initialData.ftSeq || [])]);
const validationError = ref('');

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
  if (!form.value.category) {
    validationError.value = '分类为必填项';
    return;
  }
  emit('submit', { formData: { ...form.value }, ftSeqArr: [...ftSeq.value] });
}
</script>
