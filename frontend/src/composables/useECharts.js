/**
 * Shared ECharts lifecycle composable with runtime diagnostics.
 *
 * In dev mode: console.warn on empty/dimensionless charts.
 * In production: collects diagnostic info silently for debugging.
 */
import { onBeforeUnmount, reactive } from 'vue'
import * as echarts from 'echarts'

const isDev = typeof import.meta !== 'undefined' && import.meta.env?.DEV

export function useECharts(options = {}) {
  const charts = []
  let resizeTimer = null
  const diagnostics = reactive({ warnings: [], errors: [] })

  function _warn(msg, dom) {
    const entry = { msg, time: Date.now() }
    diagnostics.warnings.push(entry)
    if (isDev) console.warn('[ECharts]', msg, dom || '')
  }

  function onResize() {
    clearTimeout(resizeTimer)
    resizeTimer = setTimeout(() => {
      charts.forEach(c => {
        try { c.resize() } catch {}
      })
    }, options.resizeDebounce || 200)
  }

  window.addEventListener('resize', onResize)

  function initChart(dom, option, initOpts = {}) {
    if (!dom) {
      _warn('initChart: DOM 元素为空 — 图表无法挂载')
      return null
    }

    const rect = dom.getBoundingClientRect()
    if (rect.width === 0 || rect.height === 0) {
      _warn(`容器尺寸为零 (${rect.width}x${rect.height}) — 图表不可见`, dom)
    }

    if (!option) {
      _warn('option 为空 — 图表将完全空白', dom)
      return null
    }

    // Check if series has actual data
    const series = option.series || []
    const hasValidData = series.some(s => {
      if (!s) return false
      if (s.data && Array.isArray(s.data) && s.data.length > 0) return true
      if (s.type === 'pie' && s.data && Array.isArray(s.data) && s.data.length > 0) return true
      return false
    })
    if (!hasValidData && series.length > 0) {
      _warn('图表有 series 定义但数据为空 — 可能显示空白', dom)
    }

    const instance = echarts.init(dom)
    instance.setOption(option, initOpts)
    charts.push(instance)
    return instance
  }

  function disposeAll() {
    window.removeEventListener('resize', onResize)
    charts.forEach(c => {
      try { c.dispose() } catch {}
    })
    charts.length = 0
  }

  onBeforeUnmount(() => { disposeAll() })

  return { initChart, disposeAll, diagnostics }
}

/**
 * Check if a chart data object has meaningful (non-zero) values.
 * Used to distinguish "object exists but all zeros" from "real data".
 */
export function hasChartData(obj, key = null) {
  if (!obj) return false
  if (key) {
    const v = obj[key]
    if (v == null) return false
    if (typeof v === 'number') return v > 0
    return true
  }
  // For objects like muscleLoad: check at least one numeric value > 0
  if (typeof obj === 'object') {
    return Object.values(obj).some(v => {
      if (typeof v === 'number') return v > 0
      if (typeof v === 'object' && v !== null) {
        return Object.values(v).some(vv => typeof vv === 'number' && vv > 0)
      }
      return false
    })
  }
  return true
}
