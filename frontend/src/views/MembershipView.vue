<template>
  <div class="membership-page">
    <!-- ========== 顶部导航栏 ========== -->
    <header class="membership-nav">
      <button class="nav-back" @click="goBack" aria-label="返回">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </button>
      <h1 class="nav-title">购买会员</h1>
      <div class="nav-capsules">
        <button class="capsule-btn" aria-label="更多">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
            <circle cx="5" cy="12" r="2" />
            <circle cx="12" cy="12" r="2" />
            <circle cx="19" cy="12" r="2" />
          </svg>
        </button>
        <button class="capsule-btn" @click="goHome" aria-label="主页">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </button>
      </div>
    </header>

    <!-- ========== 会员方案内容（复用组件） ========== -->
    <MembershipPlans />
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import MembershipPlans from '../components/MembershipPlans.vue'

const router = useRouter()

const goBack = () => {
  router.back()
}

const goHome = () => {
  router.push('/')
}
</script>

<style scoped>
/* ==================== 页面容器 ==================== */
.membership-page {
  max-width: 480px;
  margin: 0 auto;
  padding: 0 16px 40px;
  background: #f1f5f9;
  min-height: 100vh;
  font-family: "DM Sans", Inter, "Microsoft YaHei", Arial, sans-serif;
  color: #0f172a;
}

/* ==================== 导航栏 ==================== */
.membership-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  position: sticky;
  top: 0;
  background: #f1f5f9;
  z-index: 10;
}

.nav-back {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: #fff;
  border-radius: 50%;
  color: #334155;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
  transition: background 0.15s;
}

.nav-back:hover {
  background: #e2e8f0;
}

.nav-title {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
}

.nav-capsules {
  display: flex;
  gap: 6px;
}

.capsule-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 50%;
  color: #64748b;
  cursor: pointer;
  transition: background 0.15s;
}

.capsule-btn:hover {
  background: #f1f5f9;
}

/* ==================== 响应式 ==================== */
@media (min-width: 640px) {
  .membership-page {
    max-width: 560px;
    padding: 0 24px 48px;
  }
}
</style>
