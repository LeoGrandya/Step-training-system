/**
 * Shared ECharts lifecycle composable.
 *
 * Usage in report components:
 *   const { initChart, disposeAll } = useECharts()
 *   onMounted(() => { initChart(ref.value, option) })
 *   watch(sources, () => { disposeAll(); /* re-init all charts *&#47; })
 *   // disposeAll is auto-registered in onBeforeUnmount
 */
import { onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

export function useECharts(options = {}) {
  const charts = []
  let resizeTimer = null

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
    if (!dom) return null
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

  return { initChart, disposeAll }
}
