<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-lg glow-border-sky">
    <h3 class="text-slate-800 text-base font-semibold mb-3 flex items-center justify-between">
      <span class="flex items-center gap-2">
        <span class="w-1.5 h-1.5 rounded-full bg-sky-500 animate-pulse"></span>
        下肢移动与肌肉负载热力图
      </span>
      <span class="text-xs bg-sky-500/10 text-slate-900 px-2 py-0.5 rounded-full border border-sky-500/20 font-tech">
        AI 智能骨骼分析
      </span>
    </h3>

    <div class="grid grid-cols-12 gap-4 h-64">
      <!-- 人体热力图（全宽） -->
      <div class="col-span-12 bg-sky-50 rounded-lg relative flex items-center justify-center border border-slate-200/60 overflow-hidden">
        <!-- 网格背景 -->
        <div class="absolute inset-0 opacity-[0.03]"
             style="background-image: linear-gradient(rgba(255,255,255,.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.1) 1px, transparent 1px); background-size: 20px 20px;"></div>

        <!-- 颜色标尺 -->
        <div class="absolute left-2 bottom-4 top-4 w-3 flex flex-col justify-between items-center text-[10px] text-slate-400 z-20">
          <span class="text-slate-900 font-tech text-[10px]">HIGH</span>
          <div class="w-full flex-1 my-1 rounded-full overflow-hidden" style="background: linear-gradient(to bottom, #ef4444, #f59e0b, #22c55e, #3b82f6);"></div>
          <span class="text-slate-400 font-tech text-[10px]">LOW</span>
        </div>

        <!-- 人体剪影 + 热力覆盖层 -->
        <div class="relative w-full h-full flex items-center justify-center">
          <!-- 人体剪影底图 -->
          <img
            :src="humanBodySvg"
            alt="人体剪影"
            class="h-[82%] w-auto opacity-50 pointer-events-none select-none"
            style="filter: invert(0.5) brightness(1.6) drop-shadow(0 0 6px rgba(56,189,248,0.3));"
          />

          <!-- 热力覆盖层 - 多层径向渐变叠加 -->
          <!-- 区域1：膝关节（高温 - 红/橙） -->
          <div class="absolute w-11 h-11 rounded-full animate-pulse" style="left: 33%; top: 54%; background: radial-gradient(circle at center, rgba(239,68,68,0.65), rgba(249,115,22,0.35), transparent); filter: blur(3px);"></div>
          <div class="absolute w-11 h-11 rounded-full" style="left: 51%; top: 54%; background: radial-gradient(circle at center, rgba(249,115,22,0.55), rgba(250,204,21,0.25), transparent); filter: blur(3px);"></div>

          <!-- 区域2：大腿（中温 - 黄/绿） -->
          <div class="absolute w-10 h-14 rounded-full" style="left: 32%; top: 43%; background: radial-gradient(circle at center, rgba(234,179,8,0.45), rgba(74,222,128,0.20), transparent); filter: blur(4px);"></div>
          <div class="absolute w-10 h-14 rounded-full" style="left: 52%; top: 43%; background: radial-gradient(circle at center, rgba(16,185,129,0.45), rgba(74,222,128,0.18), transparent); filter: blur(4px);"></div>

          <!-- 区域3：小腿（中低温 - 绿/蓝） -->
          <div class="absolute w-9 h-11 rounded-full" style="left: 33%; top: 66%; background: radial-gradient(circle at center, rgba(16,185,129,0.55), rgba(45,212,191,0.25), transparent); filter: blur(4px);"></div>
          <div class="absolute w-9 h-11 rounded-full" style="left: 52%; top: 66%; background: radial-gradient(circle at center, rgba(45,212,191,0.50), rgba(34,211,238,0.20), transparent); filter: blur(4px);"></div>

          <!-- 区域4：脚踝（低温 - 蓝） -->
          <div class="absolute w-7 h-7 rounded-full" style="left: 34%; top: 79%; background: radial-gradient(circle at center, rgba(14,165,233,0.50), rgba(59,130,246,0.20), transparent); filter: blur(3px);"></div>
          <div class="absolute w-7 h-7 rounded-full" style="left: 51%; top: 79%; background: radial-gradient(circle at center, rgba(96,165,250,0.45), rgba(129,140,248,0.18), transparent); filter: blur(3px);"></div>

          <!-- 区域5：核心躯干（轻微活动） -->
          <div class="absolute w-14 h-16 rounded-full" style="left: 38%; top: 30%; background: radial-gradient(circle at center, rgba(6,182,212,0.25), rgba(59,130,246,0.10), transparent); filter: blur(6px);"></div>
        </div>

        <!-- 右侧标注列表 -->
        <div class="absolute right-2 top-3 space-y-2 text-[10px] z-20">
          <div class="flex items-center gap-1.5 bg-white/90 px-2 py-1 rounded border border-slate-200/60">
            <span class="w-1.5 h-1.5 rounded-full bg-orange-400 shadow-[0_0_6px_rgba(251,146,60,0.6)]"></span>
            <span class="text-slate-700">膝关节 ROM 29° 活动充分</span>
          </div>
          <div class="flex items-center gap-1.5 bg-white/90 px-2 py-1 rounded border border-slate-200/60">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]"></span>
            <span class="text-slate-700">踝关节 角速度峰值1256°/s</span>
          </div>
          <div class="flex items-center gap-1.5 bg-white/90 px-2 py-1 rounded border border-slate-200/60">
            <span class="w-1.5 h-1.5 rounded-full bg-sky-400 shadow-[0_0_6px_rgba(56,189,248,0.6)]"></span>
            <span class="text-slate-700">核心 DSO≈85% 躯干稳定</span>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import humanBodySvg from '../../assets/human-body.svg'

defineProps({
  jointROM: { type: Object, default: null },
  globalStats: { type: Object, default: null },
})
</script>
