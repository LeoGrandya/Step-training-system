<!-- 运行时必需。全站顶栏导航。 -->
<template>
  <nav class="site-nav" aria-label="主导航">
    <RouterLink to="/home" class="site-nav__brand">
      <img :src="logoUrl" alt="慧步乒乓" class="site-nav__logo" />
    </RouterLink>
    <div class="site-nav__links">
      <template v-for="item in NAV_ITEMS" :key="item.label">
        <RouterLink v-if="item.to" :to="item.to" class="site-nav__link" :class="{ 'site-nav__auth': item.auth }">{{ item.label }}</RouterLink>
        <a v-else :href="item.href" class="site-nav__link" :class="{ 'site-nav__auth': item.auth }">{{ item.label }}</a>
      </template>
    </div>
  </nav>
</template>

<script setup>
import { NAV_ITEMS } from '../router/nav.js';

const logoUrl = '/assets/img/huibu-logo.png';
</script>
