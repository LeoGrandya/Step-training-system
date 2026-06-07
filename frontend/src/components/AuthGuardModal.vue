<!-- 未登录时点击需认证页面的弹出提示。 -->
<template>
  <Teleport to="body">
    <div v-if="visible" class="auth-guard-overlay" @click.self="dismiss">
      <div class="auth-guard-modal">
        <p class="auth-guard-modal__icon">🔐</p>
        <h2 class="auth-guard-modal__title">需要登录</h2>
        <p class="auth-guard-modal__desc">进入此功能前需要先登录或注册账号。</p>
        <div class="auth-guard-modal__actions">
          <button class="auth-guard-modal__btn auth-guard-modal__btn--secondary" @click="dismiss">暂不登录</button>
          <button class="auth-guard-modal__btn auth-guard-modal__btn--primary" @click="goLogin">前往登录</button>
        </div>
        <p class="auth-guard-modal__hint">不登录仍可浏览：<span>首页</span> · <span>产品介绍</span> · <span>团队介绍</span></p>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();
const visible = ref(false);
let pendingRedirect = '';

function show(redirectPath) {
  pendingRedirect = redirectPath || '/training';
  visible.value = true;
}

function dismiss() {
  visible.value = false;
  pendingRedirect = '';
}

function goLogin() {
  const target = pendingRedirect;
  visible.value = false;
  pendingRedirect = '';
  router.push('/auth' + (target ? `?redirect=${encodeURIComponent(target)}` : ''));
}

defineExpose({ show });
</script>

<style scoped>
.auth-guard-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  animation: ag-fade-in 0.15s ease;
}
@keyframes ag-fade-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}

.auth-guard-modal {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.18);
  padding: 32px 36px 28px;
  max-width: 380px;
  width: 90vw;
  text-align: center;
  animation: ag-slide-up 0.20s ease;
}
@keyframes ag-slide-up {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

.auth-guard-modal__icon {
  font-size: 36px;
  margin: 0 0 8px;
}

.auth-guard-modal__title {
  margin: 0 0 6px;
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text, #0f172a);
}

.auth-guard-modal__desc {
  margin: 0 0 24px;
  font-size: 14px;
  color: var(--color-text-muted, #64748b);
  line-height: 1.5;
}

.auth-guard-modal__actions {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.auth-guard-modal__btn {
  padding: 9px 22px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: background 0.15s, opacity 0.15s;
}
.auth-guard-modal__btn--secondary {
  background: var(--color-bg-muted, #f1f5f9);
  color: var(--color-text, #475569);
}
.auth-guard-modal__btn--secondary:hover {
  background: #e2e8f0;
}
.auth-guard-modal__btn--primary {
  background: var(--color-primary, #2563eb);
  color: #fff;
}
.auth-guard-modal__btn--primary:hover {
  background: #1d4ed8;
}

.auth-guard-modal__hint {
  margin: 20px 0 0;
  font-size: 12px;
  color: var(--color-text-muted, #94a3b8);
  line-height: 1.5;
}
.auth-guard-modal__hint span {
  color: var(--color-text, #64748b);
  font-weight: 500;
}
</style>
