/** 最近分析记录：从结果索引加载。 */
import { ref, onMounted } from 'vue'

export function useRecentAnalyses(limit = 5) {
  const items = ref([])
  const loading = ref(false)
  const error = ref('')

  async function fetchRecent() {
    loading.value = true
    error.value = ''
    try {
      const response = await fetch('/api/analysis/results?limit=' + limit)
      const payload = await response.json().catch(() => ({}))
      if (!response.ok || !payload.ok) {
        error.value = '加载最近分析失败'
        return
      }
      items.value = (payload.items || []).slice(0, limit).map(formatItem)
    } catch (err) {
      error.value = err.message || '加载失败'
    } finally {
      loading.value = false
    }
  }

  function formatItem(item) {
    const summary = item.summaryMetrics || {}
    return {
      jobId: item.jobId || '',
      date: (item.savedAt || '').slice(0, 10) || '未知日期',
      title: item.title || '分析记录',
      avgSpeed: summary.mean_com_speed_mps != null ? Number(summary.mean_com_speed_mps).toFixed(2) : null,
      score: summary.score != null ? summary.score : null,
    }
  }

  onMounted(fetchRecent)

  return { items, loading, error, refresh: fetchRecent }
}
