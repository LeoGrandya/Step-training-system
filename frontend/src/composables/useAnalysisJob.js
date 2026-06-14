/** 分析任务轮询：进度追踪、完成跳转、取消。 */
import { ref, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const ACTIVE_KEY = 'ai_sport_lab.active_analysis'
const GUARD_KEY = 'ai_sport_lab.analysis_guard'
const GUARD_SUBMITTING = 'submitting'
const DEFAULT_ETA_SEC = 30
const POLL_MS = 2000

export { ACTIVE_KEY, GUARD_KEY, GUARD_SUBMITTING }

// 后端返回的进度可能是 0.0-1.0 或 0-100，统一归一化为 0-100 整数
export function normalizeProgress(raw) {
  const value = Number(raw)
  if (!Number.isFinite(value)) return 0
  if (value <= 1) return Math.round(Math.max(0, Math.min(1, value)) * 100)
  return Math.round(Math.max(0, Math.min(100, value)))
}

export function isRunningStatus(status) {
  return status === 'queued' || status === 'running'
}

export function stageLabel(stage) {
  const labels = {
    upload: '正在上传视频至服务器...',
    sync: '正在进行双机位视频同步...',
    pose3d: '正在提取 3D 姿态关键点...',
    kinematics: '正在计算运动学指标...',
    result: '正在生成生物力学报告...',
    queued: '任务排队中...',
    running: '分析进行中...',
  }
  return labels[stage] || '分析进行中...'
}

export function readActiveJob() {
  try {
    const raw = window.sessionStorage.getItem(ACTIVE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

export function writeActiveJob(data) {
  try { window.sessionStorage.setItem(ACTIVE_KEY, JSON.stringify(data)) } catch {}
}

export function clearActiveJob() {
  try { window.sessionStorage.removeItem(ACTIVE_KEY) } catch {}
}

export function setSubmittingGuard() {
  try { window.sessionStorage.setItem(GUARD_KEY, GUARD_SUBMITTING) } catch {}
}

export function clearAnalysisGuard() {
  try { window.sessionStorage.removeItem(GUARD_KEY) } catch {}
}

function resolveEstimatedTotal(job, etaHint) {
  const hint = Number(etaHint)
  if (Number.isFinite(hint) && hint > 0) return hint
  const fromMeta = job && job.meta && Number(job.meta.estimated_duration_s)
  if (Number.isFinite(fromMeta) && fromMeta > 0) return fromMeta
  return DEFAULT_ETA_SEC
}

function formatEtaText(job, progressPct, estimatedTotalSec) {
  if (job.status === 'done') return '分析完成'
  if (job.status === 'error' || job.status === 'failed') return '分析失败'
  if (progressPct >= 99) return '即将完成…'
  const remainingSec = Math.max(0, Math.ceil(estimatedTotalSec * (1 - progressPct / 100)))
  return remainingSec > 0 ? '预计还需 ' + remainingSec + ' 秒' : '即将完成…'
}

export function useAnalysisJob() {
  const router = useRouter()
  const progress = ref(0)
  const statusText = ref('等待分析...')
  const etaText = ref('正在估算剩余时间…')
  const fileLabel = ref('')
  // 页面状态机：idle(等待) → submitting(上传中) → running(分析中) → done(完成) | error(失败)
  const phase = ref('idle')
  const jobId = ref('')

  let pollTimer = null
  let cancelled = false
  let estimatedTotalSec = DEFAULT_ETA_SEC
  let currentFileLabel = '分析任务'

  function emitUpdate(job) {
    if (cancelled) return
    const progressPct = normalizeProgress(job.progress)
    estimatedTotalSec = resolveEstimatedTotal(job, estimatedTotalSec)
    progress.value = progressPct
    statusText.value = job.message || stageLabel(job.stage)
    etaText.value = formatEtaText(job, progressPct, estimatedTotalSec)
    fileLabel.value = currentFileLabel
  }

  async function pollOnce() {
    if (!jobId.value || cancelled) return
    try {
      const response = await fetch('/api/analysis/jobs/' + encodeURIComponent(jobId.value))
      if (cancelled) return
      if (!response.ok) {
        const text = await response.text().catch(() => '')
        throw new Error(text || `查询任务失败 (HTTP ${response.status})`)
      }
      const job = await response.json().catch(() => ({}))
      emitUpdate(job)
      if (cancelled) return
      if (job.status === 'done') {
        stop()
        clearActiveJob()
        phase.value = 'done'
      } else if (job.status === 'error' || job.status === 'failed') {
        stop()
        clearActiveJob()
        phase.value = 'error'
        statusText.value = job.message || job.error || '分析失败'
      }
    } catch (error) {
      if (cancelled) return
      stop()
      clearActiveJob()
      phase.value = 'error'
      statusText.value = error.message || '轮询失败'
    }
  }

  function start(jid, label, eta) {
    stop()
    cancelled = false
    jobId.value = jid
    currentFileLabel = label || '分析任务'
    fileLabel.value = currentFileLabel
    estimatedTotalSec = resolveEstimatedTotal(null, eta)
    phase.value = 'running'
    progress.value = 0
    statusText.value = '任务已创建，等待分析...'
    etaText.value = '正在估算剩余时间…'

    writeActiveJob({ jobId: jid, fileLabel: currentFileLabel, eta: estimatedTotalSec })
    pollOnce()
    pollTimer = window.setInterval(pollOnce, POLL_MS)
  }

  function stop() {
    cancelled = true
    if (pollTimer) {
      window.clearInterval(pollTimer)
      pollTimer = null
    }
  }

  async function cancelJob() {
    const jid = jobId.value
    if (!jid) return
    stop()
    clearActiveJob()
    phase.value = 'idle'
    try {
      await fetch('/api/analysis/jobs/' + encodeURIComponent(jid) + '/cancel', { method: 'POST' })
    } catch {}
  }

  function reset() {
    stop()
    clearActiveJob()
    phase.value = 'idle'
    progress.value = 0
    statusText.value = '等待分析...'
    etaText.value = '正在估算剩余时间…'
    fileLabel.value = ''
    jobId.value = ''
  }

  // 页面刷新/重新进入时恢复未完成的分析任务，保持进度条连续性
  async function restoreActiveJobIfAny() {
    const active = readActiveJob()
    if (!active || !active.jobId) return false

    try {
      const response = await fetch('/api/analysis/jobs/' + encodeURIComponent(active.jobId))
      const job = await response.json().catch(() => ({}))
      if (!response.ok || !isRunningStatus(job.status)) {
        clearActiveJob()
        return false
      }
      start(active.jobId, active.fileLabel || '分析任务', active.eta)
      return true
    } catch {
      clearActiveJob()
      return false
    }
  }

  onUnmounted(() => { stop() })

  return {
    progress,
    statusText,
    etaText,
    fileLabel,
    phase,
    jobId,
    start,
    stop,
    cancelJob,
    reset,
    restoreActiveJobIfAny,
  }
}
