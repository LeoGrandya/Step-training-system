<!-- 运行时必需。个人账号页：侧边栏 + 个人信息/修改密码。 -->
<template>
  <section class="page-stack account-page">
    <!-- 页头：标题左，退出登录以小脚注形式放右边 -->
    <header class="account-page__head">
      <div>
        <p class="eyebrow">Step Training</p>
        <h1>我的账号</h1>
      </div>
      <button class="account-page__logout" @click="handleLogout" title="退出登录">退出登录 &rarr;</button>
    </header>

    <!-- 分割线 -->
    <hr class="account-page__hr" />

    <!-- 主体：侧边栏 + 内容区 -->
    <div class="account-page__body">
      <!-- 侧边栏 -->
      <nav class="account-nav">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          class="account-nav__item"
          :class="{ 'account-nav__item--active': activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          <span class="account-nav__dot" aria-hidden="true" />
          {{ tab.label }}
        </button>
      </nav>

      <!-- 分隔 -->
      <div class="account-page__divider" aria-hidden="true" />

      <!-- 右侧内容区 -->
      <main class="account-main">
        <!-- 个人信息 -->
        <template v-if="activeTab === 'info' && account">
          <h2 class="account-main__title">个人信息</h2>
          <hr class="account-main__hr" />
          <dl class="account-info-dl">
            <div class="account-info-dl__row">
              <dt>账号</dt>
              <dd>{{ account.account }}</dd>
            </div>
            <div class="account-info-dl__row">
              <dt>用户名</dt>
              <dd>{{ account.username }}</dd>
            </div>
            <div class="account-info-dl__row">
              <dt>角色</dt>
              <dd v-if="account.roles && account.roles.length">
                {{ account.roles.map(r => r.name).join('、') }}
              </dd>
              <dd v-else class="account-info-dl__muted">暂无角色</dd>
            </div>
            <div class="account-info-dl__row">
              <dt>注册时间</dt>
              <dd>{{ formatDate(account.createdAt) }}</dd>
            </div>
          </dl>
        </template>

        <!-- 会员升级 -->
        <template v-if="activeTab === 'membership'">
          <h2 class="account-main__title">会员升级</h2>
          <hr class="account-main__hr" />
          <MembershipPlans />
        </template>

        <!-- 修改密码 -->
        <template v-if="activeTab === 'password'">
          <h2 class="account-main__title">修改密码</h2>
          <hr class="account-main__hr" />
          <form class="account-pwd-form" @submit.prevent="submitPassword">
            <label class="account-pwd-form__field">
              <span>旧密码</span>
              <input v-model="pwdForm.oldPassword" type="password" required autocomplete="current-password" />
            </label>
            <label class="account-pwd-form__field">
              <span>新密码</span>
              <input v-model="pwdForm.newPassword" type="password" required minlength="4" autocomplete="new-password" />
            </label>
            <label class="account-pwd-form__field">
              <span>确认新密码</span>
              <input v-model="pwdForm.confirmPassword" type="password" required minlength="4" autocomplete="new-password" />
            </label>
            <div class="account-pwd-form__actions">
              <button type="submit" :disabled="pwdSubmitting">
                {{ pwdSubmitting ? '提交中...' : '修改密码' }}
              </button>
            </div>
            <p v-if="pwdMessage" class="account-pwd-form__msg" :class="{ 'is-ok': pwdOk }">{{ pwdMessage }}</p>
          </form>
        </template>

        <p v-if="!account && !loading" class="account-main__error">加载账号信息失败，请重新登录。</p>
      </main>
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue';
import { getAccountMe, changePassword } from '../services/api.js';
import { getCurrentAccountId, logoutAccountSession } from '../stores/storage.js';
import { refreshLoginState } from '../router/guard.js';
import { useRouter } from 'vue-router';
import MembershipPlans from '../components/MembershipPlans.vue';

const router = useRouter();
const tabs = [
  { key: 'info', label: '个人信息' },
  { key: 'membership', label: '会员升级' },
  { key: 'password', label: '修改密码' },
];
const activeTab = ref('info');
const account = ref(null);
const loading = ref(true);

const pwdForm = reactive({ oldPassword: '', newPassword: '', confirmPassword: '' });
const pwdSubmitting = ref(false);
const pwdMessage = ref('');
const pwdOk = ref(false);

function handleLogout() {
  logoutAccountSession();
  refreshLoginState();
  router.push('/home');
}

function formatDate(iso) {
  if (!iso) return '-';
  return iso.slice(0, 10);
}

async function submitPassword() {
  pwdMessage.value = '';
  pwdOk.value = false;

  if (pwdForm.newPassword.length < 4) {
    pwdMessage.value = '新密码至少 4 位。';
    return;
  }
  if (pwdForm.newPassword !== pwdForm.confirmPassword) {
    pwdMessage.value = '两次输入的新密码不一致。';
    return;
  }

  pwdSubmitting.value = true;
  try {
    await changePassword({
      oldPassword: pwdForm.oldPassword,
      newPassword: pwdForm.newPassword,
    });
    pwdOk.value = true;
    pwdMessage.value = '密码修改成功。';
    pwdForm.oldPassword = '';
    pwdForm.newPassword = '';
    pwdForm.confirmPassword = '';
  } catch (error) {
    pwdMessage.value = error.message || '修改失败，请检查旧密码是否正确。';
  } finally {
    pwdSubmitting.value = false;
  }
}

onMounted(async () => {
  const aid = getCurrentAccountId();
  if (!aid) {
    loading.value = false;
    return;
  }
  try {
    const res = await getAccountMe();
    account.value = res.item || null;
  } catch {
    account.value = null;
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
/* ===== 页头 ===== */
.account-page__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}

.account-page__logout {
  border: none;
  background: transparent;
  color: var(--color-text-muted, #94a3b8);
  font-size: 13px;
  cursor: pointer;
  padding: 2px 0;
  transition: color 0.15s;
}
.account-page__logout:hover {
  color: var(--color-danger, #dc2626);
}

/* ===== 全局分割线 ===== */
.account-page__hr {
  border: none;
  border-top: 1px solid var(--color-border, #e2e8f0);
  margin: 20px 0 28px;
}

/* ===== 主体（侧边栏 + 内容） ===== */
.account-page__body {
  display: flex;
  gap: 0;
  min-height: 380px;
}

/* ===== 侧边栏 ===== */
.account-nav {
  width: 172px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-top: 4px;
}

.account-nav__item {
  display: flex;
  align-items: center;
  gap: 8px;
  border: none;
  background: transparent;
  padding: 9px 12px;
  border-radius: 6px;
  font-size: 14px;
  color: var(--color-text, #334155);
  cursor: pointer;
  text-align: left;
  transition: background 0.12s, color 0.12s;
}
.account-nav__item:hover {
  background: var(--color-bg-muted, #f8fafc);
}
.account-nav__item--active {
  font-weight: 600;
  color: var(--color-primary, #1d4ed8);
  background: var(--color-bg-muted, #f1f5f9);
}

.account-nav__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: transparent;
  flex-shrink: 0;
  transition: background 0.12s;
}
.account-nav__item--active .account-nav__dot {
  background: var(--color-primary, #1d4ed8);
}

/* ===== 侧边栏-内容分割线 ===== */
.account-page__divider {
  width: 1px;
  background: var(--color-border, #e2e8f0);
  margin: 0 28px;
  flex-shrink: 0;
  align-self: stretch;
}

/* ===== 内容区 ===== */
.account-main {
  flex: 1;
  min-width: 0;
  padding-top: 4px;
}

.account-main__title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 12px;
  color: var(--color-text, #0f172a);
}

.account-main__hr {
  border: none;
  border-top: 1px solid var(--color-border, #e2e8f0);
  margin: 0 0 20px;
}

/* ===== 个人信息 DL ===== */
.account-info-dl {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  max-width: 480px;
}

.account-info-dl__row {
  padding: 14px 0;
  border-bottom: 1px solid var(--color-border-light, #f1f5f9);
}
.account-info-dl__row:nth-last-child(1),
.account-info-dl__row:nth-last-child(2) {
  border-bottom: none;
}

.account-info-dl__row dt {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-muted, #94a3b8);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}

.account-info-dl__row dd {
  margin: 0;
  font-size: 15px;
  font-weight: 500;
  color: var(--color-text, #1e293b);
}

.account-info-dl__muted {
  color: var(--color-text-muted, #94a3b8) !important;
  font-weight: 400 !important;
}

/* ===== 修改密码表单 ===== */
.account-pwd-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 360px;
}

.account-pwd-form__field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.account-pwd-form__field span {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text, #334155);
}
.account-pwd-form__field input {
  padding: 9px 12px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 6px;
  font-size: 14px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.account-pwd-form__field input:focus {
  border-color: var(--color-primary, #2563eb);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
}

.account-pwd-form__actions button {
  padding: 9px 22px;
  border: none;
  border-radius: 6px;
  background: var(--color-primary, #2563eb);
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.account-pwd-form__actions button:hover:not(:disabled) {
  background: #1d4ed8;
}
.account-pwd-form__actions button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.account-pwd-form__msg {
  font-size: 13px;
  color: var(--color-danger, #dc2626);
}
.account-pwd-form__msg.is-ok {
  color: var(--color-success, #16a34a);
}

.account-main__error {
  font-size: 14px;
  color: var(--color-text-muted, #94a3b8);
}
</style>
