<!-- 运行时必需。最近分析列表：Linear 风格。 -->
<template>
  <div class="rcl">
    <h3 class="rcl__title">
      最近分析
      <button type="button" class="rcl__refresh" @click="refresh" :disabled="loading" aria-label="刷新">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
      </button>
    </h3>

    <div v-if="loading" class="rcl__state">加载中...</div>
    <div v-else-if="error" class="rcl__state rcl__state--err">{{ error }}</div>
    <div v-else-if="!items.length" class="rcl__state">暂无分析记录</div>

    <ul v-else class="rcl__items">
      <li v-for="item in items" :key="item.jobId" class="rcl__item">
        <a :href="'/#/report/' + encodeURIComponent(item.jobId)" class="rcl__link">
          <span class="rcl__date">{{ item.date }}</span>
          <span class="rcl__metrics">
            <span v-if="item.avgSpeed" class="rcl__metric">{{ item.avgSpeed }} m/s</span>
            <span v-if="item.score != null" class="rcl__score">{{ item.score }}</span>
          </span>
        </a>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { useRecentAnalyses } from '../composables/useRecentAnalyses.js'
const { items, loading, error, refresh } = useRecentAnalyses(5)
</script>

<style scoped>
.rcl__title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  margin: 0 0 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.rcl__refresh {
  border: none;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
  display: flex;
  transition: color 0.12s;
}
.rcl__refresh:hover { color: #64748b; }

.rcl__state {
  font-size: 13px;
  color: #94a3b8;
  padding: 8px 0;
}
.rcl__state--err { color: #dc2626; }

.rcl__items {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.rcl__item { border-radius: 6px; overflow: hidden; }

.rcl__link {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  text-decoration: none;
  border-radius: 6px;
  transition: background 0.12s;
}
.rcl__link:hover { background: #f8fafc; }
.rcl__date {
  font-size: 13px;
  color: #475569;
}
.rcl__metrics {
  display: flex;
  gap: 10px;
}
.rcl__metric {
  font-size: 12px;
  color: #94a3b8;
}
.rcl__score {
  font-size: 13px;
  font-weight: 600;
  color: #2563eb;
}
</style>
