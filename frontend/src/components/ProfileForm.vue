<!-- 运行时必需。用户档案表单（持拍手、等级等）。 -->
<template>
  <form class="panel form-grid profile-form" @submit.prevent="emitSave">
    <h2>基础训练资料</h2>
    <label>姓名<input v-model.trim="draft.name" required /></label>
    <label>年龄<input v-model.number="draft.age" type="number" min="0" max="90" /></label>
    <label>身高(cm)<input v-model.number="draft.heightCm" type="number" min="90" max="250" /></label>
    <label>体重(kg)<input v-model.number="draft.weightKg" type="number" min="30" max="200" step="0.1" /></label>
    <label>持拍手
      <select v-model="draft.hand">
        <option value="right">右手持拍</option>
        <option value="left">左手持拍</option>
      </select>
    </label>
    <label>运动年限<input v-model.number="draft.years" type="number" min="0" max="90" /></label>
    <label>运动等级
      <select v-model="draft.level">
        <option value="amateur">业余</option>
        <option value="level-2">二级</option>
        <option value="level-1">一级</option>
      </select>
    </label>
    <button type="submit">保存资料</button>
  </form>
</template>

<script setup>
import { reactive, watch } from 'vue';

const props = defineProps({ profile: { type: Object, required: true } });
const emit = defineEmits(['save']);
const draft = reactive({ ...props.profile });

watch(
  () => props.profile,
  (next) => Object.assign(draft, next),
  { deep: true },
);

function emitSave() {
  emit('save', { ...draft });
}
</script>
