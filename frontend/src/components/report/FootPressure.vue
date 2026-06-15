<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-lg flex flex-col justify-between glow-border-sky" style="min-height: 420px;">
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

        <!-- 前掌高温区 -->
        <div class="absolute w-10 h-11 rounded-full animate-pulse cursor-pointer group/zone" style="top: 12%; left: 28%; background: radial-gradient(circle at center, rgba(239,68,68,0.65), rgba(251,146,60,0.35), transparent); filter: blur(3px);">
          <div class="absolute opacity-0 group-hover/zone:opacity-100 transition-opacity -top-24 left-1/2 -translate-x-1/2 bg-slate-100 border border-slate-600 rounded-lg p-2 text-[10px] whitespace-nowrap z-30 shadow-lg pointer-events-none">
            <p class="text-slate-900 font-tech font-bold text-sm">前掌 · 高温区</p>
            <p class="text-slate-700 mt-1">压力: <span class="text-slate-900 font-tech">0.82 kN</span></p>
            <p class="text-slate-700">接触面积: <span class="text-slate-900 font-tech">38 cm²</span></p>
            <p class="text-slate-700">峰值压强: <span class="text-slate-900 font-tech">21.6 kPa</span></p>
          </div>
        </div>
        <!-- 足弓中温区 -->
        <div class="absolute w-8 h-9 rounded-full cursor-pointer group/zone2" style="top: 33%; left: 30%; background: radial-gradient(circle at center, rgba(234,179,8,0.45), rgba(74,222,128,0.20), transparent); filter: blur(4px);">
          <div class="absolute opacity-0 group-hover/zone2:opacity-100 transition-opacity -top-24 left-1/2 -translate-x-1/2 bg-slate-100 border border-slate-600 rounded-lg p-2 text-[10px] whitespace-nowrap z-30 shadow-lg pointer-events-none">
            <p class="text-slate-900 font-tech font-bold text-sm">足弓 · 中温区</p>
            <p class="text-slate-700 mt-1">压力: <span class="text-slate-900 font-tech">0.45 kN</span></p>
            <p class="text-slate-700">接触面积: <span class="text-slate-900 font-tech">22 cm²</span></p>
            <p class="text-slate-700">足弓指数: <span class="text-slate-900 font-tech">0.68</span></p>
          </div>
        </div>
        <!-- 脚跟低温区 -->
        <div class="absolute w-7 h-8 rounded-full cursor-pointer group/zone3" style="bottom: 12%; left: 33%; background: radial-gradient(circle at center, rgba(14,165,233,0.50), rgba(59,130,246,0.20), transparent); filter: blur(3px);">
          <div class="absolute opacity-0 group-hover/zone3:opacity-100 transition-opacity -top-24 left-1/2 -translate-x-1/2 bg-slate-100 border border-slate-600 rounded-lg p-2 text-[10px] whitespace-nowrap z-30 shadow-lg pointer-events-none">
            <p class="text-slate-900 font-tech font-bold text-sm">脚跟 · 低温区</p>
            <p class="text-slate-700 mt-1">压力: <span class="text-slate-900 font-tech">0.31 kN</span></p>
            <p class="text-slate-700">接触面积: <span class="text-slate-900 font-tech">16 cm²</span></p>
            <p class="text-slate-700">缓冲效率: <span class="text-slate-900 font-tech">91%</span></p>
          </div>
        </div>

        <span class="absolute bottom-0 text-sm font-tech font-bold text-slate-900 z-10">{{ fp.leftWeightPct }}<span class="text-[10px]">%</span></span>
      </div>

      <div class="w-px h-20 bg-slate-100"></div>

      <!-- 右脚 -->
      <div class="relative w-20 h-40 flex items-center justify-center">
        <span class="absolute -top-1.5 left-1/2 -translate-x-1/2 text-[10px] text-slate-400 font-tech tracking-wider z-10">RIGHT</span>
        <img :src="footprintsSvg" alt="右足" class="absolute inset-0 w-full h-full object-contain opacity-40 pointer-events-none select-none" style="filter: invert(0.55) brightness(1.5) drop-shadow(0 0 4px rgba(56,189,248,0.2));" />

        <!-- 前掌高温区（更高） -->
        <div class="absolute w-11 h-12 rounded-full cursor-pointer group/zone4" style="top: 10%; left: 26%; background: radial-gradient(circle at center, rgba(220,38,38,0.70), rgba(249,115,22,0.40), transparent); filter: blur(3px);">
          <div class="absolute opacity-0 group-hover/zone4:opacity-100 transition-opacity -top-24 left-1/2 -translate-x-1/2 bg-slate-100 border border-slate-600 rounded-lg p-2 text-[10px] whitespace-nowrap z-30 shadow-lg pointer-events-none">
            <p class="text-slate-900 font-tech font-bold text-sm">前掌 · 高温区</p>
            <p class="text-slate-700 mt-1">压力: <span class="text-slate-900 font-tech">0.91 kN</span></p>
            <p class="text-slate-700">接触面积: <span class="text-slate-900 font-tech">42 cm²</span></p>
            <p class="text-slate-700">峰值压强: <span class="text-slate-900 font-tech">21.7 kPa</span></p>
          </div>
        </div>
        <!-- 足弓中温区 -->
        <div class="absolute w-9 h-10 rounded-full cursor-pointer group/zone5" style="top: 31%; left: 28%; background: radial-gradient(circle at center, rgba(251,146,60,0.40), rgba(250,204,21,0.18), transparent); filter: blur(4px);">
          <div class="absolute opacity-0 group-hover/zone5:opacity-100 transition-opacity -top-24 left-1/2 -translate-x-1/2 bg-slate-100 border border-slate-600 rounded-lg p-2 text-[10px] whitespace-nowrap z-30 shadow-lg pointer-events-none">
            <p class="text-slate-900 font-tech font-bold text-sm">足弓 · 中温区</p>
            <p class="text-slate-700 mt-1">压力: <span class="text-slate-900 font-tech">0.48 kN</span></p>
            <p class="text-slate-700">接触面积: <span class="text-slate-900 font-tech">24 cm²</span></p>
            <p class="text-slate-700">足弓指数: <span class="text-slate-900 font-tech">0.72</span></p>
          </div>
        </div>
        <!-- 脚跟低温区 -->
        <div class="absolute w-6 h-7 rounded-full cursor-pointer group/zone6" style="bottom: 14%; left: 35%; background: radial-gradient(circle at center, rgba(56,189,248,0.45), transparent); filter: blur(3px);">
          <div class="absolute opacity-0 group-hover/zone6:opacity-100 transition-opacity -top-24 left-1/2 -translate-x-1/2 bg-slate-100 border border-slate-600 rounded-lg p-2 text-[10px] whitespace-nowrap z-30 shadow-lg pointer-events-none">
            <p class="text-slate-900 font-tech font-bold text-sm">脚跟 · 低温区</p>
            <p class="text-slate-700 mt-1">压力: <span class="text-slate-900 font-tech">0.28 kN</span></p>
            <p class="text-slate-700">接触面积: <span class="text-slate-900 font-tech">14 cm²</span></p>
            <p class="text-slate-700">缓冲效率: <span class="text-slate-900 font-tech">93%</span></p>
          </div>
        </div>

        <span class="absolute bottom-0 text-sm font-tech font-bold text-slate-900 z-10">{{ fp.rightWeightPct }}<span class="text-[10px]">%</span></span>
      </div>
    </div>

    <div>
      <div class="flex justify-between items-center mb-1.5">
        <span class="text-[11px] text-slate-400">最大压力峰值</span>
        <span class="text-sm font-tech font-bold text-slate-900" style="text-shadow: 0 0 10px rgba(248,113,113,0.5);">{{ fp.maxPeak }} kN</span>
      </div>
      <div class="h-2 bg-slate-100 rounded-full overflow-hidden flex">
        <div class="h-full transition-all" :style="{ width: fp.barPct + '%', background: 'linear-gradient(to right, #3b82f6, #22c55e, #eab308, #ef4444)' }"></div>
        <div class="h-full bg-slate-700" :style="{ width: (100 - fp.barPct) + '%' }"></div>
      </div>
      <div class="flex justify-between text-[10px] text-slate-400 mt-0.5">
        <span>0</span>
        <span>当前 {{ fp.barPct }}%</span>
        <span>MAX</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import footprintsSvg from '../../assets/footprints.svg'
import { footPressureData as staticFootPressure } from '../../data/bingbuData.js'

const props = defineProps({
  footPressureData: { type: Object, default: null },
})

const fp = computed(() => props.footPressureData || staticFootPressure)
</script>
