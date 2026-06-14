<!-- 运行时必需。视频分析页：Linear 风格，双机位上传 + 参数配置 + 进度 + 最近分析。 -->
<template>
  <section class="analysis-page" :class="{ 'analysis-page--active': job.phase.value !== 'idle' }">
    <!-- 页头 -->
    <header class="analysis-hd analysis-header">
      <div>
        <p class="analysis-hd__eyebrow">Step Training</p>
        <h1 class="analysis-hd__title">双目视频分析</h1>
      </div>
      <div class="analysis-hd__rhs analysis-header__meta">
        <span v-if="currentUserName" class="analysis-hd__user analysis-header__user">当前用户：{{ currentUserName }}</span>
        <RouterLink to="/report-history" class="analysis-hd__history analysis-header__history-link">历史报告 &rarr;</RouterLink>
      </div>
    </header>

    <hr class="analysis-divider" />

    <p v-if="pageError" class="analysis-error">{{ pageError }}</p>

    <div class="analysis-body">
      <!-- 左侧：上传 + 进度 + 操作 -->
      <main class="analysis-main">
        <!-- 双机位上传网格 -->
        <div class="analysis-stereo-grid analysis-upload-grid">
          <div class="analysis-stereo-cell">
            <AnalysisUploadZone v-model="leftFile" camera="left" accept="video/*" />
          </div>
          <div class="analysis-stereo-connector" aria-hidden="true">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.5"><line x1="4" y1="12" x2="20" y2="12"/><circle cx="12" cy="12" r="3"/></svg>
          </div>
          <div class="analysis-stereo-cell">
            <AnalysisUploadZone v-model="rightFile" camera="right" accept="video/*" />
          </div>
        </div>

        <!-- 标定文件标签 -->
        <div class="analysis-calib analysis-calibration-field">
          <span class="analysis-calib__label analysis-calibration__label">标定文件</span>
          <div class="analysis-calib__ctrl" :class="{ 'analysis-calib__ctrl--has': stereoFile, 'analysis-calib__ctrl--over': stereoDragOver }"
            @dragover.prevent="stereoDragOver = true"
            @dragleave.prevent="stereoDragOver = false"
            @drop.prevent="onStereoDrop"
          >
            <input ref="stereoInput" type="file" accept=".json,application/json" class="analysis-calib__input" @change="onStereoFileChange" />
            <span v-if="!stereoFile" class="analysis-calib__placeholder" @click="stereoInput?.click()">拖放或点击选择 JSON 标定文件</span>
            <span v-else class="analysis-calib__file">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              {{ stereoFile.name }}
              <button type="button" class="analysis-calib__clear" @click.stop="clearStereo">&times;</button>
            </span>
          </div>
        </div>

        <!-- 进度 -->
        <AnalysisProgressPanel
          :phase="job.phase.value"
          :progress="job.progress.value"
          :statusText="job.statusText.value"
          :etaText="job.etaText.value"
          :fileLabel="job.fileLabel.value"
          @cancel="handleCancel"
        />

        <!-- 操作按钮 -->
        <div v-if="job.phase.value === 'done'" class="analysis-action analysis-submit-row">
          <button class="analysis-action__btn analysis-action__btn--outline" @click="goToReport">查看分析报告</button>
        </div>

        <div v-if="job.phase.value === 'idle'" class="analysis-action analysis-submit-row">
          <button class="analysis-action__btn analysis-action__btn--primary analysis-submit-button"
            :disabled="!canSubmit || upload.submitting.value"
            @click="handleStart">
            {{ upload.submitting.value ? '提交中...' : '开始分析' }}
          </button>
          <p v-if="upload.submitError.value" class="analysis-action__err analysis-submit-error">{{ upload.submitError.value }}</p>
        </div>

        <div v-if="job.phase.value === 'error'" class="analysis-action analysis-submit-row">
          <p class="analysis-action__err">分析失败：{{ job.statusText.value }}</p>
          <button class="analysis-action__btn analysis-action__btn--outline" @click="job.reset()">重新开始</button>
        </div>
      </main>

      <!-- 右侧：参数 + 最近列表 -->
      <aside class="analysis-side">
        <div class="analysis-side-card">
          <AnalysisParamsPanel
            :stepDisplayName="stepDisplayName"
            :trainingConfigId="trainingConfigId"
            :analysisProfile="analysisProfile"
            :trainingMode="trainingMode"
            @update:stepDisplayName="stepDisplayName = $event"
            @update:trainingConfigId="trainingConfigId = $event"
          />
        </div>
        <div class="analysis-side-card">
          <AnalysisRecentList />
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AnalysisUploadZone from '../components/AnalysisUploadZone.vue'
import AnalysisParamsPanel from '../components/AnalysisParamsPanel.vue'
import AnalysisRecentList from '../components/AnalysisRecentList.vue'
import AnalysisProgressPanel from '../components/AnalysisProgressPanel.vue'
import { useAnalysisUpload } from '../composables/useAnalysisUpload.js'
import {
  useAnalysisJob,
  setSubmittingGuard,
  clearAnalysisGuard,
} from '../composables/useAnalysisJob.js'
import { saveTrainingMode, getTrainingMode, saveCurrentJobId, getCurrentUserId, getCurrentSubjectId, setCurrentSubjectId } from '../stores/storage.js'

const router = useRouter()
const upload = useAnalysisUpload()
const job = useAnalysisJob()

const leftFile = ref(null)
const rightFile = ref(null)
const stereoFile = ref(null)
const stereoDragOver = ref(false)
const stereoInput = ref(null)
const stepDisplayName = ref('')
const trainingConfigId = ref('')
const analysisProfile = ref('快速')
const trainingMode = ref(getTrainingMode() || '练习评估')
const currentUserName = ref('')
const pageError = ref('')
const analysisGeneration = ref(0)

let leaveGuardHandler = null

const canSubmit = computed(() => leftFile.value && rightFile.value && !upload.submitting.value)

function enableLeaveGuard() {
  leaveGuardHandler = (e) => { e.preventDefault(); e.returnValue = '' }
  window.addEventListener('beforeunload', leaveGuardHandler)
}

function disableLeaveGuard() {
  if (leaveGuardHandler) { window.removeEventListener('beforeunload', leaveGuardHandler); leaveGuardHandler = null }
}

async function ensureUser() {
  // 从全局受试者状态读取，顶栏切换即生效
  let subjectId = getCurrentSubjectId()

  // 如果没有选中受试者，自动拉取列表取第一个
  if (!subjectId) {
    try {
      const listRes = await fetch('/api/v1/subjects?limit=1')
      if (!listRes.ok) return false
      const listPayload = await listRes.json().catch(() => ({}))
      const first = (listPayload.items || [])[0]
      if (!first) return false
      subjectId = first.id
      setCurrentSubjectId(subjectId)
    } catch {
      return false
    }
  }

  try {
    const response = await fetch(`/api/users/${encodeURIComponent(subjectId)}`)
    const payload = await response.json().catch(() => ({}))
    if (!response.ok || !payload.ok) return false
    currentUserName.value = payload.user?.name || ''
    window.sessionStorage.setItem('pp-current-user', JSON.stringify(payload.user || {}))
    return true
  } catch {
    return false
  }
}

async function handleStart() {
  if (!canSubmit.value) return

  const gen = ++analysisGeneration.value

  trainingMode.value = getTrainingMode() || trainingMode.value || '练习评估'
  saveTrainingMode(trainingMode.value)

  setSubmittingGuard()
  enableLeaveGuard()

  try {
    const payload = await upload.submit(leftFile.value, rightFile.value, stereoFile.value, {
      trainingMode: trainingMode.value,
      analysisProfile: analysisProfile.value,
      trainingConfigId: trainingConfigId.value,
      stepDisplayName: stepDisplayName.value,
      userId: getCurrentSubjectId() || getCurrentUserId(),
      fps: 60,
    })

    if (gen !== analysisGeneration.value) return
    clearAnalysisGuard()
    disableLeaveGuard()

    const label = leftFile.value.name + ' + ' + rightFile.value.name
    const eta = payload.estimatedDurationSeconds != null ? payload.estimatedDurationSeconds : ''
    saveCurrentJobId(payload.jobId)
    job.start(payload.jobId, label, eta)
  } catch (error) {
    if (gen !== analysisGeneration.value) return
    clearAnalysisGuard()
    disableLeaveGuard()
    if (error && error.name === 'AbortError') return
  }
}

function handleCancel() {
  analysisGeneration.value++
  upload.cancelSubmit()
  upload.markJobCancelled(job.jobId.value)
  job.cancelJob()
}

function goToReport() {
  const jid = job.jobId.value
  if (jid) router.push('/report/' + encodeURIComponent(jid))
}

function onStereoDrop(e) {
  stereoDragOver.value = false
  const files = e.dataTransfer?.files
  if (!files || !files.length) return
  const jsonFile = files[0]
  stereoFile.value = jsonFile
}

function onStereoFileChange(e) {
  stereoFile.value = e.target.files?.[0] || null
}

function clearStereo() {
  stereoFile.value = null
  if (stereoInput.value) stereoInput.value.value = ''
}

function fetchUserName() {
  try {
    const raw = window.sessionStorage.getItem('pp-current-user')
    if (!raw) return
    const user = JSON.parse(raw)
    currentUserName.value = user?.name || user?.displayName || ''
  } catch {
    currentUserName.value = ''
  }
}

onMounted(async () => {
  document.documentElement.dataset.pageReady = 'analysis'
  fetchUserName()

  // 确保有可用用户（注册/登录），失败则阻断操作
  const ok = await ensureUser()
  if (!ok) {
    pageError.value = '用户加载失败，请确保已登录'
    return
  }

  // 恢复刷新前的活跃分析任务，避免页面重载后丢失进度
  const restored = await job.restoreActiveJobIfAny()
  if (!restored) job.reset()

  window.addEventListener('subject-changed', onSubjectChanged)
})

function onSubjectChanged(e) {
  currentUserName.value = e.detail?.name || ''
  leftFile.value = null
  rightFile.value = null
  stereoFile.value = null
  trainingMode.value = getTrainingMode() || trainingMode.value || '练习评估'
  saveTrainingMode(trainingMode.value)
}

onUnmounted(() => {
  disableLeaveGuard()
  window.removeEventListener('subject-changed', onSubjectChanged)
})
</script>

<style scoped>
.analysis-page {
  max-width: 1080px;
  margin: 0 auto;
  padding: 32px 40px 48px;
}

/* ===== 页头 ===== */
.analysis-hd {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}
.analysis-hd__eyebrow {
  font-size: 12px;
  font-weight: 500;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin: 0 0 4px;
}
.analysis-hd__title {
  font-size: 24px;
  font-weight: 600;
  color: #0f172a;
  letter-spacing: -0.02em;
  margin: 0;
}
.analysis-hd__rhs {
  display: flex;
  align-items: center;
  gap: 16px;
}
.analysis-hd__user {
  font-size: 13px;
  color: #64748b;
}
.analysis-hd__history {
  font-size: 13px;
  color: #2563eb;
  text-decoration: none;
  font-weight: 500;
  transition: opacity 0.15s;
}
.analysis-hd__history:hover { opacity: 0.7; }

/* ===== 分割线 ===== */
.analysis-divider {
  border: none;
  border-top: 1px solid rgba(0,0,0,0.06);
  margin: 20px 0 28px;
}

.analysis-error {
  font-size: 14px;
  color: #dc2626;
  margin: 0 0 16px;
}

/* ===== 主体 ===== */
.analysis-body {
  display: grid;
  grid-template-columns: 1fr 240px;
  gap: 24px;
  align-items: start;
}

.analysis-main {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

/* ===== 双目上传网格 ===== */
.analysis-stereo-grid {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 0;
  align-items: center;
}
.analysis-stereo-cell {
  min-width: 0;
}
.analysis-stereo-connector {
  padding: 0 12px;
  display: flex;
  align-items: center;
  opacity: 0.35;
}

/* ===== 标定文件 ===== */
.analysis-calib {
  display: flex;
  align-items: center;
  gap: 12px;
}
.analysis-calib__label {
  font-size: 12px;
  font-weight: 500;
  color: #94a3b8;
  white-space: nowrap;
}
.analysis-calib__ctrl {
  flex: 1;
  background: #fff;
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 8px;
  padding: 10px 14px;
  transition: border-color 0.15s, box-shadow 0.15s;
  cursor: pointer;
}
.analysis-calib__ctrl:hover { border-color: rgba(0,0,0,0.12); }
.analysis-calib__ctrl--over { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,0.06); }
.analysis-calib__ctrl--has { background: #f8fafc; }
.analysis-calib__input { display: none; }
.analysis-calib__placeholder {
  font-size: 13px;
  color: #94a3b8;
}
.analysis-calib__file {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
}
.analysis-calib__clear {
  margin-left: 8px;
  border: none;
  background: transparent;
  font-size: 18px;
  color: #94a3b8;
  cursor: pointer;
  line-height: 1;
}
.analysis-calib__clear:hover { color: #dc2626; }

/* ===== 操作按钮 ===== */
.analysis-action {
  margin-top: 4px;
  display: flex;
  justify-content: center;
}
.analysis-action__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 12px 36px;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: background 0.15s, box-shadow 0.15s, opacity 0.15s;
  letter-spacing: 0.01em;
}
.analysis-action__btn--primary {
  background: #2563eb;
  color: #fff;
  box-shadow: 0 2px 8px rgba(37,99,235,0.2);
}
.analysis-action__btn--primary:hover:not(:disabled) {
  background: #1d4ed8;
  box-shadow: 0 4px 14px rgba(37,99,235,0.28);
}
.analysis-action__btn--primary:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: none;
}
.analysis-action__btn--outline {
  background: #fff;
  color: #2563eb;
  border: 1px solid rgba(0,0,0,0.08);
}
.analysis-action__btn--outline:hover {
  background: #f8fafc;
}
.analysis-action__err {
  font-size: 13px;
  color: #dc2626;
  margin: 8px 0 0;
}

/* ===== 右侧栏 ===== */
.analysis-side {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.analysis-side-card {
  background: #fff;
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 10px;
  padding: 16px;
}
</style>
