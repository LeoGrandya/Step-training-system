<!-- 运行时必需。历史报告页：筛选 + 卡片网格 + 对比。 -->
<template>
  <section class="page-stack report-history-page">
    <header class="analysis-header">
      <h1>历史报告</h1>
    </header>

    <ReportFilterBar
      :userId="userId"
      :users="users"
      :userProfile="userProfile"
      :filters="filters"
      @update:userId="onUserChange"
      @update:filters="onFiltersChange"
      @reset="resetFilters"
    />

    <p v-if="error" class="analysis-page__error">{{ error }}</p>

    <div v-if="loading" class="report-history__state">加载中...</div>
    <div v-else-if="!reports.length" class="report-history__state report-history__state--empty">
      暂无历史报告，完成一次分析后自动生成
    </div>

    <div v-else class="report-grid">
      <ReportCard
        v-for="report in reports"
        :key="report.id"
        :report="report"
        :selected="selectedIds.includes(report.id)"
        @toggle-select="toggleSelect"
        @delete="handleDelete"
      />
    </div>

    <div v-if="selectedIds.length" class="report-compare-bar">
      <span class="report-compare-bar__label">已选 {{ selectedIds.length }} 份</span>
      <span class="report-compare-bar__limit">对比上限 {{ maxCompare }} 份</span>
      <div class="report-compare-bar__actions">
        <button type="button" class="report-compare-bar__btn report-compare-bar__btn--clear" @click="clearSelection">清除</button>
        <button
          type="button"
          class="report-compare-bar__btn report-compare-bar__btn--compare"
          :disabled="selectedIds.length < 2"
          @click="openCompare"
        >对比分析</button>
      </div>
    </div>

    <ReportCompareModal
      :open="compareOpen"
      :data="compareData"
      :loading="compareLoading"
      @close="compareOpen = false"
    />
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import ReportFilterBar from '../components/ReportFilterBar.vue'
import ReportCard from '../components/ReportCard.vue'
import ReportCompareModal from '../components/ReportCompareModal.vue'
import { useReportHistory } from '../composables/useReportHistory.js'
import { getCurrentUserId, STORAGE_KEYS } from '../stores/storage.js'

const { reports, users, userProfile, loading, error, fetchUsers, fetchUserProfile, fetchReports, deleteReport, compareReports } = useReportHistory()

const userId = ref(getCurrentUserId() || '')
const selectedIds = ref([])
const filters = ref({ mode: '', startDate: '', endDate: '', stepName: '' })
const compareOpen = ref(false)
const compareData = ref([])
const compareLoading = ref(false)
const maxCompare = computed(() => {
  try {
    const raw = window.localStorage.getItem('ai_sport_lab.max_compare_reports')
    const n = Number.parseInt(raw, 10)
    if (Number.isFinite(n) && n >= 2 && n <= 50) return n
  } catch {}
  return 10
})

async function loadData() {
  if (!userId.value) return
  await fetchUserProfile(userId.value)
  await fetchReports(userId.value, filters.value)
}

async function onUserChange(newId) {
  userId.value = newId
  selectedIds.value = []
  await loadData()
}

async function onFiltersChange(newFilters) {
  filters.value = newFilters
  selectedIds.value = []
  await loadData()
}

async function resetFilters() {
  filters.value = { mode: '', startDate: '', endDate: '', stepName: '' }
  selectedIds.value = []
  await loadData()
}

function toggleSelect(reportId) {
  const idx = selectedIds.value.indexOf(reportId)
  if (idx > -1) {
    selectedIds.value.splice(idx, 1)
  } else if (selectedIds.value.length < maxCompare.value) {
    selectedIds.value.push(reportId)
  }
}

function clearSelection() {
  selectedIds.value = []
}

async function handleDelete(reportId) {
  if (!window.confirm('确定删除该条历史报告？删除后不可恢复。')) return
  const ok = await deleteReport(reportId)
  if (!ok) return
  selectedIds.value = selectedIds.value.filter(id => id !== reportId)
  reports.value = reports.value.filter(r => r.id !== reportId)
}

async function openCompare() {
  if (selectedIds.value.length < 2) return
  compareOpen.value = true
  compareLoading.value = true
  const data = await compareReports(selectedIds.value)
  compareData.value = data
  compareLoading.value = false
}

onMounted(async () => {
  document.documentElement.dataset.pageReady = 'report-history'
  await fetchUsers()
  // 无缓存用户时自动选第一个可用用户
  if (!userId.value && users.value.length) {
    userId.value = users.value[0].id
  }
  // 加载档案和报告列表
  await loadData()
})
</script>
