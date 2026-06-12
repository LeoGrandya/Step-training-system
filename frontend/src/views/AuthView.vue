<!-- 运行时必需。登录/注册页，对接 accounts 表。 -->
<template>
  <section class="auth-page" data-guide="auth-intro">
    <div class="auth-card auth-card--centered">
      <form class="auth-form" @submit.prevent="submit">
        <h2>{{ mode === 'login' ? '账号登录' : '账号注册' }}</h2>

        <input v-model.trim="form.account" type="text" placeholder="账号" required autocomplete="username" />
        <input v-if="mode === 'register'" v-model.trim="form.username" type="text" placeholder="用户名（显示用）" required />
        <div class="auth-pwd-wrap">
          <input v-model="form.password" :type="passwordType" placeholder="密码" required minlength="4" autocomplete="current-password" @input="sanitizePassword" />
          <button type="button" class="auth-pwd-toggle" @click="showPassword = !showPassword" :title="showPassword ? '隐藏密码' : '显示密码'">
            <svg v-if="showPassword" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
            <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
        </div>

        <ul v-if="mode === 'register'" class="auth-checklist">
          <li :class="{ done: !!form.account.trim() }">账号 <span class="auth-checklist__hint">— 建议使用数字，便于登录</span></li>
          <li :class="{ done: !!form.username.trim() }">用户名</li>
          <li :class="{ done: /^[\x20-\x7e]{4,}$/.test(form.password) }">密码，至少 4 位，仅限字母、数字、英文符号</li>
        </ul>

        <button type="submit" :disabled="submitting" data-guide="auth-submit">
          {{ submitting ? '处理中...' : (mode === 'login' ? '进入训练' : '完成注册') }}
        </button>
        <button type="button" class="link-button" @click="toggleMode">
          {{ mode === 'login' ? '还没有账号？立即注册' : '已有账号？立即登录' }}
        </button>
        <p v-if="message" class="hint">{{ message }}</p>
      </form>
    </div>
  </section>
</template>

<script setup>
import { computed, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { registerAccount, loginAccount } from '../services/api.js';
import { loginAccountSession, savePose3dProfile } from '../stores/storage.js';
import { refreshLoginState } from '../router/guard.js';

const route = useRoute();
const router = useRouter();
const mode = ref('login');
const form = reactive({ account: '', username: '', password: '' });
const showPassword = ref(false);
const passwordType = computed(() => showPassword.value ? 'text' : 'password');
const submitting = ref(false);
const message = ref('');

function sanitizePassword() {
  form.password = form.password.replace(/[^\x20-\x7e]/g, '');
}

function toggleMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login';
  message.value = '';
  form.account = '';
  form.username = '';
  form.password = '';
}

const ERROR_CN = {
  account_required: '请输入账号',
  username_required: '请输入用户名',
  account_and_password_required: '请输入账号和密码',
  password_too_short: '密码至少需要 4 位字符',
  duplicate_account: '该账号已被注册',
  invalid_credentials: '账号或密码错误',
  invalid_old_password: '旧密码不正确',
};

function toCnMessage(err) {
  const msg = (err && err.message) || '';
  return ERROR_CN[msg] || msg || '操作失败，请稍后重试。';
}

async function submit() {
  submitting.value = true;
  message.value = '';

  if (mode.value === 'register') {
    if (!form.account.trim()) { message.value = '请输入账号'; submitting.value = false; return; }
    if (!form.username.trim()) { message.value = '请输入用户名'; submitting.value = false; return; }
    if (form.password.length < 4) { message.value = '密码至少需要 4 位字符'; submitting.value = false; return; }
  }

  try {
    let item;
    if (mode.value === 'register') {
      const res = await registerAccount({
        account: form.account.trim(),
        username: form.username.trim(),
        password: form.password,
      });
      item = res.item;
    } else {
      const res = await loginAccount({
        account: form.account.trim(),
        password: form.password,
      });
      item = res.item;
    }

    loginAccountSession(item);
    savePose3dProfile({ name: item?.username || item?.account || '' });
    refreshLoginState();
    router.push(String(route.query.redirect || '/training?selectMode=1'));
  } catch (error) {
    message.value = toCnMessage(error);
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.auth-checklist {
  list-style: none;
  padding: 0;
  margin: 16px 0 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: var(--color-text-muted, #94a3b8);
}

.auth-checklist li::before {
  content: '○';
  display: inline-block;
  width: 18px;
  margin-right: 6px;
  color: var(--color-border, #cbd5e1);
}

.auth-checklist li.done {
  color: var(--color-success, #16a34a);
}

.auth-checklist li.done::before {
  content: '●';
  color: var(--color-success, #16a34a);
}

.auth-checklist__hint {
  color: var(--color-text-muted, #94a3b8);
  font-weight: 400;
}

.auth-card--centered {
  grid-template-columns: 1fr;
  max-width: 420px;
  width: 100%;
}

.auth-pwd-wrap {
  position: relative;
}

.auth-pwd-wrap input {
  padding-right: 40px;
}

.auth-pwd-toggle {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 4px;
  line-height: 1;
  color: #94a3b8;
  display: flex;
  align-items: center;
  transition: color 0.15s;
}
.auth-pwd-toggle:hover {
  color: #475569;
}
</style>
