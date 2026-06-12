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

      <!-- 受试者切换 -->
      <div v-if="isLoggedIn" class="site-nav__dropdown" @mouseenter="subOpen = true" @mouseleave="subOpen = false">
        <span class="site-nav__link site-nav__dropdown-trigger" :class="{ 'site-nav__link--active': subOpen }">受试者：{{ currentSubjectName }} ▾</span>
        <Transition name="dd-fade">
          <div v-if="subOpen && subjects.length" class="site-nav__dropdown-menu site-nav__subject-menu">
            <button
              v-for="sub in subjects"
              :key="sub.id"
              class="site-nav__dropdown-item"
              :class="{ 'site-nav__dropdown-item--active': sub.id === currentSubjectId }"
              @click="switchSubject(sub)"
            >{{ sub.displayName || sub.name }}</button>
          </div>
        </Transition>
      </div>

      <RouterLink v-if="isLoggedIn" to="/account" class="site-nav__link site-nav__auth">我的</RouterLink>
      <RouterLink v-else to="/auth" class="site-nav__link site-nav__auth">登录/注册</RouterLink>
    </div>
  </nav>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { NAV_ITEMS, TRAINING_DROPDOWN } from '../router/nav.js';
import { isLoggedIn } from '../router/guard.js';
import { getCurrentSubjectId, setCurrentSubjectId } from '../stores/storage.js';
import { request } from '../services/api.js';

const logoUrl = '/assets/img/huibu-logo.png';
const dropdownOpen = ref(false);
const subOpen = ref(false);
const subjects = ref([]);
const currentSubjectId = ref(getCurrentSubjectId());

const currentSubjectName = computed(() => {
  if (!subjects.value.length) return '无受试者';
  const sub = subjects.value.find(s => s.id === currentSubjectId.value);
  return sub ? (sub.displayName || sub.name) : (subjects.value[0].displayName || subjects.value[0].name);
});

async function loadSubjects() {
  try {
    const payload = await request('/api/v1/subjects');
    subjects.value = payload.items || [];
    if (!currentSubjectId.value && subjects.value.length) {
      currentSubjectId.value = subjects.value[0].id;
      setCurrentSubjectId(subjects.value[0].id);
    }
  } catch { subjects.value = []; }
}

function switchSubject(sub) {
  currentSubjectId.value = sub.id;
  setCurrentSubjectId(sub.id);
  subOpen.value = false;
  window.dispatchEvent(new CustomEvent('subject-changed', { detail: sub }));
}

function openDropdown() { dropdownOpen.value = true; }
function closeDropdown() { dropdownOpen.value = false; }

function onSubChanged() { loadSubjects(); }

watch(isLoggedIn, (val) => { if (val) loadSubjects(); });
onMounted(() => {
  if (isLoggedIn.value) loadSubjects();
  window.addEventListener('subject-changed', onSubChanged);
});
onBeforeUnmount(() => {
  window.removeEventListener('subject-changed', onSubChanged);
});
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
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(0,0,0,0.07);
  border-radius: 10px;
  box-shadow: 0 12px 40px rgba(15, 23, 42, 0.08);
  min-width: 150px;
  padding: 6px;
  z-index: 100;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.site-nav__dropdown-item {
  padding: 6px 12px;
  font-size: 13px;
  color: #475569;
  background: transparent !important;
  font-weight: 400 !important;
  text-decoration: none;
  border-radius: 6px;
  transition: background 0.12s, color 0.12s;
  display: flex;
  align-items: center;
}

.site-nav__dropdown-item:hover {
  background: #f1f5f9 !important;
  color: #1e293b !important;
}

.site-nav__dropdown-item--active {
  color: #0f172a;
  font-weight: 500;
}
.site-nav__dropdown-item--active::before {
  content: '';
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #2563eb;
  margin-right: 8px;
  flex-shrink: 0;
}

.dd-fade-enter-active,
.dd-fade-leave-active {
  transition: opacity 0.12s ease, transform 0.12s ease;
}
.dd-fade-enter-from,
.dd-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.site-nav__subject-menu {
  right: 0;
  left: auto;
  min-width: 150px;
}
</style>
