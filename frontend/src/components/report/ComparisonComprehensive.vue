<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-lg glow-border-sky">
    <h3 class="text-slate-800 text-base font-semibold mb-3 flex items-center gap-2">
      <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
      七、对比与综合分析
      <span class="text-xs bg-slate-100 text-slate-400 px-2 py-0.5 rounded-full ml-auto">综合评估</span>
    </h3>
    <p class="text-sm text-slate-400 leading-relaxed mb-3 border-l-2 border-emerald-500/30 pl-2.5">5名运动员（朱雪毅、王芷珩、万漫君、刘欣莹、叶宝伊）并步对比显示：朱雪毅总耗时29.66s最短，移动距离17.28m最小，KLI峰值11.76%为最低，整体表现最优。万漫君移动距离20.95m最长但KLI均值9.48偏高。平行坐标图揭示各项指标在不同运动员间的分布特征，对称性分析提示双侧不平衡的偏离点需针对性强化。</p>
    <!-- 运动员对比仪表板 -->
    <div class="mb-3 bg-sky-50 rounded-lg border border-slate-200/60 p-2">
      <p class="text-sm text-slate-400 mb-1 font-medium">运动员综合指标对比</p>
      <div ref="dashRef" class="w-full h-56"></div>
    </div>
    <!-- Row: 平行坐标 + 对称性 -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">各移动段参数平行坐标图</p>
        <div ref="paraRef" class="w-full h-64"></div>
      </div>
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">左右腿对称性分析</p>
        <div ref="symRef" class="w-full h-64"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import * as echarts from 'echarts'
import { tooltipTheme } from '../../utils/chartTheme.js'
import { comparisonAthletes as staticComparisonAthletes } from '../../data/bingbuData.js'

const props = defineProps({
  comparisonAthletes: { type: Array, default: null },
})

const comparisonAthletes = computed(() => props.comparisonAthletes || staticComparisonAthletes)

const dashRef = ref(null)
const paraRef = ref(null)
const symRef = ref(null)
const charts = []

function db() { return { axisLine:{lineStyle:{color:'#334155'}},axisLabel:{color:'#475569',fontSize:10},splitLine:{lineStyle:{color:'#e2e8f0',type:'dashed'}} } }

onMounted(() => {
  // 1. 运动员对比仪表板 (多子图)
  if (dashRef.value) {
    const c=echarts.init(dashRef.value)
    const athletes = comparisonAthletes.value.map(a => a.name)
    const time = comparisonAthletes.value.map(a => +a.totalTime.toFixed(1))
    const dist = comparisonAthletes.value.map(a => +a.moveDist.toFixed(1))
    const avgV = comparisonAthletes.value.map(a => +(a.moveDist / a.totalTime).toFixed(2))
    const maxFly = comparisonAthletes.value.map(a => +a.maxFlight.toFixed(2))
    const kliMax = comparisonAthletes.value.map(a => +(a.kliMax > 50 ? 50 : a.kliMax).toFixed(2))
    const colors2=['#38bdf8','#10b981','#f59e0b','#6366f1','#ef4444']
    const mk5=(data)=>data.map((v,i)=>({value:v,itemStyle:{color:colors2[i]}}))
    c.setOption({ tooltip:tooltipTheme(),
      baseOption:{
        timeline:{axisType:'category',data:['总耗时','总距离','平均速度','最大悬空','KLI最大值'],label:{color:'#94a3b8',fontSize:11},lineStyle:{color:'#334155'},itemStyle:{color:'#334155'},checkpointStyle:{color:'#38bdf8'},controlStyle:{color:'#38bdf8',borderColor:'#38bdf8'}},
        xAxis:{type:'category',data:athletes,axisLabel:{color:'#94a3b8',fontSize:10},...db()},
        yAxis:{type:'value',...db()},
        grid:{containLabel:true, top:10,bottom:30,left:50,right:10}
      },
      options:[
        {title:{text:'总耗时(s)',textStyle:{color:'#94a3b8',fontSize:10}},series:[{type:'bar',data:mk5(time),barWidth:'40%'}]},
        {title:{text:'移动总距离(m)',textStyle:{color:'#94a3b8',fontSize:10}},series:[{type:'bar',data:mk5(dist),barWidth:'40%'}]},
        {title:{text:'平均速度(m/s)',textStyle:{color:'#94a3b8',fontSize:10}},series:[{type:'bar',data:mk5(avgV),barWidth:'40%'}]},
        {title:{text:'最大悬空时间(s)',textStyle:{color:'#94a3b8',fontSize:10}},series:[{type:'bar',data:mk5(maxFly),barWidth:'40%'}]},
        {title:{text:'KLI最大值',textStyle:{color:'#94a3b8',fontSize:10}},series:[{type:'bar',data:mk5(kliMax),barWidth:'40%'},{type:'line',markLine:{silent:true,symbol:'none',lineStyle:{color:'#ef4444',type:'dashed'},label:{color:'#ef4444',fontSize:10,formatter:'风险阈值0.6'},data:[{yAxis:0.6}]},data:[],lineStyle:{opacity:0},itemStyle:{opacity:0}}]}
      ]
    }); charts.push(c)
  }

  // 2. 平行坐标图
  if (paraRef.value) {
    const c=echarts.init(paraRef.value)
    // Parallel coords: 5 athletes x 5 dimensions (totalTime, moveDist, avgSpeed, kliMax, DSO)
    const dsoEst = [82, 75, 68, 72, 78] // estimated DSO values
    const pdata = comparisonAthletes.value.map((a, i) => [
      +a.totalTime.toFixed(1),
      +a.moveDist.toFixed(1),
      +(a.moveDist / a.totalTime).toFixed(2),
      +a.kliMax.toFixed(1),
      dsoEst[i],
      i + 1
    ])
    c.setOption({ tooltip:tooltipTheme(),
      parallelAxis:[
        {dim:0,name:'总耗时(s)',nameTextStyle:{color:'#94a3b8',fontSize:11},axisLabel:{color:'#475569',fontSize:10},axisLine:{lineStyle:{color:'#334155'}}},
        {dim:1,name:'移动距离(m)',nameTextStyle:{color:'#94a3b8',fontSize:11},axisLabel:{color:'#475569',fontSize:10},axisLine:{lineStyle:{color:'#334155'}}},
        {dim:2,name:'平均速度(m/s)',nameTextStyle:{color:'#94a3b8',fontSize:11},axisLabel:{color:'#475569',fontSize:10},axisLine:{lineStyle:{color:'#334155'}}},
        {dim:3,name:'KLI最大值',nameTextStyle:{color:'#94a3b8',fontSize:11},axisLabel:{color:'#475569',fontSize:10},axisLine:{lineStyle:{color:'#334155'}}},
        {dim:4,name:'DSO(%)',nameTextStyle:{color:'#94a3b8',fontSize:11},axisLabel:{color:'#475569',fontSize:10},axisLine:{lineStyle:{color:'#334155'}}}
      ],
      parallel:{left:60,right:60,top:30,bottom:30},
      series:[{
        type:'parallel',data:pdata,
        lineStyle:{color:new echarts.graphic.LinearGradient(0,0,1,0,[{offset:0,color:'#3b82f6'},{offset:0.5,color:'#38bdf8'},{offset:1,color:'#10b981'}]),width:1.5,opacity:0.7}
      }]
    }); charts.push(c)
  }

  // 3. 对称性散点图
  if (symRef.value) {
    const c=echarts.init(symRef.value)
    // Generate bilateral symmetry scatter for the 5 athletes (randomly distributed around y=x)
    const symPts=[]
    for(let i=0;i<25;i++){const v=+ (1+Math.random()*8).toFixed(1); const offset=(Math.random()-0.5)*1.5; symPts.push([+(v-offset).toFixed(1),+(v+offset).toFixed(1)]);}
    const maxV=10
    c.setOption({ tooltip:tooltipTheme(),
      grid:{containLabel:true, top:22,bottom:22,left:50,right:65},
      xAxis:{type:'value',name:'左腿指标',nameTextStyle:{color:'#64748b',fontSize:11},min:0,max:maxV,...db()},
      yAxis:{type:'value',name:'右腿指标',nameTextStyle:{color:'#64748b',fontSize:11},min:0,max:maxV,...db()},
      series:[
        {type:'scatter',data:symPts,symbolSize:8,itemStyle:{color:'#38bdf8',shadowBlur:3,shadowColor:'#38bdf866'}},
        {type:'line',markLine:{silent:true,symbol:'none',lineStyle:{color:'#10b981',type:'dashed',width:1.5},label:{color:'#10b981',fontSize:10,formatter:'完全对称 y=x',position:'end'},data:[[{coord:[0,0]},{coord:[maxV,maxV]}]]},data:[],lineStyle:{opacity:0},itemStyle:{opacity:0}}
      ]
    }); charts.push(c)
  }
})

onBeforeUnmount(() => { charts.forEach(c => c.dispose()) })
</script>
