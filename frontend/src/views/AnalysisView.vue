<!-- 运行时必需。视频分析页：双机位上传 + 参数配置 + 进度面板 + 最近分析。 -->
<template>
  <section class="page-stack analysis-page">
    <header class="analysis-header">
      <h1>双目视频分析</h1>
      <div class="analysis-header__meta">
        <p v-if="currentUserName" class="analysis-header__user">当前用户：{{ currentUserName }}</p>
        <RouterLink to="/report-history" class="analysis-header__history-link">历史报告 &rarr;</RouterLink>
      </div>
    </header>

    <p v-if="pageError" class="analysis-page__error">{{ pageError }}</p>

    <div class="analysis-layout">
      <div class="analysis-layout__upload">
        <div class="analysis-upload-grid">
          <AnalysisUploadZone
            v-model="leftFile"
            camera="left"
            accept="video/*"
          />
          <AnalysisUploadZone
            v-model="rightFile"
            camera="right"
            accept="video/*"
          />
        </div>

        <div class="analysis-calibration-field">
          <span class="analysis-calibration__label">标定文件（可选）</span>
          <div
            class="analysis-calibration__zone"
            :class="{ 'analysis-calibration__zone--has-file': stereoFile, 'analysis-calibration__zone--dragover': stereoDragOver }"
            @dragover.prevent="stereoDragOver = true"
            @dragleave.prevent="stereoDragOver = false"
            @drop.prevent="onStereoDrop"
          >
            <input
              ref="stereoInput"
              type="file"
              accept=".json,application/json"
              class="upload-zone__input"
              @change="onStereoFileChange"
            />
            <span v-if="!stereoFile" class="analysis-calibration__hint" @click="stereoInput?.click()">
              拖放或点击选择标定 JSON 文件
            </span>
            <span v-else class="analysis-calibration__file">
              <span class="analysis-calibration__file-name">{{ stereoFile.name }}</span>
              <button type="button" class="upload-zone__clear" @click.stop="clearStereo" aria-label="清除">&times;</button>
            </span>
          </div>
        </div>

        <AnalysisProgressPanel
          :phase="job.phase.value"
          :progress="job.progress.value"
          :statusText="job.statusText.value"
          :etaText="job.etaText.value"
          :fileLabel="job.fileLabel.value"
          @cancel="handleCancel"
        />

        <div v-if="job.phase.value === 'done'" class="analysis-submit-row">
          <button class="analysis-submit-button" @click="goToReport">查看分析报告</button>
        </div>

        <div v-if="job.phase.value === 'idle'" class="analysis-submit-row">
          <button
            class="analysis-submit-button"
            :disabled="!canSubmit || upload.submitting.value"
            @click="handleStart"
          >{{ upload.submitting.value ? '提交中...' : '开始分析' }}</button>
          <p v-if="upload.submitError.value" class="analysis-submit-error">{{ upload.submitError.value }}</p>
        </div>

        <div v-if="job.phase.value === 'error'" class="analysis-submit-row">
          <p class="analysis-submit-error">分析失败：{{ job.statusText.value }}</p>
          <button class="secondary-button" @click="job.reset()">重新开始</button>
        </div>
      </div>

      <aside class="analysis-layout__side">
        <AnalysisParamsPanel
          :stepDisplayName="stepDisplayName"
          @update:stepDisplayName="stepDisplayName = $event"
        />
        <AnalysisRecentList />
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
import { saveTrainingMode, getTrainingMode, saveCurrentJobId, getCurrentUserId } from '../stores/storage.js'

const router = useRouter()
const upload = useAnalysisUpload()
const job = useAnalysisJob()

const leftFile = ref(null)
const rightFile = ref(null)
const stereoFile = ref(null)
const stereoDragOver = ref(false)
const stereoInput = ref(null)
const stepDisplayName = ref('')
const currentUserName = ref('')
const pageError = ref('')
const analysisGeneration = ref(0)

let leaveGuardHandler = null

const canSubmit = computed(() => leftFile.value && rightFile.value && !upload.submitting.value)

function enableLeaveGuard() {
  leaveGuardHandler = (e) => {
    e.preventDefault()
    e.returnValue = ''
  }
  window.addEventListener('beforeunload', leaveGuardHandler)
}

function disableLeaveGuard() {
  if (leaveGuardHandler) {
    window.removeEventListener('beforeunload', leaveGuardHandler)
    leaveGuardHandler = null
  }
}

function fetchUserName() {
  try {
    const raw = window.sessionStorage.getItem('pp-current-user')
    if (raw) {
      const u = JSON.parse(raw)
      currentUserName.value = u.name || ''
    }
  } catch {}
}

async function ensureUser() {
  try {
    const response = await fetch('/api/users')
    const payload = await response.json().catch(() => ({}))
    if (!response.ok || !payload.ok || !payload.items?.length) return false

    let userId = getCurrentUserId()
    const valid = userId && payload.items.some(u => u.id === userId)
    if (!valid) {
      userId = payload.items[0].id
      window.sessionStorage.setItem('pp-current-user-id', userId)
    }

    const user = payload.items.find(u => u.id === userId)
    if (user) {
      currentUserName.value = user.name || ''
      window.sessionStorage.setItem('pp-current-user', JSON.stringify(user))
    }
    return true
  } catch {
    return false
  }
}

async function handleStart() {
  if (!canSubmit.value) return

  const gen = ++analysisGeneration.value

  saveTrainingMode(getTrainingMode() || 'eval')

  setSubmittingGuard()
  enableLeaveGuard()

  try {
    const payload = await upload.submit(leftFile.value, rightFile.value, stereoFile.value, {
      trainingMode: getTrainingMode() || 'eval',
      analysisProfile: 'fast',
      stepDisplayName: stepDisplayName.value,
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
})

onUnmounted(() => {
  disableLeaveGuard()
})
</script>
