<!-- 运行时必需。iframe 嵌入 site/ 遗留 HTML 页面。 -->
<template>
  <iframe
    class="legacy-frame"
    :key="legacyFile"
    :src="legacySrc"
    :title="legacyTitle"
  ></iframe>
</template>

<script setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();

const LEGACY_TITLES = {
  'home.html': '首页',
  'product.html': '产品介绍',
  'loading.html': '分析加载',
  'report.html': '分析报告',
  'settings.html': '设置',
  'team.html': '团队介绍',
};

const LEGACY_FILES = [
  'home.html',
  'product.html',
  'loading.html',
  'report.html',
  'settings.html',
  'team.html',
];

const legacyFile = computed(() => {
  const file = route.meta.legacyFile;
  return LEGACY_FILES.includes(file) ? file : 'home.html';
});

const legacySrc = computed(() => {
  const params = new URLSearchParams();
  params.set('embedded', '1');
  Object.entries(route.query).forEach(([key, value]) => {
    if (value != null && value !== '') params.set(key, String(value));
  });
  if (route.params.jobId) params.set('jobId', String(route.params.jobId));
  const query = params.toString();
  return `/legacy-html/${legacyFile.value}${query ? `?${query}` : ''}`;
});
const legacyTitle = computed(() => LEGACY_TITLES[legacyFile.value] || '页面');
</script>
