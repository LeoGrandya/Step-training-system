<template>
  <div v-if="hasData" class="bg-white border border-slate-200 rounded-xl p-4 shadow-lg h-full flex flex-col justify-between glow-border-sky">
    <div>
      <h3 class="text-slate-800 text-base font-semibold mb-1 flex items-center gap-2">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
        足底支撑分布
      </h3>
      <p class="text-[11px] text-slate-400">双侧支撑时间与步数统计</p>
    </div>

    <!-- 支撑占比对比条 -->
    <div class="my-2 space-y-3">
      <div>
        <div class="flex justify-between text-[11px] mb-1">
          <span class="text-slate-500">左脚支撑</span>
          <span class="font-tech text-slate-900">{{ leftSupportPct }}%</span>
        </div>
        <div class="h-3 bg-slate-100 rounded-full overflow-hidden">
          <div class="h-full bg-gradient-to-r from-sky-400 to-sky-500 rounded-full transition-all"
               :style="{ width: leftSupportPct + '%' }"></div>
        </div>
      </div>
      <div>
        <div class="flex justify-between text-[11px] mb-1">
          <span class="text-slate-500">右脚支撑</span>
          <span class="font-tech text-slate-900">{{ rightSupportPct }}%</span>
        </div>
        <div class="h-3 bg-slate-100 rounded-full overflow-hidden">
          <div class="h-full bg-gradient-to-r from-amber-400 to-amber-500 rounded-full transition-all"
               :style="{ width: rightSupportPct + '%' }"></div>
        </div>
      </div>
    </div>

    <!-- 步数统计 -->
    <div class="grid grid-cols-2 gap-3 text-center">
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-[11px] text-slate-400">左脚步数</p>
        <p class="text-xl font-tech font-bold text-sky-600">{{ leftSteps }}</p>
      </div>
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-[11px] text-slate-400">右脚步数</p>
        <p class="text-xl font-tech font-bold text-amber-600">{{ rightSteps }}</p>
      </div>
    </div>

    <!-- 腾空帧统计 -->
    <div class="mt-2 flex justify-around text-[10px] text-slate-400 bg-sky-50 rounded-lg border border-slate-200/60 p-2">
      <span>左腾空: {{ leftAirborneFrames }}帧</span>
      <span>双腾空: {{ doubleAirborneFrames }}帧</span>
      <span>右腾空: {{ rightAirborneFrames }}帧</span>
    </div>

    <!-- 对称性文字 -->
    <p class="text-[11px] text-slate-500 mt-2 text-center">{{ symmetryText }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Object, default: null },
})

const hasData = computed(() => {
  if (!props.data) return false
  return props.data.totalSteps > 0 || props.data.leftSupportPct != null
})

const leftSupportPct = computed(() => props.data?.leftSupportPct ?? 50)
const rightSupportPct = computed(() => props.data?.rightSupportPct ?? 50)
const leftSteps = computed(() => props.data?.leftStepCount ?? '-')
const rightSteps = computed(() => props.data?.rightStepCount ?? '-')
const leftAirborneFrames = computed(() => props.data?.leftAirborneFrames ?? 0)
const rightAirborneFrames = computed(() => props.data?.rightAirborneFrames ?? 0)
const doubleAirborneFrames = computed(() => props.data?.doubleAirborneFrames ?? 0)

const symmetryText = computed(() => {
  const diff = Math.abs(leftSupportPct.value - rightSupportPct.value)
  if (diff < 5) return '✓ 双侧支撑均衡'
  if (diff < 10) return '△ 双侧支撑略有偏差'
  return '⚠ ' + (leftSupportPct.value > rightSupportPct.value ? '左侧' : '右侧') + '支撑偏多，建议关注'
})
</script>
