<!-- 运行时必需。历史报告页：筛选 + 卡片网格 + 对比。 -->
<template>
  <section class="rpt-page">
    <header class="rpt-hd">
      <div>
        <p class="rpt-hd__eyebrow">Step Training</p>
        <h1 class="rpt-hd__title">历史报告</h1>
      </div>
    </header>

    <hr class="rpt-divider" />

    <ReportFilterBar
      :userId="userId"
      :users="users"
      :userProfile="userProfile"
      :filters="filters"
      @update:userId="onUserChange"
      @update:filters="onFiltersChange"
      @reset="resetFilters"
    />

    <p v-if="error" class="rpt-err">{{ error }}</p>

    <div v-if="loading" class="rpt-state">加载中...</div>
    <div v-else-if="!reports.length" class="rpt-state rpt-state--empty">暂无历史报告，完成一次分析后自动生成</div>

    <div v-else class="rpt-grid">
      <ReportCard
        v-for="report in reports"
        :key="report.id"
        :report="report"
        :selected="selectedIds.includes(report.id)"
        @toggle-select="toggleSelect"
        @delete="handleDelete"
      />
    </div>

    <Transition name="cmp-bar">
      <div v-if="selectedIds.length" class="rpt-cmp">
        <span class="rpt-cmp__label">已选 {{ selectedIds.length }} 份（上限 {{ maxCompare }} 份）</span>
        <div class="rpt-cmp__actions">
          <button type="button" class="rpt-cmp__btn rpt-cmp__btn--clr" @click="clearSelection">清除</button>
          <button type="button" class="rpt-cmp__btn rpt-cmp__btn--go" :disabled="selectedIds.length < 2" @click="openCompare">对比分析</button>
        </div>
      </div>
    </Transition>

    <ReportCompareModal :open="compareOpen" :data="compareData" :loading="compareLoading" @close="compareOpen = false" />
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import ReportFilterBar from '../components/ReportFilterBar.vue'
import ReportCard from '../components/ReportCard.vue'
import ReportCompareModal from '../components/ReportCompareModal.vue'
import { useReportHistory } from '../composables/useReportHistory.js'
import { getCurrentSubjectId } from '../stores/storage.js'

const { reports, users, userProfile, loading, error, fetchUsers, fetchUserProfile, fetchReports, deleteReport, compareReports } = useReportHistory()

const userId = ref(getCurrentSubjectId() || '')
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

<style scoped>
.rpt-page {
  max-width: 1080px;
  margin: 0 auto;
  padding: 32px 40px 48px;
}
.rpt-hd__eyebrow {
  font-size: 12px;
  font-weight: 500;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin: 0 0 4px;
}
.rpt-hd__title {
  font-size: 24px;
  font-weight: 600;
  color: #0f172a;
  letter-spacing: -0.02em;
  margin: 0;
}
.rpt-divider {
  border: none;
  border-top: 1px solid rgba(0,0,0,0.06);
  margin: 20px 0 24px;
}
.rpt-err { font-size: 14px; color: #dc2626; margin: 0 0 16px; }
.rpt-state { font-size: 14px; color: #94a3b8; padding: 32px 0; }
.rpt-state--empty { text-align: center; }

.rpt-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

.rpt-cmp {
  position: sticky;
  bottom: 20px;
  margin-top: 24px;
  background: #fff;
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 10px;
  padding: 14px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.rpt-cmp__label { font-size: 13px; color: #475569; font-weight: 500; }
.rpt-cmp__actions { display: flex; gap: 8px; }
.rpt-cmp__btn {
  border: none;
  padding: 8px 22px;
  border-radius: 7px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, opacity 0.15s;
}
.rpt-cmp__btn--clr { background: #f1f5f9; color: #475569; }
.rpt-cmp__btn--clr:hover { background: #e2e8f0; }
.rpt-cmp__btn--go { background: #2563eb; color: #fff; }
.rpt-cmp__btn--go:hover:not(:disabled) { background: #1d4ed8; }
.rpt-cmp__btn--go:disabled { opacity: 0.45; cursor: not-allowed; }

.cmp-bar-enter-active, .cmp-bar-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.cmp-bar-enter-from, .cmp-bar-leave-to { opacity: 0; transform: translateY(8px); }
</style>
