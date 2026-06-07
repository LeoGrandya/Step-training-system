<!-- 运行时必需。根布局：全局导航 + RouterView；fullFrame 路由隐藏主栏样式。 -->
<template>
  <div class="app-shell" :class="{ 'app-shell--frame': route.meta.fullFrame }">
    <SiteNav />
    <main class="app-main" :class="{ 'app-main--frame': route.meta.fullFrame }">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router';
import SiteNav from './components/SiteNav.vue';

const route = useRoute();
</script>
