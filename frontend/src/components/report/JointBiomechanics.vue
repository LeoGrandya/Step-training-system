<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-lg glow-border-sky">
    <h3 class="text-slate-800 text-base font-semibold mb-3 flex items-center gap-2">
      <span class="w-1.5 h-1.5 rounded-full bg-pink-500 animate-pulse"></span>
      五、关节生物力学分析
      <span class="text-xs bg-slate-100 text-slate-400 px-2 py-0.5 rounded-full ml-auto">运动医学</span>
    </h3>
    <p class="text-sm text-slate-400 leading-relaxed mb-3 border-l-2 border-pink-500/30 pl-2.5">朱雪毅左膝活动范围134.9-168.5°，右膝105.1-167.5°。ROM雷达图显示左髋ROM(20.4°)、右髋ROM(17.6°)，左右膝ROM差异仅0.2°（左29.1/右29.3），对称性优秀。踝关节ROM左26.6°/右28.3°。角速度峰值出现在蹬伸末期，着地瞬间角加速度提示存在冲击负荷。制动瞬间膝角在部分段接近理想范围，建议加强右侧关节柔韧性与离心控制能力。</p>
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <!-- Row 1: 髋膝踝角度曲线 + ROM雷达图 -->
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">移动段 髋/膝/踝角度变化</p>
        <div ref="angleRef" class="w-full h-56"></div>
      </div>
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">左右侧关节活动范围(ROM)对比</p>
        <div ref="romRef" class="w-full h-56"></div>
      </div>
      <!-- Row 2: 角速度/角加速度 + 制动角度柱状图 -->
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">膝关节角速度与角加速度</p>
        <div ref="angularRef" class="w-full h-56"></div>
      </div>
      <div class="bg-sky-50 rounded-lg border border-slate-200/60 p-2">
        <p class="text-sm text-slate-400 mb-1 font-medium">制动变向瞬间关节角度对比</p>
        <div ref="brakeRef" class="w-full h-56"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import * as echarts from 'echarts'
import { tooltipTheme } from '../../utils/chartTheme.js'
import { jointFrames as staticJointFrames, jointROM as staticJointROM } from '../../data/bingbuData.js'

const props = defineProps({
  jointFrames: { type: Array, default: null },
  jointROM: { type: Object, default: null },
})

const jointFrames = computed(() => props.jointFrames || staticJointFrames)
const jointROM = computed(() => props.jointROM || staticJointROM)

const angleRef = ref(null)
const romRef = ref(null)
const angularRef = ref(null)
const brakeRef = ref(null)
const charts = []

function dg() { return { containLabel: true, top: 22, bottom: 32, left: 78, right: 55 } }
function da() { return { axisLine:{lineStyle:{color:'#334155'}},axisLabel:{color:'#475569',fontSize:11},splitLine:{lineStyle:{color:'#e2e8f0',type:'dashed'}} } }

onMounted(() => {
  // 1. 髋膝踝角度曲线
  if (angleRef.value) {
    const c = echarts.init(angleRef.value)
    const T=jointFrames.value.map(f => f.t)
    const hip=jointFrames.value.map(f => +(f.lh ?? NaN).toFixed(1))
    const knee=jointFrames.value.map(f => +(f.lk ?? NaN).toFixed(1))
    const ankle=jointFrames.value.map(f => +(f.la ?? NaN).toFixed(1))
    c.setOption({ tooltip:tooltipTheme(),
      grid: dg(),
      xAxis: { type:'category',name:'时间(s)',nameTextStyle:{color:'#64748b',fontSize:11},data:T.map(v=>v.toFixed(1)),axisLabel:{color:'#475569',fontSize:10,interval:9},...da() },
      yAxis: { type:'value',name:'关节角度(°)',nameTextStyle:{color:'#64748b',fontSize:11},...da() },
      legend: { data:['髋','膝','踝'],textStyle:{color:'#94a3b8',fontSize:11},right:0,top:0 },
      series: [
        { name:'髋',type:'line',data:hip,smooth:true,symbol:'none',lineStyle:{color:'#6366f1',width:1.8} },
        { name:'膝',type:'line',data:knee,smooth:true,symbol:'none',lineStyle:{color:'#38bdf8',width:1.8} },
        { name:'踝',type:'line',data:ankle,smooth:true,symbol:'none',lineStyle:{color:'#10b981',width:1.8} }
      ]
    })
    charts.push(c)
  }

  // 2. ROM 雷达图
  if (romRef.value) {
    const c = echarts.init(romRef.value)
    c.setOption({ tooltip:tooltipTheme(),
      radar: { center:['50%','50%'],radius:'50%',
        indicator:[{name:'髋屈伸ROM',max:30},{name:'膝屈伸ROM',max:40},{name:'踝背屈ROM',max:20},{name:'踝跖屈ROM',max:20},{name:'髋外展ROM',max:20}],
        axisName:{color:'#94a3b8',fontSize:11},axisLine:{lineStyle:{color:'#334155'}},splitLine:{lineStyle:{color:'#e2e8f0'}} },
      legend: { data:['左侧','右侧'],textStyle:{color:'#94a3b8',fontSize:11},bottom:0 },
      series: [{
        type:'radar',
        data: [
          { name:'左侧',value:[+jointROM.value.leftHipROM.toFixed(1),+jointROM.value.leftKneeROM.toFixed(1),14.0,12.6,10.0],itemStyle:{color:'#38bdf8'},lineStyle:{color:'#38bdf8',width:1.5},areaStyle:{color:'rgba(56,189,248,0.2)'},symbol:'circle',symbolSize:4 },
          { name:'右侧',value:[+jointROM.value.rightHipROM.toFixed(1),+jointROM.value.rightKneeROM.toFixed(1),15.0,13.3,9.0],itemStyle:{color:'#10b981'},lineStyle:{color:'#10b981',width:1.5},areaStyle:{color:'rgba(16,185,129,0.15)'},symbol:'circle',symbolSize:4 }
        ]
      }]
    })
    charts.push(c)
  }

  // 3. 角速度/角加速度
  if (angularRef.value) {
    const c = echarts.init(angularRef.value)
    const validKF = jointFrames.value.filter(f => f.lk !== null)
    const Tk = validKF.map(f => f.t)
    const kAng = validKF.map(f => f.lk)
    const av = kAng.map((v,i) => i===0 ? 0 : +((v - kAng[i-1]) / (Tk[i] - Tk[i-1])).toFixed(1))
    const aa=[]; av.forEach((v,i)=>{aa.push(i===0?0:+((v-av[i-1])/(Tk[i]-Tk[i-1])).toFixed(1));})
    c.setOption({ tooltip:tooltipTheme(),
      grid: dg(),
      xAxis: { type:'category',data:Tk.map(v=>v.toFixed(1)),axisLabel:{color:'#475569',fontSize:10,interval:9},...da() },
      yAxis: [
        { type:'value',name:'角速度(°/s)',nameTextStyle:{color:'#38bdf8',fontSize:11},...da() },
        { type:'value',name:'角加速度(°/s²)',nameTextStyle:{color:'#f59e0b',fontSize:11},...da() }
      ],
      legend: { data:['角速度','角加速度'],textStyle:{color:'#94a3b8',fontSize:11},right:0,top:0 },
      series: [
        { name:'角速度',type:'line',data:av,smooth:true,symbol:'none',lineStyle:{color:'#38bdf8',width:1.8} },
        { name:'角加速度',type:'line',yAxisIndex:1,data:aa,smooth:true,symbol:'none',lineStyle:{color:'#f59e0b',width:1.2,type:'dashed'} }
      ]
    })
    charts.push(c)
  }

  // 4. 制动变向瞬间角度
  if (brakeRef.value) {
    const c = echarts.init(brakeRef.value)
    // Use actual joint data at key time points for braking analysis
    const brakeTimes = [1.2, 6.3, 10.8, 15.6, 20.4, 25.5]
    const segs = ['段1','段2','段4','段8','段10','段13']
    const brakeFrames = brakeTimes.map(t => jointFrames.value.find(f => Math.abs(f.t - t) < 0.15))
    const hipB = brakeFrames.map(f => +(f?.lh ?? 0).toFixed(0))
    const kneeB = brakeFrames.map(f => +(f?.lk ?? 0).toFixed(0))
    const ankleB = brakeFrames.map(f => +(f?.la ?? 0).toFixed(0))
    c.setOption({ tooltip:tooltipTheme(),
      grid: dg(),
      xAxis: { type:'category',data:segs,axisLabel:{color:'#94a3b8',fontSize:11},...da() },
      yAxis: { type:'value',name:'关节角度(°)',nameTextStyle:{color:'#64748b',fontSize:11},...da() },
      legend: { data:['髋','膝','踝'],textStyle:{color:'#94a3b8',fontSize:11},right:0,top:0 },
      series: [
        { name:'髋',type:'bar',data:hipB,itemStyle:{color:'#6366f1',borderRadius:[3,3,0,0]} },
        { name:'膝',type:'bar',data:kneeB,itemStyle:{color:'#38bdf8',borderRadius:[3,3,0,0]} },
        { name:'踝',type:'bar',data:ankleB,itemStyle:{color:'#10b981',borderRadius:[3,3,0,0]} },
        { type:'line',markLine:{silent:true,symbol:'none',lineStyle:{color:'#ef4444',type:'dashed',width:1},label:{color:'#ef4444',fontSize:10,formatter:'膝理想范围'},data:[{yAxis:130}]},data:[],lineStyle:{opacity:0},itemStyle:{opacity:0} }
      ]
    })
    charts.push(c)
  }
})

onBeforeUnmount(() => { charts.forEach(c => c.dispose()) })
</script>
