<!-- 运行时必需。根布局：全局导航 + RouterView；fullFrame 路由隐藏主栏样式。 -->
<template>
  <div class="app-shell" :class="{ 'app-shell--frame': route.meta.fullFrame }">
    <SiteNav />
    <main class="app-main" :class="{ 'app-main--frame': route.meta.fullFrame }">
      <RouterView />
    </main>
  </div>
  <AuthGuardModal ref="authModal" />
</template>

<script setup>
import { ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import SiteNav from './components/SiteNav.vue';
import AuthGuardModal from './components/AuthGuardModal.vue';
import { authGuardRedirect } from './router/guard.js';

const route = useRoute();
const authModal = ref(null);

watch(authGuardRedirect, (path) => {
  if (path && authModal.value) {
    authModal.value.show(path);
    authGuardRedirect.value = '';
  }
});
</script>
