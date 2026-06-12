<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-lg h-full flex flex-col justify-between glow-border-sky">
    <div>
      <h3 class="text-slate-800 text-base font-semibold mb-1 flex items-center gap-2">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
        足底压力动态分布
      </h3>
      <p class="text-[11px] text-slate-400">双侧足底压力传感器（高频采样实时映射 · 悬停查看细节）</p>
    </div>

    <div class="flex justify-around items-center bg-sky-50 rounded-lg border border-slate-200/60 p-3 my-2 flex-1 gap-3">
      <!-- 左脚 -->
      <div class="relative w-20 h-40 flex items-center justify-center">
        <span class="absolute -top-1.5 left-1/2 -translate-x-1/2 text-[10px] text-slate-400 font-tech tracking-wider z-10">LEFT</span>
        <img :src="footprintsSvg" alt="左足" class="absolute inset-0 w-full h-full object-contain opacity-40 pointer-events-none select-none" style="filter: invert(0.55) brightness(1.5) drop-shadow(0 0 4px rgba(56,189,248,0.2));" />

        <div class="absolute w-10 h-11 bg-radial-at-c from-red-500/65 via-orange-400/35 to-transparent rounded-full filter blur-[3px] animate-pulse cursor-pointer group/zone" style="top: 12%; left: 28%;">
          <div class="absolute opacity-0 group-hover/zone:opacity-100 transition-opacity -top-24 left-1/2 -translate-x-1/2 bg-slate-100 border border-slate-600 rounded-lg p-2 text-[10px] whitespace-nowrap z-30 shadow-lg pointer-events-none">
            <p class="text-slate-900 font-tech font-bold text-sm">前掌 · 高温区</p>
            <p class="text-slate-700 mt-1">左侧主导发力</p>
            <p class="text-slate-700">接触占比: <span class="text-slate-900 font-tech">{{ pct(leftPct) }}</span></p>
          </div>
        </div>
        <div class="absolute w-8 h-9 bg-radial-at-c from-yellow-500/45 via-green-400/20 to-transparent rounded-full filter blur-[4px] cursor-pointer group/zone2" style="top: 33%; left: 30%;">
          <div class="absolute opacity-0 group-hover/zone2:opacity-100 transition-opacity -top-24 left-1/2 -translate-x-1/2 bg-slate-100 border border-slate-600 rounded-lg p-2 text-[10px] whitespace-nowrap z-30 shadow-lg pointer-events-none">
            <p class="text-slate-900 font-tech font-bold text-sm">足弓 · 中温区</p>
            <p class="text-slate-700 mt-1">步数: <span class="text-slate-900 font-tech">{{ leftStepCount }}</span></p>
            <p class="text-slate-700 mt-1">支撑占比: <span class="text-slate-900 font-tech">{{ pct(leftPct) }}</span></p>
          </div>
        </div>
        <div class="absolute w-7 h-8 bg-radial-at-c from-sky-500/50 via-blue-400/20 to-transparent rounded-full filter blur-[3px] cursor-pointer group/zone3" style="bottom: 12%; left: 33%;">
          <div class="absolute opacity-0 group-hover/zone3:opacity-100 transition-opacity -top-24 left-1/2 -translate-x-1/2 bg-slate-100 border border-slate-600 rounded-lg p-2 text-[10px] whitespace-nowrap z-30 shadow-lg pointer-events-none">
            <p class="text-slate-900 font-tech font-bold text-sm">脚跟 · 低温区</p>
            <p class="text-slate-700 mt-1">缓冲效率良好</p>
          </div>
        </div>

        <span class="absolute bottom-0 text-sm font-tech font-bold text-slate-900 z-10">{{ pct(leftPct) }}<span class="text-[10px]">%</span></span>
      </div>

      <div class="w-px h-20 bg-slate-100"></div>

      <!-- 右脚 -->
      <div class="relative w-20 h-40 flex items-center justify-center">
        <span class="absolute -top-1.5 left-1/2 -translate-x-1/2 text-[10px] text-slate-400 font-tech tracking-wider z-10">RIGHT</span>
        <img :src="footprintsSvg" alt="右足" class="absolute inset-0 w-full h-full object-contain opacity-40 pointer-events-none select-none" style="filter: invert(0.55) brightness(1.5) drop-shadow(0 0 4px rgba(56,189,248,0.2));" />

        <div class="absolute w-11 h-12 bg-radial-at-c from-red-600/70 via-orange-500/40 to-transparent rounded-full filter blur-[3px] cursor-pointer group/zone4" style="top: 10%; left: 26%;">
          <div class="absolute opacity-0 group-hover/zone4:opacity-100 transition-opacity -top-24 left-1/2 -translate-x-1/2 bg-slate-100 border border-slate-600 rounded-lg p-2 text-[10px] whitespace-nowrap z-30 shadow-lg pointer-events-none">
            <p class="text-slate-900 font-tech font-bold text-sm">前掌 · 高温区</p>
            <p class="text-slate-700 mt-1">右侧主导发力</p>
            <p class="text-slate-700">接触占比: <span class="text-slate-900 font-tech">{{ pct(rightPct) }}</span></p>
          </div>
        </div>
        <div class="absolute w-9 h-10 bg-radial-at-c from-orange-400/40 via-yellow-400/18 to-transparent rounded-full filter blur-[4px] cursor-pointer group/zone5" style="top: 31%; left: 28%;">
          <div class="absolute opacity-0 group-hover/zone5:opacity-100 transition-opacity -top-24 left-1/2 -translate-x-1/2 bg-slate-100 border border-slate-600 rounded-lg p-2 text-[10px] whitespace-nowrap z-30 shadow-lg pointer-events-none">
            <p class="text-slate-900 font-tech font-bold text-sm">足弓 · 中温区</p>
            <p class="text-slate-700 mt-1">步数: <span class="text-slate-900 font-tech">{{ rightStepCount }}</span></p>
            <p class="text-slate-700 mt-1">支撑占比: <span class="text-slate-900 font-tech">{{ pct(rightPct) }}</span></p>
          </div>
        </div>
        <div class="absolute w-6 h-7 bg-radial-at-c from-sky-400/45 to-transparent rounded-full filter blur-[3px] cursor-pointer group/zone6" style="bottom: 14%; left: 35%;">
          <div class="absolute opacity-0 group-hover/zone6:opacity-100 transition-opacity -top-24 left-1/2 -translate-x-1/2 bg-slate-100 border border-slate-600 rounded-lg p-2 text-[10px] whitespace-nowrap z-30 shadow-lg pointer-events-none">
            <p class="text-slate-900 font-tech font-bold text-sm">脚跟 · 低温区</p>
            <p class="text-slate-700 mt-1">缓冲效率良好</p>
          </div>
        </div>

        <span class="absolute bottom-0 text-sm font-tech font-bold text-slate-900 z-10">{{ pct(rightPct) }}<span class="text-[10px]">%</span></span>
      </div>
    </div>

    <div>
      <div class="flex justify-between items-center mb-1.5">
        <span class="text-[11px] text-slate-400">最大压力峰值</span>
        <span class="text-sm font-tech font-bold text-slate-900" style="text-shadow: 0 0 10px rgba(248,113,113,0.5);">{{ peakText }}</span>
      </div>
      <div class="h-2 bg-slate-100 rounded-full overflow-hidden flex">
        <div class="h-full transition-all" :style="{ width: peakPct + '%', background: 'linear-gradient(to right, #3b82f6, #22c55e, #eab308, #ef4444)' }"></div>
        <div class="h-full bg-slate-700" :style="{ width: (100 - peakPct) + '%' }"></div>
      </div>
      <div class="flex justify-between text-[10px] text-slate-400 mt-0.5">
        <span>0</span>
        <span>当前 {{ peakPct }}%</span>
        <span>MAX</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import footprintsSvg from '../../assets/footprints.svg'

const props = defineProps({
  data: { type: Object, default: null },
})

function pct(v) { return v != null ? v : '-' }

const leftPct = computed(() => props.data?.leftSupportPct ?? 48.5)
const rightPct = computed(() => props.data?.rightSupportPct ?? 51.5)
const leftStepCount = computed(() => props.data?.leftStepCount ?? '-')
const rightStepCount = computed(() => props.data?.rightStepCount ?? '-')
const peakPct = computed(() => Math.round((leftPct.value + rightPct.value) / 1.6))
const peakText = computed(() => {
  const speed = props.data?.peakSpeed
  return speed != null ? `${Number(speed).toFixed(1)} m/s` : '1.2 m/s²'
})
</script>
