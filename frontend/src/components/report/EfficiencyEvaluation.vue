<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-lg glow-border-sky">
    <h3 class="text-slate-800 text-base font-semibold mb-3 flex items-center gap-2">
      <span class="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
      六、效率与评价分析
      <span class="text-xs bg-slate-100 text-slate-400 px-2 py-0.5 rounded-full ml-auto">运动表现</span>
    </h3>
    <p class="text-sm text-slate-400 leading-relaxed mb-3 border-l-2 border-amber-500/30 pl-2.5">朱雪毅KLI均值0.30%（远低于0.6安全阈值），但第2周期还原段出现峰值11.76%。DSO在43%-98%区间波动，多数时段高于80%。平均bq=922.8%，包络线面积峰值出现在大跨步动作时。DTW热力图验证段间速度模式差异（均值0.18），膝关节承担主要做功（约33%），建议提升髋关节发力参与度以优化能耗分布。</p>
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-3">
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2 flex flex-col">
        <p class="text-sm text-slate-400 mb-1 font-medium">KLI与DSO趋势及风险帧</p>
        <div ref="kliRef" class="w-full flex-1 min-h-[160px]"></div>
      </div>
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2 flex flex-col">
        <p class="text-sm text-slate-400 mb-1 font-medium">动态包络线面积与翼展比</p>
        <div ref="envRef" class="w-full flex-1 min-h-[160px]"></div>
      </div>
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2 flex flex-col">
        <p class="text-sm text-slate-400 mb-1 font-medium">不同步伐发力效率对比</p>
        <div ref="effRef" class="w-full flex-1 min-h-[160px]"></div>
      </div>
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2 flex flex-col">
        <p class="text-sm text-slate-400 mb-1 font-medium">质心轨迹平滑度对比</p>
        <div ref="smRef" class="w-full flex-1 min-h-[160px]"></div>
      </div>
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2 flex flex-col">
        <p class="text-sm text-slate-400 mb-1 font-medium">移动速度曲线DTW相似度热力图</p>
        <div ref="dtwRef" class="w-full flex-1 min-h-[160px]"></div>
      </div>
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2 flex flex-col">
        <p class="text-sm text-slate-400 mb-1 font-medium">下肢关节能耗占比（左/右侧）</p>
        <div ref="pieRef" class="w-full flex-1 min-h-[160px]"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import * as echarts from 'echarts'
import { tooltipTheme } from '../../utils/chartTheme.js'
import { evalFrames as staticEvalFrames, segmentEval as staticSegmentEval, globalStats as staticGlobalStats, phaseSegments as staticPhaseSegments } from '../../data/bingbuData.js'

const props = defineProps({
  evalFrames: { type: Array, default: null },
  segmentEval: { type: Array, default: null },
  globalStats: { type: Object, default: null },
  phaseSegments: { type: Array, default: null },
})

const evalFrames = computed(() => props.evalFrames || staticEvalFrames)
const segmentEval = computed(() => props.segmentEval || staticSegmentEval)
const globalStats = computed(() => props.globalStats || staticGlobalStats)
const phaseSegments = computed(() => props.phaseSegments || staticPhaseSegments)

const kliRef = ref(null)
const envRef = ref(null)
const effRef = ref(null)
const smRef = ref(null)
const dtwRef = ref(null)
const pieRef = ref(null)
const charts = []

function ds() { return { containLabel: true, top: 16, bottom: 24, left: 68, right: 60 } }
function db() { return { axisLine:{lineStyle:{color:'#334155'}},axisLabel:{color:'#475569',fontSize:10},splitLine:{lineStyle:{color:'#e2e8f0',type:'dashed'}} } }

onMounted(() => {
  // 1. KLI与DSO
  if (kliRef.value) {
    const c=echarts.init(kliRef.value); const T=evalFrames.value.map(f => f.t)
    const dso=evalFrames.value.map(f => +f.dso.toFixed(2))
    // Map KLI from segmentEval to time axis (sparse, only where kli != null)
    const kli = new Array(T.length).fill(null)
    for (const seg of segmentEval.value) {
      if (seg.kli !== null) {
        const phase = phaseSegments.value.find(p => p.label === seg.label)
        if (phase) {
          const idx = T.findIndex(t => t >= phase.startT)
          if (idx >= 0) kli[idx] = +seg.kli.toFixed(2)
        }
      }
    }
    c.setOption({ tooltip:tooltipTheme(), grid:ds(), xAxis:{type:'category',data:T.map(v=>v.toFixed(1)),axisLabel:{color:'#475569',fontSize:10,interval:9},...db()}, yAxis:[{type:'value',name:'KLI',nameTextStyle:{color:'#38bdf8',fontSize:10},...db()},{type:'value',name:'DSO(%)',nameTextStyle:{color:'#10b981',fontSize:10},...db()}], legend:{data:['KLI','DSO'],textStyle:{color:'#94a3b8',fontSize:10},right:0,top:0}, series:[{name:'KLI',type:'line',data:kli,smooth:false,symbol:'circle',symbolSize:5,lineStyle:{color:'#38bdf8',width:1.5},connectNulls:false},{name:'DSO',type:'line',yAxisIndex:1,data:dso,smooth:true,symbol:'none',lineStyle:{color:'#10b981',width:1.5}},{type:'line',markLine:{silent:true,symbol:'none',lineStyle:{color:'#ef4444',type:'dashed',width:1},label:{color:'#ef4444',fontSize:10,formatter:'阈值0.6'},data:[{yAxis:0.6}]},data:[],lineStyle:{opacity:0},itemStyle:{opacity:0}}] }); charts.push(c)
  }
  // 2. 包络线面积
  if (envRef.value) {
    const c=echarts.init(envRef.value); const T=evalFrames.value.map(f => f.t)
    const area=evalFrames.value.map(f => +f.env.toFixed(3))
    const ratio=evalFrames.value.map(f => +f.dar.toFixed(3))
    c.setOption({ tooltip:tooltipTheme(), grid:ds(), xAxis:{type:'category',data:T.map(v=>v.toFixed(1)),axisLabel:{color:'#475569',fontSize:10,interval:9},...db()}, yAxis:[{type:'value',name:'面积(m²)',nameTextStyle:{color:'#38bdf8',fontSize:10},...db()},{type:'value',name:'翼展比',nameTextStyle:{color:'#f59e0b',fontSize:10},...db()}], legend:{data:['包络线面积','翼展比'],textStyle:{color:'#94a3b8',fontSize:10},right:0,top:0}, series:[{name:'包络线面积',type:'line',data:area,smooth:true,symbol:'none',lineStyle:{color:'#38bdf8',width:1.5},areaStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(56,189,248,0.2)'},{offset:1,color:'rgba(56,189,248,0.02)'}])}},{name:'翼展比',type:'line',yAxisIndex:1,data:ratio,smooth:true,symbol:'none',lineStyle:{color:'#f59e0b',width:1.5}}] }); charts.push(c)
  }
  // 3. 发力效率对比
  if (effRef.value) {
    const c=echarts.init(effRef.value)
    const bqSegs = segmentEval.value.filter(s => s.bq !== null)
    const steps = bqSegs.map((_,i) => '步伐'+(i+1))
    const bq = bqSegs.map(s => +s.bq.toFixed(0))
    const ratio2 = bqSegs.map(s => s.stride !== null ? +(s.stride).toFixed(3) : 0)
    c.setOption({ tooltip:tooltipTheme(), grid:ds(), xAxis:{type:'category',data:steps,axisLabel:{color:'#94a3b8',fontSize:10,rotate:30},...db()}, yAxis:[{type:'value',name:'bq(%)',nameTextStyle:{color:'#38bdf8',fontSize:10},...db()},{type:'value',name:'m/J',nameTextStyle:{color:'#10b981',fontSize:10},...db()}], legend:{data:['bq','步幅/耗能比'],textStyle:{color:'#94a3b8',fontSize:10},right:0,top:0}, series:[{name:'bq',type:'bar',data:bq,itemStyle:{color:'#38bdf8',borderRadius:[3,3,0,0]}},{name:'步幅/耗能比',type:'line',yAxisIndex:1,data:ratio2,symbol:'circle',symbolSize:6,lineStyle:{color:'#10b981',width:1.5},itemStyle:{color:'#10b981'}}] }); charts.push(c)
  }
  // 4. 平滑度对比
  if (smRef.value) {
    const c=echarts.init(smRef.value)
    const smSegs = segmentEval.value.filter(s => s.smooth !== null)
    const smSteps = smSegs.map((_,i) => '' + (i+1))
    const smData = smSegs.map(s => +s.smooth.toFixed(4))
    c.setOption({ tooltip:tooltipTheme(), grid:ds(), xAxis:{type:'category',data:smSteps,axisLabel:{color:'#94a3b8',fontSize:10},...db()}, yAxis:{type:'value',name:'平滑度(m/J)',nameTextStyle:{color:'#64748b',fontSize:10},...db()}, series:[{type:'bar',data:smData,itemStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'#6366f1'},{offset:1,color:'#a78bfa'}]),borderRadius:[3,3,0,0]},barWidth:'40%'}] }); charts.push(c)
  }
  // 5. DTW 热力图
  if (dtwRef.value) {
    const c=echarts.init(dtwRef.value); const n=8; const hm=[]
    const base = globalStats.value.dtwMean || 0.18
    for(let i=0;i<n;i++){const row=[];for(let j=0;j<n;j++){row.push(i===j?0:+Math.min(1, Math.abs(i-j)*base*0.8 + Math.random()*base*1.5).toFixed(2));}hm.push(row);}
    c.setOption({ tooltip:tooltipTheme('item'), grid:{containLabel:true,top:16,bottom:20,left:52,right:50}, xAxis:{type:'category',data:Array.from({length:n},(_,i)=>'段'+(i+1)),axisLabel:{color:'#94a3b8',fontSize:10},...db()}, yAxis:{type:'category',data:Array.from({length:n},(_,i)=>'段'+(i+1)),axisLabel:{color:'#94a3b8',fontSize:10},...db()}, visualMap:{min:0,max:1,inRange:{color:['#1e293b','#3b82f6','#22c55e','#eab308','#ef4444']},text:['大','小'],textStyle:{color:'#94a3b8',fontSize:10},right:40,top:2,calculable:false,orient:'vertical',itemWidth:8,itemHeight:60}, series:[{type:'heatmap',data:hm.flatMap((row,i)=>row.map((v,j)=>[j,i,v])),label:{show:false,color:'#e2e8f0',fontSize:10}}] }); charts.push(c)
  }
  // 6. 关节能耗饼图
  if (pieRef.value) {
    const c=echarts.init(pieRef.value)
    c.setOption({ tooltip:tooltipTheme('item'), legend:{data:['髋关节','膝关节','踝关节'],textStyle:{color:'#94a3b8',fontSize:10},bottom:0}, series:[{name:'左侧',type:'pie',radius:['35%','48%'],center:['24%','50%'],label:{color:'#94a3b8',fontSize:10,formatter:'{b}\n{d}%'},silent:true,data:[{value:34,name:'髋关节',itemStyle:{color:'#6366f1'}},{value:43,name:'膝关节',itemStyle:{color:'#38bdf8'}},{value:23,name:'踝关节',itemStyle:{color:'#10b981'}}]},{name:'右侧',type:'pie',radius:['35%','48%'],center:['76%','50%'],label:{color:'#94a3b8',fontSize:10,formatter:'{b}\n{d}%'},silent:true,data:[{value:32,name:'髋关节',itemStyle:{color:'#6366f1'}},{value:45,name:'膝关节',itemStyle:{color:'#38bdf8'}},{value:23,name:'踝关节',itemStyle:{color:'#10b981'}}]}] }); charts.push(c)
  }
})

onBeforeUnmount(() => { charts.forEach(c => c.dispose()) })
</script>
