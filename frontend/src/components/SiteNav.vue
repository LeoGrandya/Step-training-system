<!-- 运行时必需。全站顶栏导航。 -->
<template>
  <nav class="site-nav" aria-label="主导航">
    <RouterLink to="/home" class="site-nav__brand">
      <img :src="logoUrl" alt="慧步乒乓" class="site-nav__logo" />
    </RouterLink>
    <div class="site-nav__links">
      <template v-for="item in NAV_ITEMS" :key="item.label">
        <RouterLink v-if="item.to" :to="item.to" class="site-nav__link">{{ item.label }}</RouterLink>
        <a v-else :href="item.href" class="site-nav__link">{{ item.label }}</a>
      </template>

      <div class="site-nav__dropdown" @mouseenter="openDropdown" @mouseleave="closeDropdown">
        <span class="site-nav__link site-nav__dropdown-trigger" :class="{ 'site-nav__link--active': dropdownOpen }">脚步训练 ▾</span>
        <Transition name="dd-fade">
          <div v-if="dropdownOpen" class="site-nav__dropdown-menu">
            <RouterLink v-for="item in TRAINING_DROPDOWN" :key="item.label" :to="item.to" class="site-nav__dropdown-item">{{ item.label }}</RouterLink>
          </div>
        </Transition>
      </div>

      <RouterLink v-if="isLoggedIn" to="/account" class="site-nav__link site-nav__auth">我的</RouterLink>
      <RouterLink v-else to="/auth" class="site-nav__link site-nav__auth">登录/注册</RouterLink>
    </div>
  </nav>
</template>

<script setup>
import { ref } from 'vue';
import { NAV_ITEMS, TRAINING_DROPDOWN } from '../router/nav.js';
import { isLoggedIn } from '../router/guard.js';

const logoUrl = '/assets/img/huibu-logo.png';
const dropdownOpen = ref(false);

function openDropdown() { dropdownOpen.value = true; }
function closeDropdown() { dropdownOpen.value = false; }
</script>

<style scoped>
.site-nav__dropdown {
  position: relative;
  display: flex;
  align-items: center;
}

.site-nav__dropdown-trigger {
  cursor: default;
}

.site-nav__dropdown-menu {
  position: absolute;
  top: 100%;
  left: 0;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(12px);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  box-shadow: 0 8px 30px rgba(15, 23, 42, 0.10);
  min-width: 150px;
  padding: 6px 0;
  z-index: 100;
  display: flex;
  flex-direction: column;
}

.site-nav__dropdown-item {
  padding: 9px 18px;
  font-size: 14px;
  color: var(--color-text, #334155);
  text-decoration: none;
  transition: background 0.12s, color 0.12s;
}

.site-nav__dropdown-item:hover {
  background: var(--color-bg-muted, #f1f5f9);
  color: var(--color-primary, #2563eb);
}

.dd-fade-enter-active,
.dd-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.dd-fade-enter-from,
.dd-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
