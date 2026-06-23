<!-- 新教练首次登录：创建第一个受试者。 -->
<template>
  <section class="csub-page">
    <div class="csub-card">
      <h1 class="csub-title">创建受试者</h1>
      <p class="csub-desc">你需要先创建至少一个受试者，才能进入训练系统。</p>

      <form class="csub-form" @submit.prevent="submit">
        <label class="csub-field">
          <span>姓名 <em>*</em></span>
          <input v-model.trim="form.name" type="text" placeholder="受试者姓名" required autofocus />
        </label>

        <details class="csub-extra" :open="extraOpen">
          <summary @click.prevent="extraOpen = !extraOpen">选填信息（可后续完善）</summary>
          <div class="csub-extra__grid">
            <label class="csub-field"><span>年龄</span><input v-model.number="form.age" type="number" min="1" max="120" /></label>
            <label class="csub-field"><span>身高 (cm)</span><input v-model.number="form.heightCm" type="number" min="50" max="300" /></label>
            <label class="csub-field"><span>体重 (kg)</span><input v-model.number="form.weightKg" type="number" min="10" max="300" step="0.1" /></label>
            <label class="csub-field"><span>训练年限</span><input v-model.number="form.years" type="number" min="0" max="80" /></label>
            <label class="csub-field">
              <span>持拍手</span>
              <select v-model="form.hand"><option value="right">右手</option><option value="left">左手</option></select>
            </label>
            <label class="csub-field">
              <span>水平</span>
              <select v-model="form.level"><option value="amateur">业余</option><option value="level-2">二级</option><option value="level-1">一级</option></select>
            </label>
          </div>
        </details>

        <button type="submit" :disabled="submitting" class="csub-btn">{{ submitting ? '创建中...' : '创建并进入系统' }}</button>
        <p v-if="message" class="csub-msg" :class="{ 'csub-msg--err': isError }">{{ message }}</p>
      </form>
    </div>
  </section>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { request } from '../services/api.js';
import { setCurrentSubjectId, STORAGE_KEYS } from '../stores/storage.js';
import { notifySubjectChanged } from '../stores/subjectEvents.js';

const router = useRouter();
const form = reactive({ name: '', age: null, heightCm: null, weightKg: null, hand: '右手', years: 0, level: '业余' });
const submitting = ref(false);
const message = ref('');
const isError = ref(false);
const extraOpen = ref(false);

function isValidName(name) {
  return /^[一-鿿㐀-䶿a-zA-Z\s]+$/.test(name);
}

async function submit() {
  const name = form.name.trim();
  if (!name) { message.value = '请输入姓名'; isError.value = true; return; }
  if (!isValidName(name)) { message.value = '姓名只允许中文或英文字母，禁止数字和符号'; isError.value = true; return; }

  submitting.value = true;
  message.value = '';
  isError.value = false;

  try {
    const payload = { name: name };
    if (form.age) payload.age = form.age;
    if (form.heightCm) payload.heightCm = form.heightCm;
    if (form.weightKg) payload.weightKg = form.weightKg;
    payload.hand = form.hand;
    payload.years = form.years || 0;
    payload.level = form.level;

    const res = await request('/api/v1/subjects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const sub = res.item;
    setCurrentSubjectId(sub.id);
    // 通知路由守卫跳过缓存（通过 sessionStorage 避免循环引用）
    try { window.sessionStorage.setItem(STORAGE_KEYS.subjectJustCreated, '1'); } catch {}
    notifySubjectChanged();
    router.push('/training?selectMode=1');
  } catch (error) {
    isError.value = true;
    message.value = error.message || '创建失败，请重试。';
    // 同名冲突 → 自动展开选填信息，提醒用户补充更多区分信息
    if ((error.message || '').includes('补充')) {
      extraOpen.value = true;
    }
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.csub-page {
  min-height: calc(100vh - 112px);
  display: grid;
  place-items: center;
  padding: 32px;
}
.csub-card {
  background: #fff;
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 12px;
  padding: 36px 40px;
  max-width: 480px;
  width: 100%;
}
.csub-title { font-size: 22px; font-weight: 600; color: #0f172a; margin: 0 0 6px; letter-spacing: -0.02em; }
.csub-desc { font-size: 14px; color: #64748b; margin: 0 0 24px; }

.csub-form { display: flex; flex-direction: column; gap: 14px; }
.csub-field { display: flex; flex-direction: column; gap: 4px; }
.csub-field span { font-size: 13px; font-weight: 500; color: #475569; }
.csub-field span em { color: #dc2626; font-style: normal; }
.csub-field input, .csub-field select {
  padding: 9px 12px;
  border: 1px solid rgba(0,0,0,0.10);
  border-radius: 7px;
  font-size: 14px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.csub-field input:focus, .csub-field select:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.08);
}

.csub-extra { margin-top: 2px; }
.csub-extra summary { font-size: 13px; color: #94a3b8; cursor: pointer; }
.csub-extra__grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; }

.csub-btn {
  margin-top: 4px;
  padding: 11px 24px;
  border: none;
  border-radius: 8px;
  background: #2563eb;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}
.csub-btn:hover:not(:disabled) { background: #1d4ed8; }
.csub-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.csub-msg { font-size: 13px; color: #16a34a; margin: 0; }
.csub-msg--err { color: #dc2626; }
</style>
