/** Canvas 雷达图绘制：多报告指标对比，原生 Canvas 无第三方依赖。 */
const PALETTE = [
  { stroke: '#2563eb', fill: 'rgba(37,99,235,0.12)' },
  { stroke: '#f59e0b', fill: 'rgba(245,158,11,0.12)' },
  { stroke: '#10b981', fill: 'rgba(16,185,129,0.12)' },
  { stroke: '#8b5cf6', fill: 'rgba(139,92,246,0.12)' },
  { stroke: '#ef4444', fill: 'rgba(239,68,68,0.12)' },
  { stroke: '#ec4899', fill: 'rgba(236,72,153,0.12)' },
]

export function useRadarChart(canvasRef, options = {}) {
  const AXES = options.axes || ['平均速度', '对称性', '循环数', '峰值加速度', '总时长']
  const SIZE = options.size || 340
  const PADDING = options.padding || 56
  const MAX_NORMALIZED = options.max || 100
  const LEVELS = options.levels || 5

  function draw(reports) {
    const canvas = canvasRef.value
    if (!canvas || !reports.length) return
    const ctx = canvas.getContext('2d')
    const dpr = window.devicePixelRatio || 1
    canvas.width = SIZE * dpr
    canvas.height = SIZE * dpr
    canvas.style.width = SIZE + 'px'
    canvas.style.height = SIZE + 'px'
    ctx.scale(dpr, dpr)

    const cx = SIZE / 2
    const cy = SIZE / 2
    const radius = (SIZE - PADDING * 2) / 2
    const angleStep = (Math.PI * 2) / AXES.length

    ctx.clearRect(0, 0, SIZE, SIZE)

    // 同心多边形网格（5层），最外层加粗为参考线
    for (let lvl = 1; lvl <= LEVELS; lvl++) {
      ctx.beginPath()
      for (let i = 0; i < AXES.length; i++) {
        const r = (radius / LEVELS) * lvl
        const x = cx + r * Math.cos(angleStep * i - Math.PI / 2)
        const y = cy + r * Math.sin(angleStep * i - Math.PI / 2)
        if (i === 0) ctx.moveTo(x, y)
        else ctx.lineTo(x, y)
      }
      ctx.closePath()
      ctx.strokeStyle = lvl === LEVELS ? '#cbd5e1' : '#e8ecf1'
      ctx.lineWidth = lvl === LEVELS ? 1.5 : 0.5
      ctx.stroke()
    }

    // axes
    for (let i = 0; i < AXES.length; i++) {
      const x = cx + radius * Math.cos(angleStep * i - Math.PI / 2)
      const y = cy + radius * Math.sin(angleStep * i - Math.PI / 2)
      ctx.beginPath()
      ctx.moveTo(cx, cy)
      ctx.lineTo(x, y)
      ctx.strokeStyle = '#e2e8f0'
      ctx.lineWidth = 0.5
      ctx.stroke()

      // labels
      const lx = cx + (radius + 16) * Math.cos(angleStep * i - Math.PI / 2)
      const ly = cy + (radius + 16) * Math.sin(angleStep * i - Math.PI / 2)
      ctx.font = '11px "DM Mono", "Courier New", monospace'
      ctx.fillStyle = '#64748b'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(AXES[i], lx, ly)
    }

    // 每条报告绘制一个半透明多边形 + 数据点
    reports.forEach((report, idx) => {
      const palette = PALETTE[idx % PALETTE.length]
      ctx.beginPath()
      AXES.forEach((axis, i) => {
        const val = getMetricValue(report, axis)
        const normalized = Math.min(MAX_NORMALIZED, Math.max(0, val))
        const r = (normalized / MAX_NORMALIZED) * radius
        const x = cx + r * Math.cos(angleStep * i - Math.PI / 2)
        const y = cy + r * Math.sin(angleStep * i - Math.PI / 2)
        if (i === 0) ctx.moveTo(x, y)
        else ctx.lineTo(x, y)

        // dot
        ctx.save()
        ctx.fillStyle = palette.stroke
        ctx.beginPath()
        ctx.arc(x, y, 3, 0, Math.PI * 2)
        ctx.fill()
        ctx.restore()
      })
      ctx.closePath()
      ctx.fillStyle = palette.fill
      ctx.fill()
      ctx.strokeStyle = palette.stroke
      ctx.lineWidth = 2
      ctx.stroke()
    })

    // legend
    const legendY = SIZE - 14
    let legendX = 12
    ctx.font = '11px "DM Sans", "Microsoft YaHei", sans-serif'
    reports.forEach((report, idx) => {
      const palette = PALETTE[idx % PALETTE.length]
      ctx.fillStyle = palette.stroke
      ctx.beginPath()
      ctx.arc(legendX + 4, legendY, 4, 0, Math.PI * 2)
      ctx.fill()
      ctx.fillStyle = '#334155'
      ctx.textAlign = 'start'
      ctx.textBaseline = 'middle'
      const label = (report.stepName || '报告') + (report.date ? ' ' + report.date : '')
      const w = ctx.measureText(label).width
      ctx.fillText(label, legendX + 12, legendY)
      legendX += w + 28
    })
  }

  function getMetricValue(report, axis) {
    const s = report.summary || {}
    const map = { '平均速度': s.avgSpeed, '对称性': s.symmetry, '循环数': s.loops, '峰值加速度': s.peakAccel, '总时长': s.totalTime }
    const v = Number(map[axis])
    return Number.isFinite(v) ? v : 0
  }

  return { draw }
}
