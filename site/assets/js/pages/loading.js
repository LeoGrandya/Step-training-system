(function () {
  function getQueryParam(name) {
    var search = (window.top || window).location.search || window.location.search || '';
    var hashQuery = '';
    var hash = (window.top || window).location.hash || window.location.hash || '';
    var qIndex = hash.indexOf('?');
    if (qIndex >= 0) hashQuery = hash.slice(qIndex);
    var params = new URLSearchParams(search || hashQuery);
    return params.get(name);
  }

  var monitor = null;

  function updateUi(payload) {
    var progressBar = window.App.qs('#loading-progress');
    var percentText = window.App.qs('#loading-percent');
    var statusText = window.App.qs('#loading-status');
    var fileLabelEl = window.App.qs('#loading-filename');
    var etaEl = window.App.qs('#loading-eta');

    if (fileLabelEl) fileLabelEl.textContent = payload.fileLabel;
    if (progressBar) progressBar.style.width = payload.progressPct + '%';
    if (percentText) percentText.textContent = payload.progressPct + '%';
    if (statusText) statusText.textContent = payload.statusText;
    if (etaEl) etaEl.textContent = payload.etaText;
  }

  function cancelAnalysis() {
    if (monitor) monitor.stop();
    window.AnalysisJobMonitor.clearActiveJob();
    window.App.showToast('已取消分析', 'warn');
    window.setTimeout(function () {
      (window.top || window).location.href = '/#/analysis';
    }, 800);
  }

  function startAnalysis() {
    var jobId = getQueryParam('jobId') || window.localStorage.getItem('ai_sport_lab.current_job_id') || '';
    var fileLabel = getQueryParam('file') || '分析任务';
    var eta = getQueryParam('eta');

    if (!jobId) {
      window.App.showToast('缺少任务 ID，请重新上传视频', 'warn');
      window.setTimeout(function () {
        (window.top || window).location.href = '/#/analysis';
      }, 1200);
      return;
    }

    monitor = window.AnalysisJobMonitor.createAnalysisJobMonitor({
      jobId: jobId,
      fileLabel: fileLabel,
      eta: eta,
      stageLabelFn: window.AnalysisLegacy && window.AnalysisLegacy.stageLabel,
      onUpdate: updateUi,
      onDone: function () {
        var statusText = window.App.qs('#loading-status');
        if (statusText) {
          statusText.textContent = '分析完成，正在跳转...';
          statusText.style.color = '#10B981';
        }
        updateUi({
          fileLabel: fileLabel,
          progressPct: 100,
          statusText: '分析完成，正在跳转...',
          etaText: '分析完成，正在跳转…',
        });
        window.setTimeout(function () {
          (window.top || window).location.href = '/#/report/' + encodeURIComponent(jobId);
        }, 1200);
      },
      onError: function (message) {
        window.App.showToast(message || '分析失败', 'error');
        window.setTimeout(function () {
          (window.top || window).location.href = '/#/analysis';
        }, 1500);
      },
    });

    updateUi({
      fileLabel: fileLabel,
      progressPct: 0,
      statusText: '任务已创建，等待分析...',
      etaText: '正在估算剩余时间…',
    });
    monitor.start();
  }

  window.App.onReady(function () {
    document.documentElement.dataset.pageReady = 'loading';
    startAnalysis();
  });

  window.cancelAnalysis = cancelAnalysis;
})();
