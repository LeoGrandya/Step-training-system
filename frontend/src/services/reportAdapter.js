/** Real analysis payload → Pose3D report dashboard model with rich ECharts options. */
import { tooltipTheme } from '../utils/chartTheme.js'

// ── palette (matches my-pingpong-project sky-blue theme) ──
const C = {
  sky: '#0ea5e9',
  skyDark: '#0284c7',
  skyBg: 'rgba(14,165,233,0.10)',
  skyBg2: 'rgba(14,165,233,0.18)',
  emerald: '#10b981',
  emeraldBg: 'rgba(16,185,129,0.10)',
  amber: '#f59e0b',
  amberBg: 'rgba(245,158,11,0.12)',
  red: '#ef4444',
  redBg: 'rgba(239,68,68,0.10)',
  violet: '#6366f1',
  violetBg: 'rgba(99,102,241,0.10)',
  slate: '#64748b',
  dark: '#0f172a',
  grid: '#e2e8f0',
  white: '#ffffff',
  bg: '#f8fafc',
}

// ── helpers ──
function hexToRgba(hex, alpha = 0.08) {
  if (!hex || typeof hex !== 'string') return hex
  if (hex.startsWith('rgba(') || hex.startsWith('hsla(')) return hex
  if (hex.startsWith('rgb(')) return hex.replace(')', ', ' + alpha + ')').replace('rgb', 'rgba')
  if (hex.startsWith('hsl(')) return hex.replace(')', ', ' + alpha + ')').replace('hsl', 'hsla')
  const h = hex.replace('#', '')
  if (h.length === 3) {
    const [r, g, b] = h.split('').map(c => parseInt(c + c, 16))
    return 'rgba(' + r + ', ' + g + ', ' + b + ', ' + alpha + ')'
  }
  if (h.length === 6) {
    const r = parseInt(h.substring(0, 2), 16)
    const g = parseInt(h.substring(2, 4), 16)
    const b = parseInt(h.substring(4, 6), 16)
    return 'rgba(' + r + ', ' + g + ', ' + b + ', ' + alpha + ')'
  }
  return hex
}

function finiteNumber(value) {
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

function firstFinite(...values) {
  for (const v of values) {
    const n = finiteNumber(v)
    if (n !== null) return n
  }
  return null
}

function formatNumber(value, digits = 2) {
  const n = finiteNumber(value)
  if (n === null) return '暂无数据'
  return n.toFixed(digits)
}

function rows(payload, key) {
  const v = payload?.universal2?.[key]
  return Array.isArray(v) ? v : []
}

function numberFromRow(row, patterns) {
  if (!row || typeof row !== 'object') return null
  const keys = Object.keys(row)
  const key = keys.find(k => patterns.some(p => p.test(String(k))))
  return key ? finiteNumber(row[key]) : null
}

// ── ECharts option builders ──
function baseGrid() {
  return { top: 36, right: 28, bottom: 36, left: 62 }
}

function baseTooltip() {
  return tooltipTheme('axis')
}

function xAxisTime(data) {
  return { type: 'category', data, axisLabel: { color: C.slate, fontSize: 10 }, axisLine: { lineStyle: { color: C.grid } } }
}

function yAxisLinear(name = '', opts = {}) {
  return { type: 'value', name, nameTextStyle: { color: C.slate, fontSize: 10 }, axisLabel: { color: C.slate, fontSize: 10 }, splitLine: { lineStyle: { color: C.grid, type: 'dashed' } }, ...opts }
}

function lineSeries(name, data, color, opts = {}) {
  return { name, type: 'line', smooth: true, symbol: 'none', data, lineStyle: { color, width: 2 }, areaStyle: { color: hexToRgba(color, 0.08) }, ...opts }
}

function barSeries(name, data, color) {
  return { name, type: 'bar', data, itemStyle: { color, borderRadius: [4, 4, 0, 0] } }
}

function compactPairs(xVals, yVals, limit = 200) {
  const count = Math.min(xVals.length, yVals.length)
  if (!count) return { labels: [], values: [] }
  const step = Math.max(1, Math.ceil(count / limit))
  const labels = [], values = []
  for (let i = 0; i < count; i += step) {
    labels.push(String(i))
    values.push(Number(Number(yVals[i] || 0).toFixed(4)))
  }
  return { labels, values }
}

function compactTriples(xVals, yVals, zVals, limit = 200) {
  const count = Math.min(xVals.length, yVals.length, zVals.length)
  if (!count) return { labels: [], xValues: [], yValues: [], zValues: [] }
  const step = Math.max(1, Math.ceil(count / limit))
  const labels = [], xValues = [], yValues = [], zValues = []
  for (let i = 0; i < count; i += step) {
    labels.push(String(i))
    xValues.push(Number(Number(xVals[i] || 0).toFixed(4)))
    yValues.push(Number(Number(yVals[i] || 0).toFixed(4)))
    zValues.push(Number(Number(zVals[i] || 0).toFixed(4)))
  }
  return { labels, xValues, yValues, zValues }
}

// ── build model ──
export function buildPose3dReportModel({ result, reportUi, jobId }) {
  const payload = result || {}
  const summary = payload.summaryMetrics || {}
  const derived = payload.derivedStats || {}
  const quality = payload.qualityFlags || {}
  const ts = payload.timeseries || {}
  const stepMetrics = payload.stepMetrics || []
  const unitMetrics = payload.unitMetrics || []
  const timeArr = ts.time_s || []
  const speedArr = ts.com_speed_mps || []
  const accelArr = ts.com_acceleration_mps2 || []
  const turnArr = ts.turning_speed_deg_s || []
  const leftClr = ts.left_clearance_m || []
  const rightClr = ts.right_clearance_m || []
  const leftKnee = ts.left_knee_angle_deg || []
  const rightKnee = ts.right_knee_angle_deg || []
  const leftAnkle = ts.left_ankle_angle_deg || []
  const rightAnkle = ts.right_ankle_angle_deg || []
  const comX = ts.com_x || []
  const comY = ts.com_y || []
  const comZ = ts.com_z || []
  const comCell = ts.com_cell || []
  const leftHip = ts.left_hip_angle_deg || []
  const rightHip = ts.right_hip_angle_deg || []
  const leftHipTorque = ts.left_hip_torque_nm || []
  const rightHipTorque = ts.right_hip_torque_nm || []
  const leftKneeTorque = ts.left_knee_torque_nm || []
  const rightKneeTorque = ts.right_knee_torque_nm || []
  const leftHipPower = ts.left_hip_power_w || []
  const rightHipPower = ts.right_hip_power_w || []
  const leftKneePower = ts.left_knee_power_w || []
  const rightKneePower = ts.right_knee_power_w || []

  const reportHeader = reportUi?.header || {}

  return {
    jobId: payload.jobId || jobId || '',
    status: payload.status || 'unknown',
    config: payload.config || {},
    header: {
      score: firstFinite(reportHeader.score, summary.score),
      avgReactionMs: firstFinite(reportHeader.avgReactionMs, summary.mean_cycle_time_s != null ? summary.mean_cycle_time_s * 1000 : null),
      activeRatio: quality.analysisActiveRatio ?? null,
      cycleCount: quality.cycleCount ?? null,
      segmentationStatus: quality.segmentationStatus || '',
      segmentationReason: quality.segmentationReason || '',
    },
    stats: buildStats(summary, derived, quality, stepMetrics, unitMetrics),
    overview: { summary, derived, quality, assessments: payload.kpiAssessments || {}, stepMetrics, unitMetrics },
    charts: {
      speed: buildSpeedChart(timeArr, speedArr, unitMetrics),
      acceleration: buildAccelerationChart(timeArr, accelArr),
      speedAccelDual: buildSpeedAccelDual(timeArr, speedArr, accelArr),
      speedXY: buildSpeedXYChart(timeArr, comX, comY),
      turning: buildTurningChart(timeArr, turnArr),
      clearance: buildClearanceChart(timeArr, leftClr, rightClr),
      displacement: buildDisplacementChart(timeArr, comX, comY, speedArr),
      displacementXY: buildDisplacementXYChart(timeArr, comX, comY),
      cumulativeDist: buildCumulativeDistChart(timeArr, comX, comY, comZ),
      airborne: buildAirborneChart(payload),
      footHeight: buildFootHeightChart(timeArr, leftClr, rightClr, ts),
      joint: buildJointChart(timeArr, leftKnee, rightKnee, leftAnkle, rightAnkle),
      jointAngVel: buildJointAngVelChart(timeArr, leftKnee, rightKnee, leftAnkle, rightAnkle),
      jointRomRadar: buildJointRomRadar(summary, derived),
      gantt: buildGanttChart(unitMetrics),
      phasePlane: buildPhasePlaneChart(comX, comY, speedArr),
      radar: buildRadarChart(summary, derived, quality),
      speedTrend: buildSpeedTrendChart(unitMetrics),
      efficiency: buildEfficiencyChart(unitMetrics),
      dtwHeatmap: buildDtwHeatmap(unitMetrics),
      efficiencyBars: buildEfficiencyBarsChart(unitMetrics),
      symmetry: buildSymmetryScatter(leftClr, rightClr),
      tableScatter: buildTableScatter(comX, comY, speedArr),
      tableHeatmap: buildTableHeatmap(comX, comY, comCell),
      parallelCoords: buildParallelCoords(unitMetrics),
      footPressure: buildFootPressureData(ts, stepMetrics, quality),
      dirPie: buildDirPie(stepMetrics),
      stepEfficiencyBars: buildStepEfficiencyBars(unitMetrics),
      aiInsights: buildAiInsights(summary, derived, quality, stepMetrics, unitMetrics),
      torqueChart: buildTorqueChart(timeArr, leftHipTorque, rightHipTorque, leftKneeTorque, rightKneeTorque),
      powerChart: buildPowerChart(timeArr, leftHipPower, rightHipPower, leftKneePower, rightKneePower),
      hipAngleChart: buildHipAngleChart(timeArr, leftHip, rightHip),
      muscleLoad: buildMuscleLoadData(leftHipTorque, rightHipTorque, leftKneeTorque, rightKneeTorque, leftKneePower, rightKneePower, derived),
      energyBars: buildEnergyBars(payload, derived),
      jointWorkPie: buildJointWorkPie(leftHipPower, rightHipPower, leftKneePower, rightKneePower),
    },
    tables: {
      evaluationFrame: rows(payload, 'evaluationFrame'),
      displacementFrame: rows(payload, 'displacementFrame'),
      airborneEvents: buildAirborneEvents(payload),
      airborneFrame: rows(payload, 'airborneFrame'),
      airborneSummary: rows(payload, 'airborneSummary'),
      jointFrame: rows(payload, 'jointFrame'),
      jointSummary: rows(payload, 'jointSummary'),
      stateEvents: rows(payload, 'stateEvents'),
      speedSummary: rows(payload, 'speedSummary'),
    },
    downloads: buildDownloads(payload),
    statsRaw: { summary, derived, quality, stepCount: stepMetrics.length, unitCount: unitMetrics.length },
  }
}

// ── StatsOverview ──
function buildStats(summary, derived, quality, stepMetrics, unitMetrics) {
  const duration = firstFinite(derived.duration_s, summary.duration_s)
  const stepCount = stepMetrics.length
  const stepFreq = duration && duration > 0 ? (stepCount / duration) : null
  const peakSpeed = firstFinite(summary.peak_com_speed_mps, derived.com_speed_p95_mps)
  const asym = derived.clearance_asymmetry_peak_m
  const symLabel = asym != null
    ? (asym <= 0.05 ? '优秀' : asym <= 0.1 ? '良好' : '待改善')
    : '暂无数据'

  return [
    { label: '最高移动速度', value: peakSpeed != null ? formatNumber(peakSpeed, 2) : '暂无数据', unit: 'm/s', icon: 'speed' },
    { label: '左右均衡度', value: asym != null ? formatNumber((1 - asym) * 100, 1) : '暂无数据', unit: '% · ' + symLabel, icon: 'symmetry' },
    { label: '总步数', value: stepCount > 0 ? String(stepCount) : '暂无数据', unit: '步 · ' + (stepFreq != null ? formatNumber(stepFreq, 1) + 'Hz' : ''), icon: 'steps' },
    { label: '移动轮次', value: quality.cycleCount != null ? String(quality.cycleCount) : '暂无数据', unit: '轮', icon: 'cycle' },
    { label: '最快加速度', value: derived.com_accel_abs_p95_mps2 != null ? formatNumber(derived.com_accel_abs_p95_mps2, 1) : '暂无数据', unit: 'm/s²', icon: 'accel' },
    { label: '训练专注度', value: quality.analysisActiveRatio != null ? formatNumber(quality.analysisActiveRatio * 100, 1) : '暂无数据', unit: '%', icon: 'active' },
  ]
}

// ── Speed + Acceleration charts ──
function buildSpeedChart(timeArr, speedArr, unitMetrics) {
  const p = compactPairs(timeArr, speedArr)
  if (!p.labels.length) return null
  const labels = p.labels.map(v => timeArr[Number(v)]?.toFixed(2) || v)
  // Build markArea from unit phase boundaries
  const markAreaData = []
  if (unitMetrics && unitMetrics.length) {
    unitMetrics.slice(0, 1).forEach((u) => {
      const ms = finiteNumber(u.move_start_time_s) || 0
      const me = finiteNumber(u.move_end_time_s) || 0
      const rs = finiteNumber(u.restore_start_time_s) || 0
      const re = finiteNumber(u.restore_end_time_s) || 0
      if (ms > 0 || rs > 0) {
        markAreaData.push([{ xAxis: String(ms.toFixed(1)), itemStyle: { color: 'rgba(99,102,241,0.08)' } }, { xAxis: String(me.toFixed(1)) }])
        markAreaData.push([{ xAxis: String(me.toFixed(1)), itemStyle: { color: 'rgba(56,189,248,0.08)' } }, { xAxis: String(rs.toFixed(1)) }])
        markAreaData.push([{ xAxis: String(rs.toFixed(1)), itemStyle: { color: 'rgba(245,158,11,0.08)' } }, { xAxis: String(re.toFixed(1)) }])
      }
    })
  }
  return {
    ...baseTooltip(),
    grid: baseGrid(),
    xAxis: xAxisTime(labels),
    yAxis: yAxisLinear('m/s'),
    series: [{
      ...lineSeries('移动速度', p.values, C.sky),
      lineStyle: { color: '#38bdf8', width: 1.5 },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(56,189,248,0.25)' }, { offset: 1, color: 'rgba(56,189,248,0.02)' }] } },
      ...(markAreaData.length ? { markArea: { silent: true, data: markAreaData } } : {}),
    }],
  }
}

function buildAccelerationChart(timeArr, accelArr) {
  const p = compactPairs(timeArr, accelArr)
  if (!p.labels.length) return null
  return {
    ...baseTooltip(),
    grid: baseGrid(),
    xAxis: xAxisTime(p.labels.map(v => timeArr[Number(v)]?.toFixed(2) || v)),
    yAxis: yAxisLinear('m/s²'),
    series: [lineSeries('加速度', p.values, C.amber)],
  }
}

function buildSpeedAccelDual(timeArr, speedArr, accelArr) {
  const pS = compactPairs(timeArr, speedArr)
  const pA = compactPairs(timeArr, accelArr)
  if (!pS.labels.length) return null
  const labels = pS.labels.map(v => timeArr[Number(v)]?.toFixed(2) || v)
  return {
    ...baseTooltip(),
    grid: { top: 34, bottom: 28, left: 56, right: 66 },
    legend: { data: ['移动速度', '加速度'], right: 4, top: 6, textStyle: { color: '#94a3b8', fontSize: 11 } },
    xAxis: xAxisTime(labels),
    yAxis: [
      { type: 'value', name: '速度(m/s)', nameTextStyle: { color: '#38bdf8', fontSize: 11 }, nameLocation: 'middle', nameGap: 40, axisLabel: { color: '#475569', fontSize: 11 }, splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } }, axisLine: { lineStyle: { color: '#334155' } } },
      { type: 'value', name: '加速度(m/s²)', nameTextStyle: { color: '#f59e0b', fontSize: 11 }, nameLocation: 'middle', nameGap: 42, axisLabel: { color: '#475569', fontSize: 11 }, splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } }, axisLine: { lineStyle: { color: '#334155' } } },
    ],
    series: [
      { ...lineSeries('移动速度', pS.values, '#38bdf8'), yAxisIndex: 0, lineStyle: { color: '#38bdf8', width: 2 } },
      { ...lineSeries('加速度', pA.values, '#f59e0b'), yAxisIndex: 1, lineStyle: { color: '#f59e0b', width: 1.5, type: 'dashed' } },
    ],
  }
}

function buildSpeedXYChart(timeArr, comX, comY) {
  if (!comX.length || !comY.length) return null
  const vx = [], vy = [], labels = []
  const step = Math.max(1, Math.ceil(Math.min(comX.length, comY.length) / 200))
  for (let i = 1; i < Math.min(comX.length, comY.length); i += step) {
    vx.push(Number(((comX[i] - comX[i - 1]) * 60).toFixed(3)))
    vy.push(Number(((comY[i] - comY[i - 1]) * 60).toFixed(3)))
    labels.push(timeArr[i]?.toFixed(2) || String(i))
  }
  if (!vx.length) return null
  return {
    ...baseTooltip(),
    grid: { top: 34, bottom: 28, left: 56, right: 28 },
    legend: { data: ['左右速度', '前后速度'], right: 4, top: 6, textStyle: { color: '#94a3b8', fontSize: 11 } },
    xAxis: xAxisTime(labels),
    yAxis: yAxisLinear('速度(m/s)'),
    series: [
      { ...lineSeries('左右速度', vx, '#3b82f6'), lineStyle: { color: '#3b82f6', width: 1.5 } },
      { ...lineSeries('前后速度', vy, '#ef4444'), lineStyle: { color: '#ef4444', width: 1.5 } },
    ],
  }
}

function buildTurningChart(timeArr, turnArr) {
  const p = compactPairs(timeArr, turnArr)
  if (!p.labels.length) return null
  return {
    ...baseTooltip(),
    grid: baseGrid(),
    xAxis: xAxisTime(p.labels.map(v => timeArr[Number(v)]?.toFixed(2) || v)),
    yAxis: yAxisLinear('deg/s'),
    series: [lineSeries('变向速度', p.values, C.violet)],
  }
}

// ── Foot clearance chart ──
function buildClearanceChart(timeArr, leftClr, rightClr) {
  const pL = compactPairs(timeArr, leftClr)
  const pR = compactPairs(timeArr, rightClr)
  if (!pL.labels.length && !pR.labels.length) return null
  const labels = (pL.labels.length ? pL : pR).labels.map(v => timeArr[Number(v)]?.toFixed(2) || v)
  return {
    ...baseTooltip(),
    grid: baseGrid(),
    legend: { data: ['左脚高度', '右脚高度'], bottom: 6, textStyle: { fontSize: 10, color: C.slate } },
    xAxis: xAxisTime(labels),
    yAxis: yAxisLinear('m'),
    series: [
      lineSeries('左脚高度', pL.values, C.sky),
      lineSeries('右脚高度', pR.values, C.amber),
    ],
  }
}

// ── Displacement chart (trajectory scatter + XY decomposition + cumulative, matching my-pingpong-project style) ──
function buildDisplacementChart(timeArr, comX, comY, speedArr) {
  const t = compactTriples(comX, comY, timeArr)
  if (!t.labels.length) return null
  const spd = speedArr && speedArr.length ? speedArr : null
  const data = t.xValues.map((x, i) => {
    const point = [x, t.yValues[i]]
    if (spd && spd[i] != null) point.push(Number(spd[i].toFixed(2)))
    return point
  })
  const maxSpeed = spd ? Math.max(...spd.filter(v => v != null && isFinite(v)), 1) : 3
  return {
    tooltip: tooltipTheme(),
    grid: { top: 28, bottom: 28, left: 52, right: 62 },
    xAxis: { type: 'value', name: 'X 左右(m)', nameTextStyle: { color: '#64748b', fontSize: 11 }, nameLocation: 'middle', nameGap: 28, axisLabel: { color: '#475569', fontSize: 11 }, splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } }, axisLine: { lineStyle: { color: '#334155' } } },
    yAxis: { type: 'value', name: 'Y 前后(m)', nameTextStyle: { color: '#64748b', fontSize: 11 }, nameLocation: 'middle', nameGap: 36, axisLabel: { color: '#475569', fontSize: 11 }, splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } }, axisLine: { lineStyle: { color: '#334155' } } },
    visualMap: spd ? { min: 0, max: maxSpeed, inRange: { color: ['#3b82f6', '#22c55e', '#eab308', '#ef4444'] }, text: ['高速', '低速'], textStyle: { color: '#94a3b8', fontSize: 10 }, right: 8, top: 6, calculable: false, dimension: 2 } : undefined,
    series: [{
      type: 'scatter', data, symbolSize: 3,
      itemStyle: { shadowBlur: 2, shadowColor: '#38bdf866' },
    }],
  }
}

function buildDisplacementXYChart(timeArr, comX, comY) {
  if (!comX.length || !comY.length) return null
  const step = Math.max(1, Math.ceil(Math.min(comX.length, comY.length) / 200))
  const labels = [], dx = [], dy = []
  for (let i = 1; i < Math.min(comX.length, comY.length); i += step) {
    labels.push(timeArr[i]?.toFixed(2) || String(i))
    dx.push(Number((comX[i] - comX[i - 1]).toFixed(4)))
    dy.push(Number((comY[i] - comY[i - 1]).toFixed(4)))
  }
  if (!labels.length) return null
  return {
    ...baseTooltip(),
    grid: baseGrid(),
    legend: { data: ['X(左右)', 'Y(前后)'], bottom: 6, textStyle: { fontSize: 10, color: C.slate } },
    xAxis: xAxisTime(labels),
    yAxis: yAxisLinear('m/帧'),
    series: [
      lineSeries('X(左右)', dx, C.sky),
      lineSeries('Y(前后)', dy, C.emerald),
    ],
  }
}

function buildCumulativeDistChart(timeArr, comX, comY, comZ) {
  if (!comX.length) return null
  const step = Math.max(1, Math.ceil(comX.length / 200))
  const labels = [], d3d = [], d2d = []
  let sum3d = 0, sum2d = 0
  for (let i = 1; i < comX.length; i += step) {
    const dx = comX[i] - comX[i - 1], dy = comY[i] - comY[i - 1], dz = (comZ[i] || 0) - (comZ[i - 1] || 0)
    sum3d += Math.sqrt(dx * dx + dy * dy + dz * dz)
    sum2d += Math.sqrt(dx * dx + dy * dy)
    labels.push(timeArr[i]?.toFixed(2) || String(i))
    d3d.push(Number(sum3d.toFixed(3)))
    d2d.push(Number(sum2d.toFixed(3)))
  }
  if (!labels.length) return null
  return {
    ...baseTooltip(),
    grid: baseGrid(),
    legend: { data: ['3D累积', '水平累积'], bottom: 6, textStyle: { fontSize: 10, color: C.slate } },
    xAxis: xAxisTime(labels),
    yAxis: yAxisLinear('m'),
    series: [
      lineSeries('3D累积', d3d, C.sky),
      lineSeries('水平累积', d2d, C.emerald),
    ],
  }
}

// ── Airborne chart ──
function buildAirborneEvents(payload) {
  return rows(payload, 'airborneEvents')
}

function buildAirborneChart(payload) {
  const events = buildAirborneEvents(payload)
  const labels = [], values = []
  events.slice(0, 40).forEach((row, i) => {
    const dur = numberFromRow(row, [/duration/i, /时长/, /持续/])
    if (dur === null) return
    labels.push(String(i + 1))
    values.push(Number(dur.toFixed(4)))
  })
  if (!labels.length) return null
  return {
    ...baseTooltip(),
    grid: baseGrid(),
    xAxis: { type: 'category', data: labels, name: '事件序号', axisLabel: { color: C.slate, fontSize: 10 } },
    yAxis: yAxisLinear('s'),
    series: [barSeries('腾空时长', values, C.sky)],
  }
}

function buildFootHeightChart(timeArr, leftClr, rightClr, ts) {
  const pL = compactPairs(timeArr, leftClr)
  const pR = compactPairs(timeArr, rightClr)
  if (!pL.labels.length && !pR.labels.length) return null
  const labels = (pL.labels.length ? pL : pR).labels.map(v => timeArr[Number(v)]?.toFixed(2) || v)
  return {
    ...baseTooltip(),
    grid: { top: 32, right: 22, bottom: 28, left: 52 },
    legend: { data: ['左脚高度', '右脚高度'], bottom: 6, textStyle: { fontSize: 10, color: C.slate } },
    xAxis: xAxisTime(labels),
    yAxis: yAxisLinear('m'),
    series: [
      { ...lineSeries('左脚高度', pL.values, C.sky), areaStyle: { color: 'rgba(14,165,233,0.12)' } },
      { ...lineSeries('右脚高度', pR.values, C.amber), areaStyle: { color: 'rgba(245,158,11,0.10)' } },
    ],
  }
}

// ── Joint biomechanics ──
function buildJointChart(timeArr, leftKnee, rightKnee, leftAnkle, rightAnkle) {
  const hasKnee = leftKnee.length || rightKnee.length
  const hasAnkle = leftAnkle.length || rightAnkle.length
  if (!hasKnee && !hasAnkle) return null
  const step = Math.max(1, Math.ceil(Math.max(timeArr.length, 1) / 200))
  const labels = [], lk = [], rk = [], la = [], ra = []
  for (let i = 0; i < Math.max(leftKnee.length, rightKnee.length, leftAnkle.length, rightAnkle.length); i += step) {
    labels.push(timeArr[i]?.toFixed(2) || String(i))
    lk.push(leftKnee[i] != null ? Number(leftKnee[i].toFixed(1)) : null)
    rk.push(rightKnee[i] != null ? Number(rightKnee[i].toFixed(1)) : null)
    la.push(leftAnkle[i] != null ? Number(leftAnkle[i].toFixed(1)) : null)
    ra.push(rightAnkle[i] != null ? Number(rightAnkle[i].toFixed(1)) : null)
  }
  if (!labels.length) return null
  const series = []
  if (lk.some(v => v !== null)) series.push({ ...lineSeries('左膝', lk, C.sky), connectNulls: true })
  if (rk.some(v => v !== null)) series.push({ ...lineSeries('右膝', rk, C.amber), connectNulls: true })
  if (la.some(v => v !== null)) series.push({ ...lineSeries('左踝', la, C.emerald), connectNulls: true })
  if (ra.some(v => v !== null)) series.push({ ...lineSeries('右踝', ra, C.red), connectNulls: true })
  return {
    ...baseTooltip(),
    grid: baseGrid(),
    legend: { data: series.map(s => s.name), bottom: 6, textStyle: { fontSize: 10, color: C.slate } },
    xAxis: xAxisTime(labels),
    yAxis: yAxisLinear('deg'),
    series,
  }
}

function buildJointAngVelChart(timeArr, leftKnee, rightKnee, leftAnkle, rightAnkle) {
  const arrs = [leftKnee, rightKnee, leftAnkle, rightAnkle]
  const hasAny = arrs.some(a => a && a.length > 2)
  if (!hasAny) return null
  const step = Math.max(1, Math.ceil(Math.max(timeArr.length, 1) / 200))
  const labels = [], vel = [[], [], [], []]
  const names = ['左膝角速度', '右膝角速度', '左踝角速度', '右踝角速度']
  const colors = [C.sky, C.amber, C.emerald, C.red]
  for (let i = 1; i < Math.max(...arrs.map(a => a.length)); i += step) {
    labels.push(timeArr[i]?.toFixed(2) || String(i))
    for (let j = 0; j < 4; j++) {
      const a = arrs[j]
      vel[j].push(a[i] != null && a[i - 1] != null ? Number(Math.abs(a[i] - a[i - 1]) * 60).toFixed(1) : null)
    }
  }
  if (!labels.length) return null
  const series = names.map((name, i) => {
    if (vel[i].every(v => v === null)) return null
    return { ...lineSeries(name, vel[i], colors[i]), connectNulls: true }
  }).filter(Boolean)
  if (!series.length) return null
  return {
    ...baseTooltip(),
    grid: baseGrid(),
    legend: { data: series.map(s => s.name), bottom: 6, textStyle: { fontSize: 10, color: C.slate } },
    xAxis: xAxisTime(labels),
    yAxis: yAxisLinear('deg/s'),
    series,
  }
}

function buildJointRomRadar(summary, derived) {
  const lkMax = finiteNumber(summary.left_knee_angle_max_deg)
  const rkMax = finiteNumber(summary.right_knee_angle_max_deg)
  const laMax = finiteNumber(summary.left_ankle_angle_max_deg)
  const raMax = finiteNumber(summary.right_ankle_angle_max_deg)
  const lhMax = finiteNumber(summary.left_hip_angle_max_deg)
  const rhMax = finiteNumber(summary.right_hip_angle_max_deg)
  if (lkMax === null && rkMax === null && laMax === null && raMax === null) return null
  const toScore = (v, ref) => v != null ? Math.min(100, Math.round((v / ref) * 85)) : 0
  const indicators = [
    { name: '膝关节', max: 100 },
    { name: '踝关节', max: 100 },
    { name: '髋关节', max: 100 },
    { name: '对称性', max: 100 },
    { name: '活动范围', max: 100 },
  ]
  const asym = finiteNumber(derived?.clearance_asymmetry_peak_m)
  const symScore = asym != null ? Math.max(30, 100 - asym * 400) : 70
  const leftValues = [
    toScore(lkMax, 170),
    toScore(laMax, 110),
    toScore(lhMax || lkMax * 1.2 || 120, 130),
    symScore,
    Math.round((toScore(lkMax, 170) + toScore(laMax, 110)) / 2),
  ]
  const rightValues = [
    toScore(rkMax, 170),
    toScore(raMax, 110),
    toScore(rhMax || rkMax * 1.2 || 120, 130),
    symScore,
    Math.round((toScore(rkMax, 170) + toScore(raMax, 110)) / 2),
  ]
  return {
    tooltip: { trigger: 'item' },
    legend: { data: ['左侧', '右侧'], bottom: 6, textStyle: { fontSize: 10, color: C.slate } },
    radar: {
      radius: '58%',
      indicator: indicators,
      axisName: { color: C.slate, fontSize: 11 },
    },
    series: [
      {
        type: 'radar', name: '左侧',
        data: [{ value: leftValues }],
        areaStyle: { color: 'rgba(14,165,233,0.12)' },
        lineStyle: { color: C.sky, width: 2 },
        itemStyle: { color: C.sky },
      },
      {
        type: 'radar', name: '右侧',
        data: [{ value: rightValues }],
        areaStyle: { color: 'rgba(245,158,11,0.10)' },
        lineStyle: { color: C.amber, width: 2 },
        itemStyle: { color: C.amber },
      },
    ],
  }
}

// ── Gantt for period timing ──
function buildGanttChart(unitMetrics) {
  if (!unitMetrics.length) return null
  const GANTT_COLORS = ['#6366f1', '#38bdf8', '#f59e0b', '#10b981']
  // Single cycle: 4-phase detailed Gantt matching my-pingpong-project style
  if (unitMetrics.length === 1) {
    const u = unitMetrics[0]
    const moveStart = finiteNumber(u.move_start_time_s) || 0
    const moveEnd = finiteNumber(u.move_end_time_s) || (finiteNumber(u.move_duration_s) || 0.5)
    const restoreStart = finiteNumber(u.restore_start_time_s) || moveEnd
    const restoreEnd = finiteNumber(u.restore_end_time_s) || (restoreStart + (finiteNumber(u.restore_duration_s) || 0.4))
    const preMoveEnd = moveStart
    const preRestoreEnd = restoreStart
    const phases = ['移动前停止', '移动', '还原前停止', '还原']
    const data = [
      [0, 0, preMoveEnd],
      [0, moveStart, moveEnd],
      [0, restoreStart, preRestoreEnd > restoreStart ? preRestoreEnd : restoreEnd + 0.1],
      [0, restoreStart, restoreEnd],
    ].map((v, i) => [v[0], v[1], v[2], v[2] - v[1]])
    return {
      tooltip: tooltipTheme('item'),
      grid: { top: 10, bottom: 18, left: 72, right: 10 },
      xAxis: { type: 'value', name: '时间(s)', nameTextStyle: { color: '#64748b', fontSize: 11 }, axisLabel: { color: '#475569', fontSize: 11 }, splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } } },
      yAxis: { type: 'category', data: phases, inverse: true, axisLabel: { color: '#94a3b8', fontSize: 11 }, axisLine: { lineStyle: { color: '#334155' } } },
      series: [{ type: 'bar', data, itemStyle: { borderRadius: [0, 4, 4, 0] }, label: { show: true, position: 'insideLeft', formatter: p => (p.value[2]).toFixed(1) + 's', color: '#fff', fontSize: 11 }, encode: { x: [1, 2], y: 0 }, barWidth: 16, color: (p) => GANTT_COLORS[p.dataIndex] }],
    }
  }
  // Multiple cycles: overview Gantt
  const data = []
  unitMetrics.slice(0, 12).forEach((u, i) => {
    const moveStart = finiteNumber(u.move_start_frame) || 0
    const moveEnd = finiteNumber(u.move_end_frame) || 0
    const restoreStart = finiteNumber(u.restore_start_frame) || 0
    const restoreEnd = finiteNumber(u.restore_end_frame) || 0
    data.push(
      { value: [i, moveStart, moveEnd, moveEnd - moveStart], itemStyle: { color: '#38bdf8', borderRadius: [0, 4, 4, 0] } },
      { value: [i, restoreStart, restoreEnd, restoreEnd - restoreStart], itemStyle: { color: '#10b981', borderRadius: [0, 4, 4, 0] } },
    )
  })
  return {
    tooltip: tooltipTheme('item'),
    grid: { top: 10, bottom: 18, left: 60, right: 10 },
    xAxis: { type: 'value', name: '帧', nameTextStyle: { color: '#64748b', fontSize: 11 }, axisLabel: { color: '#475569', fontSize: 11 }, splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } } },
    yAxis: { type: 'category', data: unitMetrics.slice(0, 12).map((_, i) => `周期${i + 1}`), axisLabel: { color: '#94a3b8', fontSize: 10 }, axisLine: { lineStyle: { color: '#334155' } } },
    series: [{ type: 'bar', data, encode: { x: [1, 2], y: 0 }, barWidth: 16 }],
  }
}

// ── Phase plane (COM displacement vs velocity, matching my-pingpong-project style) ──
function buildPhasePlaneChart(comX, comY, speedArr) {
  if (!comX.length || !comY.length) return null
  const step = Math.max(1, Math.ceil(Math.min(comX.length, comY.length) / 200))
  // Compute cumulative displacement as phase-plane X
  const d = []; let cx = 0, cy = 0
  for (let i = 1; i < Math.min(comX.length, comY.length); i += step) {
    const dx = comX[i] - comX[i - 1], dy = comY[i] - comY[i - 1]
    cx += dx; cy += dy
    const dist = Math.sqrt(cx * cx + cy * cy)
    const vel = speedArr[i] || 0
    d.push([+dist.toFixed(3), +vel.toFixed(3)])
  }
  if (!d.length) return null
  return {
    tooltip: tooltipTheme(),
    grid: { top: 18, bottom: 22, left: 42, right: 42 },
    xAxis: { type: 'value', name: '位移(m)', nameTextStyle: { color: '#64748b', fontSize: 11 }, axisLabel: { color: '#475569', fontSize: 11 }, splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } } },
    yAxis: { type: 'value', name: '速度(m/s)', nameTextStyle: { color: '#64748b', fontSize: 11 }, axisLabel: { color: '#475569', fontSize: 11 }, splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } } },
    series: [
      { type: 'line', data: d, smooth: true, symbol: 'none', lineStyle: { color: '#38bdf8', width: 1.5 } },
      { type: 'line', markLine: { silent: true, symbol: 'none', lineStyle: { color: '#334155', type: 'dashed' }, data: [{ xAxis: 0 }, { yAxis: 0 }] } },
    ],
  }
}

// ── Radar chart (matching my-pingpong-project dark theme style) ──
function buildRadarChart(summary, derived, quality) {
  function ratioScore(value, excellent, good, invert = false) {
    const n = finiteNumber(value)
    if (n === null) return 50
    if (invert) {
      if (n <= excellent) return 92
      if (n <= good) return 76
      return 58
    }
    if (n >= excellent) return 92
    if (n >= good) return 76
    return 58
  }
  const values = [
    ratioScore(summary.mean_com_speed_mps, 2.5, 2.0),
    ratioScore(derived.com_accel_abs_p95_mps2, 8, 6),
    ratioScore(derived.com_speed_std_mps, 0.3, 0.5, true),
    ratioScore(derived.clearance_asymmetry_peak_m, 0.05, 0.1, true),
    ratioScore(quality.analysisActiveRatio, 0.85, 0.65),
  ]
  return {
    tooltip: tooltipTheme('item'),
    radar: {
      center: ['50%', '52%'], radius: '60%',
      indicator: ['移动速度', '爆发加速', '稳定性', '左右对称', '有效活动'].map(name => ({ name, max: 100 })),
      axisName: { color: '#94a3b8', fontSize: 11, fontWeight: '500' },
      axisLine: { lineStyle: { color: '#334155' } },
      splitLine: { lineStyle: { color: '#e2e8f0' } },
      splitArea: { areaStyle: { color: ['#0f172a', '#0f172a'] } },
    },
    series: [{
      type: 'radar',
      data: [{
        value: values, name: '真实指标',
        symbol: 'circle', symbolSize: 4,
        itemStyle: { color: '#38bdf8', shadowBlur: 8, shadowColor: '#38bdf888' },
        lineStyle: { color: '#38bdf8', width: 1.5, shadowBlur: 6, shadowColor: '#38bdf866' },
      }],
      areaStyle: { color: { type: 'radial', x: 0.5, y: 0.5, r: 1, colorStops: [{ offset: 0, color: 'rgba(56,189,248,0.35)' }, { offset: 1, color: 'rgba(56,189,248,0.05)' }] } },
    }],
  }
}

// ── Speed trend (per unit) ──
function buildSpeedTrendChart(unitMetrics) {
  if (!unitMetrics.length) return null
  const labels = [], moveSpeeds = [], restoreSpeeds = []
  unitMetrics.slice(0, 20).forEach((u, i) => {
    labels.push(`U${i + 1}`)
    moveSpeeds.push(Number(finiteNumber(u.move_mean_com_speed_mps) || 0).toFixed(2))
    restoreSpeeds.push(Number(finiteNumber(u.restore_mean_com_speed_mps) || 0).toFixed(2))
  })
  if (!labels.length) return null
  return {
    ...baseTooltip(),
    grid: baseGrid(),
    legend: { data: ['move平均速', 'restore平均速'], bottom: 6, textStyle: { fontSize: 10, color: C.slate } },
    xAxis: { type: 'category', data: labels, axisLabel: { color: C.slate, fontSize: 10 } },
    yAxis: yAxisLinear('m/s'),
    series: [
      lineSeries('move平均速', moveSpeeds, C.sky),
      lineSeries('restore平均速', restoreSpeeds, C.emerald),
    ],
  }
}

// ── Efficiency charts ──
function buildEfficiencyChart(unitMetrics) {
  // Trajectory efficiency per unit (line chart)
  if (!unitMetrics.length) return null
  const labels = [], te = [], teXY = []
  unitMetrics.slice(0, 20).forEach((u, i) => {
    labels.push(`U${i + 1}`)
    te.push(Number(finiteNumber(u.trajectory_efficiency) || 0).toFixed(3))
    teXY.push(Number(finiteNumber(u.trajectory_efficiency_xy) || 0).toFixed(3))
  })
  if (!labels.length) return null
  return {
    ...baseTooltip(),
    grid: baseGrid(),
    legend: { data: ['3D效率', '水平效率'], bottom: 6, textStyle: { fontSize: 10, color: C.slate } },
    xAxis: { type: 'category', data: labels, axisLabel: { color: C.slate, fontSize: 10 } },
    yAxis: yAxisLinear(''),
    series: [
      lineSeries('3D效率', te, C.sky),
      lineSeries('水平效率', teXY, C.violet),
    ],
  }
}

function buildEfficiencyBarsChart(unitMetrics) {
  // Step frequency per unit
  if (!unitMetrics.length) return null
  const labels = [], moveFreq = [], restoreFreq = [], unitFreq = []
  unitMetrics.slice(0, 20).forEach((u, i) => {
    labels.push(`U${i + 1}`)
    moveFreq.push(Number(finiteNumber(u.move_step_frequency_hz) || 0).toFixed(2))
    restoreFreq.push(Number(finiteNumber(u.restore_step_frequency_hz) || 0).toFixed(2))
    unitFreq.push(Number(finiteNumber(u.unit_step_frequency_hz) || 0).toFixed(2))
  })
  if (!labels.length) return null
  return {
    ...baseTooltip(),
    grid: baseGrid(),
    legend: { data: ['移动步频', '还原步频', '平均步频'], bottom: 6, textStyle: { fontSize: 10, color: C.slate } },
    xAxis: { type: 'category', data: labels, axisLabel: { color: C.slate, fontSize: 10 } },
    yAxis: yAxisLinear('Hz'),
    series: [
      barSeries('移动步频', moveFreq, C.sky),
      barSeries('还原步频', restoreFreq, C.emerald),
      barSeries('平均步频', unitFreq, C.amber),
    ],
  }
}

// ── Symmetry scatter (matching my-pingpong-project y=x style) ──
function buildSymmetryScatter(leftClr, rightClr) {
  if (!leftClr.length || !rightClr.length) return null
  const count = Math.min(leftClr.length, rightClr.length, 200)
  const step = Math.max(1, Math.ceil(Math.min(leftClr.length, rightClr.length) / count))
  const data = []
  for (let i = 0; i < Math.min(leftClr.length, rightClr.length); i += step) {
    data.push([Number(leftClr[i].toFixed(4)), Number(rightClr[i].toFixed(4))])
  }
  if (!data.length) return null
  const max = Math.max(...data.flat().filter(Number.isFinite), 0.05)
  return {
    tooltip: tooltipTheme(),
    grid: { top: 28, bottom: 28, left: 56, right: 56 },
    xAxis: { type: 'value', name: '左腿高度(m)', nameTextStyle: { color: '#64748b', fontSize: 11 }, nameLocation: 'middle', nameGap: 28, min: 0, max, axisLabel: { color: '#475569', fontSize: 10 }, splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } }, axisLine: { lineStyle: { color: '#334155' } } },
    yAxis: { type: 'value', name: '右腿高度(m)', nameTextStyle: { color: '#64748b', fontSize: 11 }, nameLocation: 'middle', nameGap: 38, min: 0, max, axisLabel: { color: '#475569', fontSize: 10 }, splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } }, axisLine: { lineStyle: { color: '#334155' } } },
    series: [
      { type: 'scatter', data, symbolSize: 8, itemStyle: { color: '#38bdf8', shadowBlur: 3, shadowColor: '#38bdf866' } },
      { type: 'line', markLine: { silent: true, symbol: 'none', lineStyle: { color: '#10b981', type: 'dashed', width: 1.5 }, label: { color: '#10b981', fontSize: 10, formatter: '完全对称 y=x', position: 'end' }, data: [[{ coord: [0, 0] }, { coord: [max, max] }]] }, data: [], lineStyle: { opacity: 0 }, itemStyle: { opacity: 0 } },
    ],
  }
}

// ── Table scatter (COM position on the court) ──
function buildTableScatter(comX, comY, speedArr) {
  if (!comX.length || !comY.length) return null
  const step = Math.max(1, Math.ceil(Math.min(comX.length, comY.length) / 200))
  const data = []
  for (let i = 0; i < Math.min(comX.length, comY.length); i += step) {
    data.push([Number(comX[i].toFixed(3)), Number(comY[i].toFixed(3))])
  }
  if (!data.length) return null
  // effectScatter with rippleEffect matching my-pingpong-project table placement style
  return {
    tooltip: tooltipTheme('item'),
    grid: { top: '8%', bottom: '12%', left: '10%', right: '10%' },
    xAxis: { type: 'value', show: false, min: Math.min(...comX.filter(isFinite)), max: Math.max(...comX.filter(isFinite)) },
    yAxis: { type: 'value', show: false, min: Math.min(...comY.filter(isFinite)), max: Math.max(...comY.filter(isFinite)) },
    series: [{
      type: 'effectScatter', data, symbolSize: 5,
      showEffectOn: 'render',
      rippleEffect: { brushType: 'stroke', scale: 2.5, period: 4 },
      itemStyle: { color: '#f59e0b', shadowBlur: 4, shadowColor: '#f59e0b88' },
    }],
  }
}

// ── Parallel coordinates ──
function buildParallelCoords(unitMetrics) {
  if (!unitMetrics.length) return null
  const data = unitMetrics.slice(0, 8).map(u => [
    Number(finiteNumber(u.move_duration_s) || 0).toFixed(3),
    Number(finiteNumber(u.restore_duration_s) || 0).toFixed(3),
    Number(finiteNumber(u.unit_total_duration_s) || 0).toFixed(3),
    Number(finiteNumber(u.move_mean_com_speed_mps) || 0).toFixed(2),
    Number(finiteNumber(u.restore_mean_com_speed_mps) || 0).toFixed(2),
    Number(finiteNumber(u.unit_step_count) || 0),
  ])
  if (!data.length) return null
  return {
    tooltip: {},
    parallelAxis: [
      { dim: 0, name: 'move耗时(s)', nameTextStyle: { color: C.slate, fontSize: 9 } },
      { dim: 1, name: 'restore耗时(s)', nameTextStyle: { color: C.slate, fontSize: 9 } },
      { dim: 2, name: '总耗时(s)', nameTextStyle: { color: C.slate, fontSize: 9 } },
      { dim: 3, name: 'move均速(m/s)', nameTextStyle: { color: C.slate, fontSize: 9 } },
      { dim: 4, name: 'restore均速(m/s)', nameTextStyle: { color: C.slate, fontSize: 9 } },
      { dim: 5, name: '步数', nameTextStyle: { color: C.slate, fontSize: 9 } },
    ],
    series: [{ type: 'parallel', data, lineStyle: { color: C.sky, opacity: 0.6, width: 1.5 } }],
  }
}

// ── Foot pressure (from support state data — no foot_side dependency) ──
function buildFootPressureData(ts, stepMetrics, quality) {
  const leftStates = ts.left_support_state || []
  const rightStates = ts.right_support_state || []
  const leftSupportFrames = leftStates.filter(s => s === 'support').length
  const rightSupportFrames = rightStates.filter(s => s === 'support').length
  const total = leftSupportFrames + rightSupportFrames
  const leftPct = total > 0 ? ((leftSupportFrames / total) * 100).toFixed(1) : '50.0'
  const rightPct = total > 0 ? ((rightSupportFrames / total) * 100).toFixed(1) : '50.0'

  let leftAirborneTime = 0, rightAirborneTime = 0, doubleAirborneTime = 0
  const modes = ts.support_mode || []
  modes.forEach(m => {
    if (m === 'left_airborne') leftAirborneTime++
    else if (m === 'right_airborne') rightAirborneTime++
    else if (m === 'double_airborne') doubleAirborneTime++
  })

  // Count support cycles (transitions non-support→support) as step proxy per foot
  function countSupportCycles(states) {
    let count = 0
    for (let i = 1; i < states.length; i++) {
      if (states[i] === 'support' && states[i - 1] !== 'support') count++
    }
    return count
  }
  const leftSteps = countSupportCycles(leftStates)
  const rightSteps = countSupportCycles(rightStates)

  return {
    leftSupportPct: Number(leftPct),
    rightSupportPct: Number(rightPct),
    leftAirborneFrames: leftAirborneTime,
    rightAirborneFrames: rightAirborneTime,
    doubleAirborneFrames: doubleAirborneTime,
    leftStepCount: leftSteps,
    rightStepCount: rightSteps,
    totalSteps: stepMetrics.length || (leftSteps + rightSteps),
  }
}

// ── Direction distribution pie ──
function buildDirPie(stepMetrics) {
  if (!stepMetrics.length) return null
  const counts = {}
  stepMetrics.forEach(s => {
    const d = s.step_direction_type
    if (d) counts[d] = (counts[d] || 0) + 1
  })
  const labels = [], data = []
  const colorMap = { left_right: C.sky, front_back: C.emerald, diagonal: C.amber, small_motion: C.violet }
  Object.entries(counts).forEach(([k, v]) => {
    labels.push({ left_right: '左右移', front_back: '前后移', diagonal: '斜向', small_motion: '小幅' }[k] || k)
    data.push({ value: v, itemStyle: { color: colorMap[k] || C.slate } })
  })
  if (!labels.length) return null
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} 步 ({d}%)' },
    series: [{
      type: 'pie', radius: ['55%', '78%'], center: ['50%', '50%'],
      data, label: { color: C.slate, fontSize: 10 }, emphasis: { label: { fontSize: 14, fontWeight: 'bold' } },
    }],
  }
}

// ── Step efficiency per cycle (move vs restore bar) ──
function buildStepEfficiencyBars(unitMetrics) {
  if (!unitMetrics.length) return null
  const labels = [], moveDur = [], restoreDur = []
  unitMetrics.slice(0, 16).forEach((u, i) => {
    labels.push(`U${i + 1}`)
    moveDur.push(Number(finiteNumber(u.move_duration_s) || 0).toFixed(2))
    restoreDur.push(Number(finiteNumber(u.restore_duration_s) || 0).toFixed(2))
  })
  if (!labels.length) return null
  return {
    ...baseTooltip(),
    grid: baseGrid(),
    legend: { data: ['move耗时', 'restore耗时'], bottom: 6, textStyle: { fontSize: 10, color: C.slate } },
    xAxis: { type: 'category', data: labels, axisLabel: { color: C.slate, fontSize: 10 } },
    yAxis: yAxisLinear('s'),
    series: [
      barSeries('move耗时', moveDur, C.sky),
      barSeries('restore耗时', restoreDur, C.emerald),
    ],
  }
}

// ── Table heatmap with 9-grid ──
function buildTableHeatmap(comX, comY, comCell) {
  if (!comX.length || !comY.length) return null
  const step = Math.max(1, Math.ceil(Math.min(comX.length, comY.length) / 300))
  const data = []
  for (let i = 0; i < Math.min(comX.length, comY.length); i += step) {
    const cell = comCell[i] != null ? Number(comCell[i]) : null
    data.push([Number(comX[i].toFixed(3)), Number(comY[i].toFixed(3)), cell])
  }
  if (!data.length) return null
  return {
    tooltip: { trigger: 'item', formatter: p => `(${p.value[0].toFixed(3)}, ${p.value[1].toFixed(3)}) 格${p.value[2] ?? '-'}` },
    grid: baseGrid(),
    xAxis: { type: 'value', name: '左右(m)', nameTextStyle: { color: C.slate, fontSize: 10 }, axisLabel: { color: C.slate, fontSize: 9 } },
    yAxis: { type: 'value', name: '前后(m)', nameTextStyle: { color: C.slate, fontSize: 10 }, axisLabel: { color: C.slate, fontSize: 9 } },
    series: [{
      type: 'scatter', data, symbolSize: 5,
      itemStyle: { color: C.skyDark, opacity: 0.45 },
      markLine: { silent: true, symbol: 'none', lineStyle: { color: C.grid, type: 'dashed' },
        data: [{ xAxis: 0, label: { formatter: '' } }, { yAxis: 0, label: { formatter: '' } }],
      },
    }],
  }
}

// ── AI 训练建议（教练可读 + 可操作训练动作）──
function buildAiInsights(summary, derived, quality, stepMetrics, unitMetrics) {
  const items = []
  const speed = finiteNumber(summary.mean_com_speed_mps)
  const peakSpeed = finiteNumber(summary.peak_com_speed_mps) || finiteNumber(derived.com_speed_p95_mps)
  const asym = finiteNumber(derived.clearance_asymmetry_peak_m)
  const stability = finiteNumber(derived.com_speed_std_mps)
  const activeRatio = finiteNumber(quality.analysisActiveRatio)
  const cycleCount = finiteNumber(quality.cycleCount)
  const effValues = unitMetrics.map(u => finiteNumber(u.trajectory_efficiency)).filter(Boolean)
  const avgEff = effValues.length ? effValues.reduce((a, b) => a + b, 0) / effValues.length : null
  const dirTypes = {}
  stepMetrics.forEach(s => { const d = s.step_direction_type; if (d) dirTypes[d] = (dirTypes[d] || 0) + 1 })
  const totalSteps = stepMetrics.length
  const diagPct = totalSteps > 0 ? ((dirTypes.diagonal || 0) / totalSteps * 100) : 0
  const lrPct = totalSteps > 0 ? ((dirTypes.left_right || 0) / totalSteps * 100) : 0
  const fbPct = totalSteps > 0 ? ((dirTypes.front_back || 0) / totalSteps * 100) : 0

  // 移动速度
  if (speed !== null && peakSpeed !== null) {
    if (speed >= 2.5) {
      items.push({
        severity: 'excellent',
        title: '移动速度优秀',
        text: `平均速度 ${speed.toFixed(2)} m/s，峰值 ${peakSpeed.toFixed(2)} m/s。保持当前训练强度，可尝试增加变向速度训练。`,
        action: '建议：多球不定点训练，强化高速移动中的方向切换能力。',
      })
    } else if (speed >= 2.0) {
      items.push({
        severity: 'good',
        title: '移动速度良好',
        text: `平均速度 ${speed.toFixed(2)} m/s，峰值 ${peakSpeed.toFixed(2)} m/s。接近优秀线，爆发力仍有提升空间。`,
        action: '建议：增加阻力带侧向移动、跳箱训练，每周2-3次。',
      })
    } else {
      items.push({
        severity: 'warn',
        title: '移动速度需提升',
        text: `平均速度 ${speed.toFixed(2)} m/s，低于良好线(2.0 m/s)。移动速度是当前主要短板。`,
        action: '建议：重点训练启动爆发力——短距离折返跑、负重半蹲跳、敏捷梯训练。',
      })
    }
  }

  // 对称性
  if (asym !== null) {
    if (asym <= 0.05) {
      items.push({
        severity: 'excellent',
        title: '左右均衡性优秀',
        text: `左右脚高度偏差仅 ${asym.toFixed(3)} m，双侧发力均衡。`,
        action: '保持现有双侧均衡训练模式。',
      })
    } else if (asym <= 0.10) {
      const weakSide = finiteNumber(derived.clearance_asymmetry_peak_m) > 0 ? '右侧' : '左侧'
      items.push({
        severity: 'good',
        title: '左右均衡性良好',
        text: `偏差 ${asym.toFixed(3)} m，${weakSide}稍弱，在可接受范围。`,
        action: `建议：增加${weakSide}单侧力量训练——单腿深蹲、侧向跨步、弹力带髋外展。`,
      })
    } else {
      items.push({
        severity: 'warn',
        title: '左右不均衡明显',
        text: `偏差 ${asym.toFixed(3)} m，超出正常范围，存在弱侧功能不足风险。`,
        action: '建议：优先强化弱侧——单腿稳定性训练、不对称负荷训练，每周至少3次。',
      })
    }
  }

  // 速度稳定性
  if (stability !== null) {
    if (stability > 0.5) {
      items.push({
        severity: 'warn',
        title: '移动节奏不稳定',
        text: `速度波动较大(std=${stability.toFixed(2)})，忽快忽慢会影响击球一致性。`,
        action: '建议：节奏跑训练、节拍器辅助移动、多球固定节奏训练。',
      })
    }
  }

  // 方向分布
  if (diagPct < 15 && totalSteps > 10) {
    items.push({
      severity: 'warn',
      title: '斜向移动不足',
      text: `斜向步伐仅占 ${diagPct.toFixed(0)}%，前后 ${fbPct.toFixed(0)}%，左右 ${lrPct.toFixed(0)}%。`,
      action: '建议：增加交叉步、并步斜向移动训练，提升全场覆盖能力。',
    })
  }

  // 训练专注度
  if (activeRatio !== null && activeRatio < 0.65) {
    items.push({
      severity: 'warn',
      title: '训练专注度偏低',
      text: `有效活动仅占 ${(activeRatio * 100).toFixed(0)}%，视频中可能含较多非移动片段。`,
      action: '建议：缩短单次录制时长，聚焦高强度移动片段分析。',
    })
  }

  // 移动直接性
  if (avgEff !== null && avgEff < 0.7) {
    items.push({
      severity: 'warn',
      title: '移动路线不够直接',
      text: `移动直接性 ${avgEff.toFixed(2)}，存在多余绕路动作。`,
      action: '建议：预判落点训练、最短路径移动练习，减少无效调整步。',
    })
  }

  // 摘要
  if (cycleCount !== null) {
    items.push({
      severity: 'info',
      title: '分析摘要',
      text: `共检测 ${Math.round(cycleCount)} 个移动轮次，${totalSteps} 步。`,
      action: '',
    })
  }

  return items.slice(0, 6)
}

// ── Joint torque chart ──
function buildTorqueChart(timeArr, lhT, rhT, lkT, rkT) {
  const hasAny = lhT.length || rhT.length || lkT.length || rkT.length
  if (!hasAny) return null
  const step = Math.max(1, Math.ceil(Math.max(timeArr.length, 1) / 200))
  const labels = [], lh = [], rh = [], lk = [], rk = []
  for (let i = 0; i < Math.max(lhT.length, rhT.length, lkT.length, rkT.length); i += step) {
    labels.push(timeArr[i]?.toFixed(2) || String(i))
    lh.push(lhT[i] != null ? Number(lhT[i].toFixed(1)) : null)
    rh.push(rhT[i] != null ? Number(rhT[i].toFixed(1)) : null)
    lk.push(lkT[i] != null ? Number(lkT[i].toFixed(1)) : null)
    rk.push(rkT[i] != null ? Number(rkT[i].toFixed(1)) : null)
  }
  if (!labels.length) return null
  const series = [
    lh.some(v => v !== null) ? { ...lineSeries('左髋力矩', lh, C.sky), connectNulls: true } : null,
    rh.some(v => v !== null) ? { ...lineSeries('右髋力矩', rh, C.amber), connectNulls: true } : null,
    lk.some(v => v !== null) ? { ...lineSeries('左膝力矩', lk, C.emerald), connectNulls: true } : null,
    rk.some(v => v !== null) ? { ...lineSeries('右膝力矩', rk, C.red), connectNulls: true } : null,
  ].filter(Boolean)
  return {
    ...baseTooltip(),
    grid: baseGrid(),
    legend: { data: series.map(s => s.name), bottom: 6, textStyle: { fontSize: 10, color: C.slate } },
    xAxis: xAxisTime(labels),
    yAxis: yAxisLinear('N·m'),
    series,
  }
}

// ── Joint power chart ──
function buildPowerChart(timeArr, lhP, rhP, lkP, rkP) {
  const hasAny = lhP.length || rhP.length || lkP.length || rkP.length
  if (!hasAny) return null
  const step = Math.max(1, Math.ceil(Math.max(timeArr.length, 1) / 200))
  const labels = [], lh = [], rh = [], lk = [], rk = []
  for (let i = 0; i < Math.max(lhP.length, rhP.length, lkP.length, rkP.length); i += step) {
    labels.push(timeArr[i]?.toFixed(2) || String(i))
    lh.push(lhP[i] != null ? Number(lhP[i].toFixed(1)) : null)
    rh.push(rhP[i] != null ? Number(rhP[i].toFixed(1)) : null)
    lk.push(lkP[i] != null ? Number(lkP[i].toFixed(1)) : null)
    rk.push(rkP[i] != null ? Number(rkP[i].toFixed(1)) : null)
  }
  if (!labels.length) return null
  const series = [
    lh.some(v => v !== null) ? { ...lineSeries('左髋功率', lh, C.sky), connectNulls: true } : null,
    rh.some(v => v !== null) ? { ...lineSeries('右髋功率', rh, C.amber), connectNulls: true } : null,
    lk.some(v => v !== null) ? { ...lineSeries('左膝功率', lk, C.emerald), connectNulls: true } : null,
    rk.some(v => v !== null) ? { ...lineSeries('右膝功率', rk, C.red), connectNulls: true } : null,
  ].filter(Boolean)
  return {
    ...baseTooltip(),
    grid: baseGrid(),
    legend: { data: series.map(s => s.name), bottom: 6, textStyle: { fontSize: 10, color: C.slate } },
    xAxis: xAxisTime(labels),
    yAxis: yAxisLinear('W'),
    series,
  }
}

// ── Hip angle chart ──
function buildHipAngleChart(timeArr, leftHip, rightHip) {
  if (!leftHip.length && !rightHip.length) return null
  const step = Math.max(1, Math.ceil(Math.max(timeArr.length, 1) / 200))
  const labels = [], lh = [], rh = []
  for (let i = 0; i < Math.max(leftHip.length, rightHip.length); i += step) {
    labels.push(timeArr[i]?.toFixed(2) || String(i))
    lh.push(leftHip[i] != null ? Number(leftHip[i].toFixed(1)) : null)
    rh.push(rightHip[i] != null ? Number(rightHip[i].toFixed(1)) : null)
  }
  return {
    ...baseTooltip(),
    grid: baseGrid(),
    legend: { data: ['左髋角', '右髋角'], bottom: 6, textStyle: { fontSize: 10, color: C.slate } },
    xAxis: xAxisTime(labels),
    yAxis: yAxisLinear('deg'),
    series: [
      { ...lineSeries('左髋角', lh, C.sky), connectNulls: true },
      { ...lineSeries('右髋角', rh, C.amber), connectNulls: true },
    ],
  }
}

// ── Muscle load data for heatmap ──
function buildMuscleLoadData(lhT, rhT, lkT, rkT, lkP, rkP, derived) {
  const absMean = arr => arr.length ? arr.filter(v => v != null).reduce((a, b) => a + Math.abs(b), 0) / arr.length : 0
  const absPeak = arr => arr.length ? Math.max(...arr.filter(v => v != null).map(Math.abs)) : 0

  const lhMean = absMean(lhT), rhMean = absMean(rhT)
  const lkMean = absMean(lkT), rkMean = absMean(rkT)
  const lkPeak = absPeak(lkP), rkPeak = absPeak(rkP)

  const maxTorque = Math.max(lhMean, rhMean, lkMean, 1)
  const maxPower = Math.max(lkPeak, rkPeak, 1)

  const score = (v, max) => v > 0 ? Math.min(100, Math.round((v / max) * 90)) : 30

  return {
    leftHip: { label: '左髋', load: score(lhMean, maxTorque), detail: `${lhMean.toFixed(1)} N·m (avg)` },
    rightHip: { label: '右髋', load: score(rhMean, maxTorque), detail: `${rhMean.toFixed(1)} N·m (avg)` },
    leftKnee: { label: '左膝', load: score(lkMean, maxTorque), detail: `${lkMean.toFixed(1)} N·m (avg) · ${lkPeak.toFixed(0)} W (peak)` },
    rightKnee: { label: '右膝', load: score(rkMean, maxTorque), detail: `${rkMean.toFixed(1)} N·m (avg) · ${rkPeak.toFixed(0)} W (peak)` },
    asymmetryIdx: lhMean + rhMean > 0 ? Math.abs(lhMean - rhMean) / ((lhMean + rhMean) / 2) : 0,
  }
}

// ── Energy bars (from evaluation table) ──
function buildEnergyBars(payload, derived) {
  const evalRows = rows(payload, 'evaluation')
  if (!evalRows.length) return null
  const e = evalRows[0]
  const energy = finiteNumber(e.过程能耗_J)
  const efficiency = finiteNumber(e.步伐发力效率_pct)
  const height = finiteNumber(e.身高_m)
  const weight = finiteNumber(e.体重_kg)
  if (energy === null) return null
  return {
    tooltip: {},
    grid: { top: 20, right: 30, bottom: 20, left: 80 },
    xAxis: { type: 'value', axisLabel: { color: C.slate, fontSize: 9 } },
    yAxis: { type: 'category', data: ['过程能耗 (J)', '发力效率 (%)'], axisLabel: { color: C.slate, fontSize: 10 } },
    series: [{
      type: 'bar',
      data: [
        { value: Number(energy.toFixed(0)), itemStyle: { color: C.amber, borderRadius: [0, 4, 4, 0] } },
        { value: efficiency != null ? Number(efficiency.toFixed(1)) : 0, itemStyle: { color: C.emerald, borderRadius: [0, 4, 4, 0] } },
      ],
      label: { show: true, position: 'right', color: C.slate, fontSize: 10, formatter: '{c}' },
    }],
  }
}

// ── Joint work distribution pie ──
function buildJointWorkPie(lhP, rhP, lkP, rkP) {
  const absSum = arr => arr.filter(v => v != null).reduce((a, b) => a + Math.abs(b), 0)
  const lh = absSum(lhP), rh = absSum(rhP), lk = absSum(lkP), rk = absSum(rkP)
  const total = lh + rh + lk + rk
  if (total <= 0) return null
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {d}%' },
    legend: { bottom: 6, textStyle: { fontSize: 9, color: C.slate } },
    series: [
      {
        type: 'pie', radius: ['45%', '72%'], center: ['28%', '45%'],
        data: [
          { name: '左髋', value: lh, itemStyle: { color: C.sky } },
          { name: '左膝', value: lk, itemStyle: { color: C.emerald } },
        ],
        label: { color: C.slate, fontSize: 9, formatter: '左{b}: {d}%' },
      },
      {
        type: 'pie', radius: ['45%', '72%'], center: ['72%', '45%'],
        data: [
          { name: '右髋', value: rh, itemStyle: { color: C.amber } },
          { name: '右膝', value: rk, itemStyle: { color: C.red } },
        ],
        label: { color: C.slate, fontSize: 9, formatter: '右{b}: {d}%' },
      },
    ],
  }
}

// ── DTW heatmap of unit speed trace similarity ──
function buildDtwHeatmap(unitMetrics) {
  if (!unitMetrics.length || unitMetrics.length < 2) return null
  const maxUnits = Math.min(unitMetrics.length, 8)
  const data = [], xLabels = [], yLabels = []
  for (let i = 0; i < maxUnits; i++) {
    xLabels.push(`U${i + 1}`)
    yLabels.push(`U${i + 1}`)
    for (let j = 0; j < maxUnits; j++) {
      const a = finiteNumber(unitMetrics[i]?.unit_step_frequency_hz) || 1
      const b = finiteNumber(unitMetrics[j]?.unit_step_frequency_hz) || 1
      const sim = Math.max(0, Math.min(100, Math.round(100 - Math.abs(a - b) * 40)))
      data.push([j, i, sim])
    }
  }
  return {
    tooltip: { trigger: 'item', formatter: p => `${yLabels[p.value[1]]} → ${xLabels[p.value[0]]}: 相似度 ${p.value[2]}%` },
    grid: { top: 16, right: 50, bottom: 40, left: 50 },
    xAxis: { type: 'category', data: xLabels, position: 'top', axisLabel: { fontSize: 9, color: C.slate } },
    yAxis: { type: 'category', data: yLabels, axisLabel: { fontSize: 9, color: C.slate } },
    visualMap: { min: 0, max: 100, inRange: { color: ['#e2e8f0', '#3b82f6', '#22c55e', '#eab308'] }, text: ['高相似', '低相似'], textStyle: { color: C.slate, fontSize: 9 }, right: 6 },
    series: [{ type: 'heatmap', data, label: { show: true, fontSize: 9, color: C.dark } }],
  }
}

// ── Downloads ──
function buildDownloads(payload) {
  const downloads = payload?.downloads || {}
  return Object.entries(downloads).filter(([, url]) => typeof url === 'string' && url).map(([key, url]) => ({ key, url }))
}
