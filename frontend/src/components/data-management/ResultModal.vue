<!-- 通用结果弹窗：processing / success / error / confirm 四种状态。 -->
<template>
  <Teleport to="body">
    <div v-if="show" class="data-management-modal" @click.self="state !== 'processing' && $emit('dismiss')">
      <div class="data-management-modal__card data-management-result-card">
        <!-- 处理中 -->
        <template v-if="state === 'processing'">
          <p class="data-management-result-status">
            <span class="data-management-spinner"></span> {{ title }}
          </p>
        </template>

        <!-- 成功 -->
        <template v-else-if="state === 'success'">
          <p class="data-management-result-status is-success">&#10003; {{ title }}</p>
          <button type="button" class="data-management-result-btn" @click="$emit('dismiss')">确定</button>
        </template>

        <!-- 确认 -->
        <template v-else-if="state === 'confirm'">
          <p class="data-management-result-status is-warning">{{ title }}</p>
          <p v-if="desc" class="data-management-result-desc">{{ desc }}</p>
          <slot name="confirm-body" />
          <label v-if="confirmLabel" class="data-management-confirm-input">
            <span>请输入 <strong>{{ confirmLabel }}</strong> 以确认删除：</span>
            <input v-model="confirmInput" type="text" :placeholder="confirmLabel" @keyup.enter="$emit('confirm')" />
          </label>
          <div class="data-management-result-actions">
            <button type="button" class="secondary-button" @click="dismissAndClear">取消</button>
            <button type="button" class="danger-button" :disabled="confirmLabel && confirmInput !== confirmLabel" @click="$emit('confirm')">确认删除</button>
          </div>
        </template>

        <!-- 失败 -->
        <template v-else-if="state === 'error'">
          <p class="data-management-result-status is-error">&#10007; 操作失败</p>
          <p class="data-management-result-desc data-management-error">{{ error }}</p>
          <div class="data-management-result-actions">
            <button type="button" class="secondary-button" @click="$emit('dismiss')">关闭</button>
            <button type="button" class="data-management-result-btn" @click="$emit('retry')">返回修改</button>
          </div>
        </template>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue';

const props = defineProps({
  show: { type: Boolean, default: false },
  state: { type: String, default: 'processing' },
  title: { type: String, default: '' },
  desc: { type: String, default: '' },
  error: { type: String, default: '' },
  confirmLabel: { type: String, default: '' },
});

const emit = defineEmits(['dismiss', 'confirm', 'retry']);

const confirmInput = ref('');

// 弹窗关闭时清除输入
watch(() => props.show, (val) => { if (!val) confirmInput.value = ''; });

function dismissAndClear() {
  confirmInput.value = '';
  emit('dismiss');
}
</script>
