/** 分析上传：FormData 构建、提交、取消。 */
import { ref } from 'vue'
import { createAnalysisJob } from '../services/api.js'
import { getCurrentUserId } from '../stores/storage.js'
import { getTrainingMode, getProfile } from '../stores/storage.js'

export function useAnalysisUpload() {
  const submitting = ref(false)
  const submitError = ref('')
  let submitAbortController = null
  let lastCancelledJobId = null

  function buildFormData(leftFile, rightFile, stereoFile, params = {}) {
    const formData = new FormData()
    formData.append('left_video', leftFile)
    formData.append('right_video', rightFile)
    formData.append('fps', String(params.fps || 60))
    formData.append('user_id', params.userId || getCurrentUserId())
    formData.append('training_mode', params.trainingMode || getTrainingMode() || 'eval')
    formData.append('profile_json', new Blob(
      [JSON.stringify(params.profileJson || getProfile())],
      { type: 'application/json' }
    ))
    if (params.analysisProfile) {
      formData.append('analysis_profile', params.analysisProfile)
    }
    if (params.trainingConfigId) {
      formData.append('training_config_id', params.trainingConfigId)
    }
    if (params.stepDisplayName) {
      formData.append('step_display_name', params.stepDisplayName)
    }
    if (stereoFile) {
      formData.append('stereo_params_matlab_json', stereoFile)
    }
    return formData
  }

  async function submit(leftFile, rightFile, stereoFile, params = {}) {
    if (submitAbortController) {
      submitAbortController.abort()
    }
    submitAbortController = new AbortController()
    submitting.value = true
    submitError.value = ''

    try {
      const formData = buildFormData(leftFile, rightFile, stereoFile, params)
      const payload = await createAnalysisJob(formData)
      return payload
    } catch (error) {
      if (error && error.name === 'AbortError') return null
      submitError.value = error.message || '提交失败'
      throw error
    } finally {
      submitting.value = false
      submitAbortController = null
    }
  }

  function cancelSubmit() {
    if (submitAbortController) {
      submitAbortController.abort()
      submitAbortController = null
    }
  }

  function markJobCancelled(jobId) {
    lastCancelledJobId = jobId
  }

  function isCancelledJob(job) {
    if (!job) return false
    const jobId = job.job_id || job.jobId || ''
    if (lastCancelledJobId && jobId === lastCancelledJobId) return true
    return job.error_code === 'CANCELLED'
  }

  return { submitting, submitError, submit, cancelSubmit, markJobCancelled, isCancelledJob }
}
