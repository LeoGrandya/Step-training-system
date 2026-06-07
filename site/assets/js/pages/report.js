(function () {
  var globalChartOpt = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: { legend: { position: 'bottom', labels: { font: { size: 11, weight: 'bold' } } } }
  };

  var reportPayload = null;
  var muscleJointsData = [];
  var scene;
  var camera;
  var renderer;
  var humanGroup;
  var raycaster;
  var mouseVec;
  var interactiveJoints = [];
  var muscleReady = false;

  function getJobId() {
    var search = window.location.search || '';
    var params = new URLSearchParams(search);
    var fromQuery = params.get('jobId');
    if (fromQuery) return fromQuery;
    try {
      var topHash = (window.top || window).location.hash || '';
      var reportMatch = topHash.match(/#\/report\/([^/?]+)/);
      if (reportMatch) return decodeURIComponent(reportMatch[1]);
      var qIndex = topHash.indexOf('?');
      if (qIndex >= 0) {
        var hashParams = new URLSearchParams(topHash.slice(qIndex));
        var fromHash = hashParams.get('jobId');
        if (fromHash) return fromHash;
      }
    } catch (error) {
      // ignore cross-origin access errors
    }
    return window.localStorage.getItem('ai_sport_lab.current_job_id') || '';
  }

  function showToast(msg, type) {
    var host = document.getElementById('toastHost');
    if (!host) return;
    var toast = document.createElement('div');
    toast.className = 'toast-item ' + (type || 'success');
    toast.textContent = msg;
    host.appendChild(toast);
    window.setTimeout(function () { toast.remove(); }, 2200);
  }

  function renderHeader(header) {
    var scoreEl = document.getElementById('report-score');
    var reactionEl = document.getElementById('metric-reaction');
    var accuracyEl = document.getElementById('metric-accuracy');
    var dtwEl = document.getElementById('metric-dtw');
    if (scoreEl) scoreEl.textContent = String(header.score || 0);
    if (reactionEl) reactionEl.textContent = String(header.avgReactionMs || 0) + 'ms';
    if (accuracyEl) accuracyEl.textContent = String(header.stepAccuracyPct || 0) + '%';
    if (dtwEl) dtwEl.textContent = String(header.dtwSimilarityPct || 0) + '%';
  }

  function renderAiInsights(aiInsights) {
    window.App.qsa('[data-ai-chart]').forEach(function (block) {
      var key = block.getAttribute('data-ai-chart');
      var list = block.querySelector('ul');
      if (!list) return;
      list.innerHTML = '';
      (aiInsights[key] || []).forEach(function (text) {
        var li = document.createElement('li');
        li.textContent = text;
        list.appendChild(li);
      });
    });
    var injuryList = document.querySelector('#injury-ai-insights ul');
    if (injuryList) {
      injuryList.innerHTML = '';
      (aiInsights.injury || []).forEach(function (text) {
        var li = document.createElement('li');
        li.innerHTML = '<span class="highlight">● ' + text + '</span>';
        injuryList.appendChild(li);
      });
    }
  }

  function renderChart(id, config) {
    var canvas = document.getElementById(id);
    if (!canvas || !window.Chart || !config) return;
    if (canvas.chart) canvas.chart.destroy();
    var options = globalChartOpt;
    if (config.type === 'pie') {
      options = Object.assign({}, globalChartOpt, { plugins: { legend: { position: 'right' } } });
    }
    canvas.chart = new window.Chart(canvas, {
      type: config.type,
      data: {
        labels: config.labels || [],
        datasets: config.datasets || []
      },
      options: options
    });
  }

  function renderCharts(charts) {
    Object.keys(charts || {}).forEach(function (key) {
      renderChart(key, charts[key]);
    });
  }

  function renderHistory(history) {
    var host = document.getElementById('historyList');
    if (!host) return;
    host.innerHTML = '';
    (history || []).forEach(function (item) {
      var row = document.createElement('div');
      row.className = 'history-item';
      row.innerHTML =
        '<div><div class="font-medium text-lg">' + (item.title || '分析报告') + '</div>' +
        '<div class="text-sm text-gray-500 mt-1">' + (item.summary || '') + '</div></div>' +
        '<button class="btn-secondary view-history">查看详情</button>';
      row.querySelector('.view-history').addEventListener('click', function () {
        if (item.jobId) {
          (window.top || window).location.href = '/#/report/' + encodeURIComponent(item.jobId);
        }
      });
      host.appendChild(row);
    });
  }

  function bindTabs() {
    var tabs = document.querySelectorAll('.report-tab');
    var contents = document.querySelectorAll('.tab-content');
    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        tabs.forEach(function (t) { t.classList.remove('active'); });
        tab.classList.add('active');
        var target = tab.dataset.tab;
        contents.forEach(function (content) { content.style.display = 'none'; });
        var panel = document.getElementById('tab-' + target);
        if (panel) panel.style.display = 'block';
        if (target === 'injury' && !muscleReady) {
          window.setTimeout(initMuscle3D, 80);
        }
      });
    });
  }

  function updateRiskLightMuscle() {
    var risk = muscleJointsData.some(function (joint) {
      return joint.angleVal < joint.stdRange[0] || joint.angleVal > joint.stdRange[1];
    });
    var light = document.getElementById('riskLight');
    if (!light) return;
    if (risk) light.classList.add('alert');
    else light.classList.remove('alert');
  }

  function showJointInfoMuscle(joint) {
    var nameSpan = document.getElementById('selectedJointName');
    var angleSpan = document.getElementById('selectedJointAngle');
    var riskSpan = document.getElementById('riskBadge');
    if (!joint || !nameSpan || !angleSpan) return;
    var isAbnormal = joint.angleVal < joint.stdRange[0] || joint.angleVal > joint.stdRange[1];
    var statusColor = isAbnormal ? '#ef4444' : '#10b981';
    var statusText = isAbnormal
      ? '⚠️ 超出安全范围 [' + joint.stdRange[0] + '-' + joint.stdRange[1] + ']'
      : '✅ 标准范围内';
    nameSpan.innerHTML = joint.name + ' <span style="font-size:12px;">(肌肉力群)</span>';
    angleSpan.innerHTML = joint.angleVal + '° &nbsp; <span style="font-size:12px; background:' + statusColor + '20; padding:2px 8px; border-radius:30px;">' + statusText + '</span><br><span style="font-size:12px; display:block; margin-top:6px;">' + joint.advice + '</span>';
    if (riskSpan) {
      riskSpan.innerHTML = isAbnormal
        ? '<span style="background:#ef4444; padding:4px 12px; border-radius:40px;">⚠️ 高风险偏差</span>'
        : '<span style="background:#10b981; padding:4px 12px; border-radius:40px;">无急性风险</span>';
    }
  }

  function addMuscleSegment(parent, width, height, depth, color, pos, rotZ) {
    var geo = new THREE.SphereGeometry(1, 32, 32);
    var mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({
      color: color,
      roughness: 0.4,
      metalness: 0.2,
      emissive: 0x221100,
      emissiveIntensity: 0.1
    }));
    mesh.scale.set(width, height, depth);
    mesh.position.set(pos[0], pos[1], pos[2]);
    mesh.rotation.z = rotZ || 0;
    parent.add(mesh);
    return mesh;
  }

  function initMuscle3D() {
    if (muscleReady && renderer) return;
    if (!window.THREE) return;
    var container = document.getElementById('human3dBox');
    if (!container) return;

    var oldCanvas = container.querySelector('canvas');
    if (oldCanvas) oldCanvas.remove();

    var w = container.clientWidth;
    var h = container.clientHeight;
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0c14);
    scene.fog = new THREE.FogExp2(0x0a0c14, 0.006);
    camera = new THREE.PerspectiveCamera(42, w / h, 0.1, 1000);
    camera.position.set(4.2, 1.8, 5.5);
    camera.lookAt(0, -0.5, 0);
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(w, h);
    container.appendChild(renderer.domElement);

    humanGroup = new THREE.Group();
    scene.add(humanGroup);

    scene.add(new THREE.AmbientLight(0x404060));
    var mainLight = new THREE.DirectionalLight(0xffddbb, 1.2);
    mainLight.position.set(2, 4, 3);
    scene.add(mainLight);

    addMuscleSegment(humanGroup, 0.85, 1.2, 0.65, 0xcd9a6b, [0, 0.2, 0]);
    addMuscleSegment(humanGroup, 0.9, 0.6, 0.7, 0xc28b5c, [0, -0.55, 0]);
    addMuscleSegment(humanGroup, 0.65, 0.95, 0.6, 0xbc7f4a, [-0.9, -1.05, 0], 0.05);
    addMuscleSegment(humanGroup, 0.65, 0.95, 0.6, 0xbc7f4a, [0.9, -1.05, 0], -0.05);
    addMuscleSegment(humanGroup, 0.55, 0.85, 0.55, 0xad7242, [-0.95, -2.1, 0], 0.02);
    addMuscleSegment(humanGroup, 0.55, 0.85, 0.55, 0xad7242, [0.95, -2.1, 0], -0.02);

    interactiveJoints = [];
    muscleJointsData.forEach(function (joint) {
      var geometry = new THREE.SphereGeometry(0.21, 32, 32);
      var material = new THREE.MeshStandardMaterial({
        color: 0xffaa55,
        emissive: 0xff4400,
        emissiveIntensity: 0.5,
        metalness: 0.2
      });
      var sphere = new THREE.Mesh(geometry, material);
      sphere.position.set(joint.pos[0], joint.pos[1], joint.pos[2]);
      sphere.userData = { jointData: joint };
      humanGroup.add(sphere);
      interactiveJoints.push({ mesh: sphere, data: joint });
    });

    raycaster = new THREE.Raycaster();
    mouseVec = new THREE.Vector2();
    renderer.domElement.addEventListener('click', function (event) {
      var rect = renderer.domElement.getBoundingClientRect();
      mouseVec.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouseVec.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(mouseVec, camera);
      var intersects = raycaster.intersectObjects(interactiveJoints.map(function (item) { return item.mesh; }));
      if (intersects.length > 0) {
        showJointInfoMuscle(intersects[0].object.userData.jointData);
      }
    });

    var isDrag = false;
    var lastX = 0;
    var lastY = 0;
    renderer.domElement.addEventListener('mousedown', function (event) {
      isDrag = true;
      lastX = event.clientX;
      lastY = event.clientY;
    });
    window.addEventListener('mousemove', function (event) {
      if (!isDrag || !humanGroup) return;
      humanGroup.rotation.y += (event.clientX - lastX) * 0.008;
      humanGroup.rotation.x += (event.clientY - lastY) * 0.006;
      humanGroup.rotation.x = Math.max(-0.9, Math.min(0.7, humanGroup.rotation.x));
      lastX = event.clientX;
      lastY = event.clientY;
    });
    window.addEventListener('mouseup', function () { isDrag = false; });

    function animate() {
      window.requestAnimationFrame(animate);
      if (renderer && scene && camera) renderer.render(scene, camera);
      updateRiskLightMuscle();
    }
    animate();

    muscleReady = true;
    var riskJoint = muscleJointsData.find(function (joint) {
      return joint.angleVal < joint.stdRange[0] || joint.angleVal > joint.stdRange[1];
    });
    showJointInfoMuscle(riskJoint || muscleJointsData[0]);
  }

  function bindExportButtons() {
    document.getElementById('exportPdfBtn')?.addEventListener('click', function () {
      showToast('📄 运动分析报告已生成 (PDF模拟)', 'success');
    });
    document.getElementById('exportCsvBtn')?.addEventListener('click', function () {
      var downloads = (reportPayload && reportPayload.downloads) || {};
      var first = Object.values(downloads).find(Boolean);
      if (first) {
        window.open(first, '_blank');
        showToast('📊 正在下载 CSV 数据', 'success');
      } else {
        showToast('暂无可下载 CSV', 'warn');
      }
    });
    document.getElementById('filterHistoryBtn')?.addEventListener('click', function () {
      showToast('🔍 历史报告筛选已应用', 'success');
    });
  }

  function readTrainingMode() {
    try {
      var ppPayload = JSON.parse(window.localStorage.getItem('pp-footwork-training-mode') || 'null');
      if (ppPayload && ppPayload.mode) return ppPayload.mode;
    } catch (error) {
      // ignore
    }
    return window.localStorage.getItem('ai_sport_lab.training_mode') || 'eval';
  }

  function getCurrentUserId() {
    try {
      return window.sessionStorage.getItem('pp-current-user-id') || '';
    } catch (error) {
      return '';
    }
  }

  async function saveReportToUserHistory(jobId, header) {
    var userId = getCurrentUserId();
    if (!userId || !jobId) return;
    var summary = {
      loops: header.loops || 0,
      avgSpeed: Number(header.avgSpeed || header.meanComSpeedMps || 0),
      symmetry: header.symmetry != null ? header.symmetry : (header.stepAccuracyPct || 0),
      totalTime: Number(header.totalTime || header.durationS || 0),
      peakAccel: Number(header.peakAccel || 0),
      score: header.score || 0,
    };
    try {
      await fetch('/api/reports', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          job_id: jobId,
          mode: readTrainingMode(),
          step_name: header.stepName || '视频分析',
          summary: summary,
        }),
      });
    } catch (error) {
      // non-blocking
    }
  }

  async function loadReport() {
    var jobId = getJobId();
    if (!jobId) {
      showToast('缺少任务 ID，无法加载报告', 'warn');
      return;
    }
    try {
      var response = await fetch('/api/analysis/jobs/' + encodeURIComponent(jobId) + '/report-ui');
      var payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error((payload && payload.error) || '加载报告失败');
      }
      reportPayload = payload;
      muscleJointsData = payload.muscleJoints || [];
      renderHeader(payload.header || {});
      renderCharts(payload.charts || {});
      renderAiInsights(payload.aiInsights || {});
      renderHistory(payload.history || []);
      await saveReportToUserHistory(jobId, payload.header || {});
    } catch (error) {
      showToast(error.message || '报告加载失败', 'error');
    }
  }

  window.App.onReady(function () {
    document.documentElement.dataset.pageReady = 'report';
    bindTabs();
    bindExportButtons();
    loadReport();
  });
})();
