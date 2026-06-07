/** 历史报告数据管理：列表、删除、对比、用户档案。 */
import { ref } from 'vue'

export function useReportHistory() {
  const reports = ref([])
  const users = ref([])
  const userProfile = ref(null)
  const loading = ref(false)
  const error = ref('')

  async function fetchUsers() {
    try {
      const resp = await fetch('/api/users')
      const payload = await resp.json().catch(() => ({}))
      if (resp.ok && payload.ok) users.value = payload.items || []
    } catch {}
  }

  async function fetchUserProfile(userId) {
    if (!userId) { userProfile.value = null; return }
    try {
      const resp = await fetch('/api/users/' + encodeURIComponent(userId))
      const payload = await resp.json().catch(() => ({}))
      if (resp.ok && payload.ok) userProfile.value = payload.user || payload.item || null
    } catch { userProfile.value = null }
  }

  async function fetchReports(userId, filters = {}) {
    if (!userId) { reports.value = []; return }
    loading.value = true
    error.value = ''
    try {
      let url = '/api/reports?user_id=' + encodeURIComponent(userId)
      if (filters.mode) url += '&mode=' + encodeURIComponent(filters.mode)
      if (filters.startDate) url += '&start_date=' + encodeURIComponent(filters.startDate)
      if (filters.endDate) url += '&end_date=' + encodeURIComponent(filters.endDate)
      if (filters.stepName) url += '&step_name=' + encodeURIComponent(filters.stepName)

      const resp = await fetch(url)
      const payload = await resp.json().catch(() => ({}))
      if (!resp.ok || !payload.ok || !Array.isArray(payload.items)) {
        reports.value = []
        return
      }
      reports.value = payload.items.map(formatReport)
    } catch (err) {
      error.value = err.message || '加载失败'
      reports.value = []
    } finally {
      loading.value = false
    }
  }

  function formatReport(item) {
    const summary = item.summary || {}
    return {
      id: item.id,
      date: formatDate(item.completedAt),
      mode: item.mode || 'eval',
      stepName: item.stepName || '未知步伐',
      summary: {
        loops: summary.loops || 0,
        avgSpeed: Number(summary.avgSpeed) || 0,
        symmetry: summary.symmetry != null ? summary.symmetry : 0,
        totalTime: Number(summary.totalTime) || 0,
        peakAccel: Number(summary.peakAccel) || 0,
      },
      userId: item.userId,
      jobId: item.jobId,
      completedAt: item.completedAt,
    }
  }

  function formatDate(dateStr) {
    if (!dateStr) return '未知日期'
    const d = new Date(dateStr)
    if (Number.isNaN(d.getTime())) return String(dateStr).slice(0, 10)
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0')
  }

  async function deleteReport(reportId) {
    try {
      const resp = await fetch('/api/reports/' + encodeURIComponent(reportId), { method: 'DELETE' })
      const payload = await resp.json().catch(() => ({}))
      return !!(resp.ok && payload.ok)
    } catch { return false }
  }

  async function compareReports(ids) {
    try {
      const resp = await fetch('/api/reports/compare?ids=' + encodeURIComponent(ids.join(',')))
      const payload = await resp.json().catch(() => ({}))
      if (resp.ok && payload.ok && payload.reports) return payload.reports
      return []
    } catch { return [] }
  }

  return {
    reports, users, userProfile, loading, error,
    fetchUsers, fetchUserProfile, fetchReports, deleteReport, compareReports,
  }
}
