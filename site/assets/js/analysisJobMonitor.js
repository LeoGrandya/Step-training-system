/** 运行时必需（legacy）。分析任务轮询：进度、完成跳转、取消态。 */
(function () {
  var ACTIVE_KEY = 'ai_sport_lab.active_analysis';
  var GUARD_KEY = 'ai_sport_lab.analysis_guard';
  var GUARD_SUBMITTING = 'submitting';
  var DEFAULT_ETA_SEC = 30;
  var POLL_MS = 2000;

  function normalizeProgress(raw) {
    var value = Number(raw);
    if (!Number.isFinite(value)) return 0;
    if (value <= 1) return Math.round(Math.max(0, Math.min(1, value)) * 100);
    return Math.round(Math.max(0, Math.min(100, value)));
  }

  function readActiveJob() {
    try {
      var raw = window.sessionStorage.getItem(ACTIVE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (error) {
      return null;
    }
  }

  function writeActiveJob(data) {
    try {
      window.sessionStorage.setItem(ACTIVE_KEY, JSON.stringify(data));
    } catch (error) {
      // ignore
    }
  }

  function clearActiveJob() {
    try {
      window.sessionStorage.removeItem(ACTIVE_KEY);
    } catch (error) {
      // ignore
    }
  }

  function setSubmittingGuard() {
    try {
      window.sessionStorage.setItem(GUARD_KEY, GUARD_SUBMITTING);
    } catch (error) {
      // ignore
    }
  }

  function clearAnalysisGuard() {
    try {
      window.sessionStorage.removeItem(GUARD_KEY);
    } catch (error) {
      // ignore
    }
  }

  function isSubmittingGuard() {
    try {
      return window.sessionStorage.getItem(GUARD_KEY) === GUARD_SUBMITTING;
    } catch (error) {
      return false;
    }
  }

  function resolveEstimatedTotal(job, etaHint) {
    var hint = Number(etaHint);
    if (Number.isFinite(hint) && hint > 0) return hint;
    var fromMeta = job && job.meta && Number(job.meta.estimated_duration_s);
    if (Number.isFinite(fromMeta) && fromMeta > 0) return fromMeta;
    return DEFAULT_ETA_SEC;
  }

  function formatEtaText(job, progressPct, estimatedTotalSec) {
    if (job.status === 'done') return '分析完成';
    if (job.status === 'error' || job.status === 'failed') return '分析失败';
    if (progressPct >= 99) return '即将完成…';
    var remainingSec = Math.max(0, Math.ceil(estimatedTotalSec * (1 - progressPct / 100)));
    return remainingSec > 0 ? '预计还需 ' + remainingSec + ' 秒' : '即将完成…';
  }

  function isRunningStatus(status) {
    return status === 'queued' || status === 'running';
  }

  function createAnalysisJobMonitor(options) {
    options = options || {};
    var pollTimer = null;
    var cancelled = false;
    var jobId = options.jobId || '';
    var fileLabel = options.fileLabel || '分析任务';
    var estimatedTotalSec = resolveEstimatedTotal(null, options.eta);
    var stageLabelFn = options.stageLabelFn;

    function persistActive() {
      writeActiveJob({
        jobId: jobId,
        fileLabel: fileLabel,
        eta: estimatedTotalSec,
      });
    }

    function emitUpdate(job) {
      if (cancelled) return;
      var progressPct = normalizeProgress(job.progress);
      estimatedTotalSec = resolveEstimatedTotal(job, estimatedTotalSec);
      var statusText = job.message
        || (stageLabelFn && stageLabelFn(job.stage))
        || '分析进行中...';
      var etaText = formatEtaText(job, progressPct, estimatedTotalSec);
      if (options.onUpdate) {
        options.onUpdate({
          job: job,
          progressPct: progressPct,
          statusText: statusText,
          etaText: etaText,
          fileLabel: fileLabel,
        });
      }
    }

    async function pollOnce() {
      if (!jobId || cancelled) return;
      try {
        var response = await fetch('/api/analysis/jobs/' + encodeURIComponent(jobId));
        var job = await response.json().catch(function () { return {}; });
        if (cancelled) return;
        if (!response.ok) {
          throw new Error((job && job.error) || '查询任务失败');
        }
        emitUpdate(job);
        if (cancelled) return;
        if (job.status === 'done') {
          stop();
          clearActiveJob();
          if (options.onDone) options.onDone(job);
        } else if (job.status === 'error' || job.status === 'failed') {
          stop();
          clearActiveJob();
          if (options.onError) options.onError(job.message || job.error || '分析失败', job);
        }
      } catch (error) {
        if (cancelled) return;
        stop();
        clearActiveJob();
        if (options.onError) options.onError(error.message || '轮询失败', null);
      }
    }

    function start() {
      stop();
      cancelled = false;
      persistActive();
      pollOnce();
      pollTimer = window.setInterval(pollOnce, POLL_MS);
    }

    function stop() {
      cancelled = true;
      if (pollTimer) {
        window.clearInterval(pollTimer);
        pollTimer = null;
      }
    }

    return {
      start: start,
      stop: stop,
      pollOnce: pollOnce,
      getJobId: function () { return jobId; },
    };
  }

  window.AnalysisJobMonitor = {
    ACTIVE_KEY: ACTIVE_KEY,
    GUARD_KEY: GUARD_KEY,
    GUARD_SUBMITTING: GUARD_SUBMITTING,
    DEFAULT_ETA_SEC: DEFAULT_ETA_SEC,
    POLL_MS: POLL_MS,
    normalizeProgress: normalizeProgress,
    readActiveJob: readActiveJob,
    writeActiveJob: writeActiveJob,
    clearActiveJob: clearActiveJob,
    setSubmittingGuard: setSubmittingGuard,
    clearAnalysisGuard: clearAnalysisGuard,
    isSubmittingGuard: isSubmittingGuard,
    resolveEstimatedTotal: resolveEstimatedTotal,
    formatEtaText: formatEtaText,
    isRunningStatus: isRunningStatus,
    createAnalysisJobMonitor: createAnalysisJobMonitor,
  };
})();
