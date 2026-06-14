<!-- 报告图表无数据时的统一占位提示 -->
<template>
  <div class="report-empty-state flex items-center justify-center bg-slate-50 rounded-lg border border-slate-200/60" :style="{ minHeight: minHeight + 'px' }">
    <div class="text-center">
      <svg class="w-8 h-8 mx-auto mb-2 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
      <p class="text-sm text-slate-400">{{ text }}</p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  text: { type: String, default: '暂无可用数据' },
  minHeight: { type: Number, default: 120 },
})
</script>
