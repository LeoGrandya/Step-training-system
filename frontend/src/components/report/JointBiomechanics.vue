<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-lg glow-border-sky">
    <h3 class="text-slate-800 text-base font-semibold mb-3 flex items-center gap-2">
      <span class="w-1.5 h-1.5 rounded-full bg-pink-500 animate-pulse"></span>
      五、关节生物力学分析
      <span class="text-xs bg-slate-100 text-slate-400 px-2 py-0.5 rounded-full ml-auto">运动医学</span>
    </h3>
    <p class="text-sm text-slate-400 leading-relaxed mb-3 border-l-2 border-pink-500/30 pl-2.5">膝关节活动范围最大（65°-155°），踝关节相对稳定。ROM雷达图显示左侧关节活动度略优于右侧。角速度峰值出现在蹬伸末期，着地瞬间角加速度提示存在冲击负荷。制动瞬间膝角在段3-4接近理想范围，建议加强右侧关节柔韧性与离心控制能力。</p>
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-3">
      <!-- Row 1: 髋膝踝角度曲线 + ROM雷达图 + 角速度 -->
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">髋/膝/踝角度变化</p>
        <div ref="angleRef" class="w-full h-56"></div>
      </div>
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">左右侧关节活动范围(ROM)对比</p>
        <div ref="romRef" class="w-full h-56 aspect-square mx-auto max-w-[280px]"></div>
      </div>
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">膝关节角速度</p>
        <div ref="angularRef" class="w-full h-56"></div>
      </div>
      <!-- Row 2: 力矩 + 功率 + 髋角 -->
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">髋膝力矩时间序列</p>
        <div ref="torqueRef" class="w-full h-56"></div>
      </div>
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">髋膝功率时间序列</p>
        <div ref="powerRef" class="w-full h-56"></div>
      </div>
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">髋关节角度变化</p>
        <div ref="hipRef" class="w-full h-56"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'
import { tooltipTheme } from '../../utils/chartTheme.js'
import ReportEmptyState from './ReportEmptyState.vue'

const isDev = import.meta.env.DEV

const props = defineProps({
  joint: Object,
  jointAngVel: Object,
  jointRomRadar: Object,
  torqueChart: Object,
  powerChart: Object,
  hipAngleChart: Object
})

const angleRef = ref(null)
const romRef = ref(null)
const angularRef = ref(null)
const torqueRef = ref(null)
const powerRef = ref(null)
const hipRef = ref(null)
const charts = []

const hasJoint = computed(() => !!props.joint)
const hasRom = computed(() => !!props.jointRomRadar)
const hasAngVel = computed(() => !!props.jointAngVel)
const hasTorque = computed(() => !!props.torqueChart)
const hasPower = computed(() => !!props.powerChart)
const hasHip = computed(() => !!props.hipAngleChart)

function dg() { return { top: 22, bottom: 22, left: 46, right: 12 } }
function da() { return { axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#475569', fontSize: 11 }, splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } } } }

function mockJoint() {
  const T = Array.from({ length: 100 }, (_, i) => +(i).toFixed(0))
  const hip = T.map(x => 90 + Math.sin(x * 0.06) * 25 + Math.cos(x * 0.04) * 10 + Math.random() * 3)
  const knee = T.map(x => 120 + Math.sin(x * 0.06 + 1) * 35 + Math.cos(x * 0.05) * 15 + Math.random() * 3)
  const ankle = T.map(x => 95 + Math.sin(x * 0.06 + 2) * 15 + Math.cos(x * 0.04) * 8 + Math.random() * 2)
  return {
    tooltip: tooltipTheme(),
    grid: dg(),
    xAxis: { type: 'category', name: '标准化百分比(%)', nameTextStyle: { color: '#64748b', fontSize: 11 }, data: T, axisLabel: { color: '#475569', fontSize: 10, interval: 19 }, ...da() },
    yAxis: { type: 'value', name: '关节角度(°)', nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() },
    legend: { data: ['髋', '膝', '踝'], textStyle: { color: '#94a3b8', fontSize: 11 }, right: 0, top: 0 },
    series: [
      { name: '髋', type: 'line', data: hip, smooth: true, symbol: 'none', lineStyle: { color: '#6366f1', width: 1.8 } },
      { name: '膝', type: 'line', data: knee, smooth: true, symbol: 'none', lineStyle: { color: '#38bdf8', width: 1.8 } },
      { name: '踝', type: 'line', data: ankle, smooth: true, symbol: 'none', lineStyle: { color: '#10b981', width: 1.8 } }
    ]
  }
}

function mockJointRomRadar() {
  return {
    tooltip: tooltipTheme(),
    radar: {
      center: ['50%', '55%'], radius: '55%',
      indicator: [{ name: '髋屈伸ROM', max: 80 }, { name: '膝屈伸ROM', max: 100 }, { name: '踝背屈ROM', max: 30 }, { name: '踝跖屈ROM', max: 40 }, { name: '髋外展ROM', max: 40 }],
      axisName: { color: '#94a3b8', fontSize: 11 },
      axisLine: { lineStyle: { color: '#334155' } },
      splitLine: { lineStyle: { color: '#e2e8f0' } }
    },
    legend: { data: ['左侧', '右侧'], textStyle: { color: '#94a3b8', fontSize: 11 }, bottom: 0 },
    series: [{
      type: 'radar',
      data: [
        { name: '左侧', value: [62, 88, 22, 32, 28], itemStyle: { color: '#38bdf8' }, lineStyle: { color: '#38bdf8', width: 1.5 }, areaStyle: { color: 'rgba(56,189,248,0.2)' }, symbol: 'circle', symbolSize: 4 },
        { name: '右侧', value: [58, 85, 24, 30, 26], itemStyle: { color: '#10b981' }, lineStyle: { color: '#10b981', width: 1.5 }, areaStyle: { color: 'rgba(16,185,129,0.15)' }, symbol: 'circle', symbolSize: 4 }
      ]
    }]
  }
}

function mockJointAngVel() {
  const T = Array.from({ length: 100 }, (_, i) => +(i * 0.04).toFixed(2))
  const av = T.map(x => Math.sin(x * 2.8) * 200 + Math.cos(x * 1.5) * 80 + Math.random() * 30)
  const aa = []
  av.forEach((v, i) => { aa.push(i === 0 ? 0 : ((v - av[i - 1]) / 0.04)) })
  return {
    tooltip: tooltipTheme(),
    grid: dg(),
    xAxis: { type: 'category', data: T.map(v => v.toFixed(1)), axisLabel: { color: '#475569', fontSize: 10, interval: 24 }, ...da() },
    yAxis: [
      { type: 'value', name: '角速度(°/s)', nameTextStyle: { color: '#38bdf8', fontSize: 11 }, ...da() },
      { type: 'value', name: '角加速度(°/s²)', nameTextStyle: { color: '#f59e0b', fontSize: 11 }, ...da() }
    ],
    legend: { data: ['角速度', '角加速度'], textStyle: { color: '#94a3b8', fontSize: 11 }, right: 0, top: 0 },
    series: [
      { name: '角速度', type: 'line', data: av, smooth: true, symbol: 'none', lineStyle: { color: '#38bdf8', width: 1.8 } },
      { name: '角加速度', type: 'line', yAxisIndex: 1, data: aa, smooth: true, symbol: 'none', lineStyle: { color: '#f59e0b', width: 1.2, type: 'dashed' } }
    ]
  }
}

function mockTorqueChart() {
  const segs = ['段1', '段2', '段3', '段4', '段5', '段6']
  const hipB = segs.map(() => +(80 + Math.random() * 30).toFixed(0))
  const kneeB = segs.map(() => +(100 + Math.random() * 40).toFixed(0))
  const ankleB = segs.map(() => +(85 + Math.random() * 20).toFixed(0))
  return {
    tooltip: tooltipTheme(),
    grid: dg(),
    xAxis: { type: 'category', data: segs, axisLabel: { color: '#94a3b8', fontSize: 11 }, ...da() },
    yAxis: { type: 'value', name: '关节角度(°)', nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() },
    legend: { data: ['髋', '膝', '踝'], textStyle: { color: '#94a3b8', fontSize: 11 }, right: 0, top: 0 },
    series: [
      { name: '髋', type: 'bar', data: hipB, itemStyle: { color: '#6366f1', borderRadius: [3, 3, 0, 0] } },
      { name: '膝', type: 'bar', data: kneeB, itemStyle: { color: '#38bdf8', borderRadius: [3, 3, 0, 0] } },
      { name: '踝', type: 'bar', data: ankleB, itemStyle: { color: '#10b981', borderRadius: [3, 3, 0, 0] } },
      { type: 'line', markLine: { silent: true, symbol: 'none', lineStyle: { color: '#ef4444', type: 'dashed', width: 1 }, label: { color: '#ef4444', fontSize: 10, formatter: '膝理想范围' }, data: [{ yAxis: 130 }] }, data: [], lineStyle: { opacity: 0 }, itemStyle: { opacity: 0 } }
    ]
  }
}

function renderCharts() {
  if (angleRef.value) {
    const c = echarts.init(angleRef.value)
    if (props.joint) c.setOption(props.joint, true)
    else if (isDev) c.setOption(mockJoint(), true)
    charts.push(c)
  }
  if (romRef.value) {
    const c = echarts.init(romRef.value)
    if (props.jointRomRadar) c.setOption(props.jointRomRadar, true)
    else if (isDev) c.setOption(mockJointRomRadar(), true)
    charts.push(c)
  }
  if (angularRef.value) {
    const c = echarts.init(angularRef.value)
    if (props.jointAngVel) c.setOption(props.jointAngVel, true)
    else if (isDev) c.setOption(mockJointAngVel(), true)
    charts.push(c)
  }
  if (torqueRef.value) {
    const c = echarts.init(torqueRef.value)
    if (props.torqueChart) c.setOption(props.torqueChart, true)
    else if (isDev) c.setOption(mockTorqueChart(), true)
    charts.push(c)
  }
  if (powerRef.value) {
    const c = echarts.init(powerRef.value)
    if (props.powerChart) c.setOption(props.powerChart, true)
    else if (isDev) {
      // Reuse mockTorqueChart as a fallback visual for power
      const mockPower = mockTorqueChart()
      mockPower.yAxis.name = '功率(W)'
      mockPower.series[0].name = '髋功率'
      mockPower.series[1].name = '膝功率'
      c.setOption(mockPower, true)
    }
    charts.push(c)
  }
  if (hipRef.value) {
    const c = echarts.init(hipRef.value)
    if (props.hipAngleChart) c.setOption(props.hipAngleChart, true)
    else if (isDev) {
      // Fallback: show a simplified hip angle chart
      const T = Array.from({ length: 100 }, (_, i) => +(i).toFixed(0))
      const lh = T.map(x => 90 + Math.sin(x * 0.06) * 25 + Math.cos(x * 0.04) * 10 + Math.random() * 3)
      const rh = T.map(x => 88 + Math.sin(x * 0.06 + 0.5) * 22 + Math.cos(x * 0.04) * 12 + Math.random() * 3)
      c.setOption({
        tooltip: tooltipTheme(),
        grid: dg(),
        xAxis: { type: 'category', name: '标准化百分比(%)', nameTextStyle: { color: '#64748b', fontSize: 11 }, data: T, axisLabel: { color: '#475569', fontSize: 10, interval: 19 }, ...da() },
        yAxis: { type: 'value', name: '关节角度(°)', nameTextStyle: { color: '#64748b', fontSize: 11 }, ...da() },
        legend: { data: ['左髋', '右髋'], textStyle: { color: '#94a3b8', fontSize: 11 }, right: 0, top: 0 },
        series: [
          { name: '左髋', type: 'line', data: lh, smooth: true, symbol: 'none', lineStyle: { color: '#6366f1', width: 1.8 } },
          { name: '右髋', type: 'line', data: rh, smooth: true, symbol: 'none', lineStyle: { color: '#f59e0b', width: 1.8 } },
        ],
      }, true)
    }
    charts.push(c)
  }
}

onMounted(() => { renderCharts() })
watch(() => [props.joint, props.jointAngVel, props.jointRomRadar, props.torqueChart, props.powerChart, props.hipAngleChart], () => { renderCharts() })

onBeforeUnmount(() => { charts.forEach(c => c.dispose()) })
</script>
