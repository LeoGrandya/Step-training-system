<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-lg glow-border-sky">
    <h3 class="text-slate-800 text-base font-semibold mb-3 flex items-center justify-between">
      <span class="flex items-center gap-2">
        <span class="w-1.5 h-1.5 rounded-full bg-sky-500 animate-pulse"></span>
        下肢移动与肌肉负载热力图
      </span>
      <span class="text-xs bg-sky-500/10 text-slate-900 px-2 py-0.5 rounded-full border border-sky-500/20 font-tech">AI 智能骨骼分析</span>
    </h3>

    <div class="grid grid-cols-12 gap-4 h-64">
      <div class="col-span-12 bg-sky-50 rounded-lg relative flex items-center justify-center border border-slate-200/60 overflow-hidden">
        <div class="absolute inset-0 opacity-[0.03]"
             style="background-image: linear-gradient(rgba(255,255,255,.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.1) 1px, transparent 1px); background-size: 20px 20px;"></div>

        <div class="absolute left-2 bottom-4 top-4 w-3 flex flex-col justify-between items-center text-[10px] text-slate-400 z-20">
          <span class="text-slate-900 font-tech text-[10px]">HIGH</span>
          <div class="w-full flex-1 my-1 rounded-full overflow-hidden" style="background: linear-gradient(to bottom, #ef4444, #f59e0b, #22c55e, #3b82f6);"></div>
          <span class="text-slate-400 font-tech text-[10px]">LOW</span>
        </div>

        <div class="relative w-full h-full flex items-center justify-center">
          <img :src="humanBodySvg" alt="人体剪影"
               class="h-[82%] w-auto opacity-50 pointer-events-none select-none"
               style="filter: invert(0.5) brightness(1.6) drop-shadow(0 0 6px rgba(56,189,248,0.3));" />

          <!-- 膝关节 -->
          <div class="absolute w-11 h-11 bg-radial-at-c from-red-500/65 via-orange-500/35 to-transparent rounded-full filter blur-[3px] animate-pulse" style="left: 33%; top: 54%;"></div>
          <div class="absolute w-11 h-11 bg-radial-at-c from-orange-500/55 via-yellow-400/25 to-transparent rounded-full filter blur-[3px]" style="left: 51%; top: 54%;"></div>
          <!-- 大腿 -->
          <div class="absolute w-10 h-14 bg-radial-at-c from-yellow-500/45 via-green-400/20 to-transparent rounded-full filter blur-[4px]" style="left: 32%; top: 43%;"></div>
          <div class="absolute w-10 h-14 bg-radial-at-c from-emerald-500/45 via-green-400/18 to-transparent rounded-full filter blur-[4px]" style="left: 52%; top: 43%;"></div>
          <!-- 小腿 -->
          <div class="absolute w-9 h-11 bg-radial-at-c from-emerald-500/55 via-teal-400/25 to-transparent rounded-full filter blur-[4px]" style="left: 33%; top: 66%;"></div>
          <div class="absolute w-9 h-11 bg-radial-at-c from-teal-400/50 via-cyan-400/20 to-transparent rounded-full filter blur-[4px]" style="left: 52%; top: 66%;"></div>
          <!-- 脚踝 -->
          <div class="absolute w-7 h-7 bg-radial-at-c from-sky-500/50 via-blue-500/20 to-transparent rounded-full filter blur-[3px]" style="left: 34%; top: 79%;"></div>
          <div class="absolute w-7 h-7 bg-radial-at-c from-blue-400/45 via-indigo-400/18 to-transparent rounded-full filter blur-[3px]" style="left: 51%; top: 79%;"></div>
          <!-- 核心躯干 -->
          <div class="absolute w-14 h-16 bg-radial-at-c from-cyan-500/25 via-blue-500/10 to-transparent rounded-full filter blur-[6px]" style="left: 38%; top: 30%;"></div>
        </div>

        <div class="absolute right-2 top-3 space-y-2 text-[10px] z-20">
          <div class="flex items-center gap-1.5 bg-white/90 px-2 py-1 rounded border border-slate-200/60">
            <span class="w-1.5 h-1.5 rounded-full bg-orange-400 shadow-[0_0_6px_rgba(251,146,60,0.6)]"></span>
            <span class="text-slate-700">膝关节 稳定性良好</span>
          </div>
          <div class="flex items-center gap-1.5 bg-white/90 px-2 py-1 rounded border border-slate-200/60">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]"></span>
            <span class="text-slate-700">小腿 爆发力充沛</span>
          </div>
          <div class="flex items-center gap-1.5 bg-white/90 px-2 py-1 rounded border border-slate-200/60">
            <span class="w-1.5 h-1.5 rounded-full bg-sky-400 shadow-[0_0_6px_rgba(56,189,248,0.6)]"></span>
            <span class="text-slate-700">核心 躯干稳定</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import humanBodySvg from '../../assets/human-body.svg'
</script>
