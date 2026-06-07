<!-- 运行时必需。最近分析列表：预览版，显示关键指标，点击跳转报告。 -->
<template>
  <div class="recent-list">
    <h3 class="recent-list__title">
      最近分析
      <button type="button" class="recent-list__refresh" @click="refresh" :disabled="loading" aria-label="刷新">&circlearrowright;</button>
    </h3>

    <div v-if="loading" class="recent-list__state">加载中...</div>
    <div v-else-if="error" class="recent-list__state recent-list__state--error">{{ error }}</div>
    <div v-else-if="!items.length" class="recent-list__state">暂无分析记录</div>

    <ul v-else class="recent-list__items">
      <li v-for="item in items" :key="item.jobId" class="recent-list__item">
        <a :href="'/#/report/' + encodeURIComponent(item.jobId)" class="recent-list__link">
          <span class="recent-list__item-date">{{ item.date }}</span>
          <span v-if="item.avgSpeed" class="recent-list__item-metric">
            <span class="recent-list__metric-label">均速</span>
            <span class="recent-list__metric-val">{{ item.avgSpeed }} m/s</span>
          </span>
          <span v-if="item.score != null" class="recent-list__item-score">{{ item.score }}</span>
        </a>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { useRecentAnalyses } from '../composables/useRecentAnalyses.js'

const { items, loading, error, refresh } = useRecentAnalyses(5)
</script>
