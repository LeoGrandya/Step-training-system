<!-- 运行时必需。报告卡片：Linear 风格白卡。 -->
<template>
  <div class="rc-card" :class="{ 'rc-card--sel': selected }" @click="$emit('toggle-select', report.id)">
    <div class="rc-card__bar">
      <label class="rc-card__check" @click.stop>
        <input type="checkbox" :checked="selected" @change="$emit('toggle-select', report.id)" />
        <span class="rc-card__checkmk" />
      </label>
      <span class="rc-card__date">{{ report.date }}</span>
      <span class="rc-card__mode" :data-mode="report.mode">{{ modeLabel }}</span>
      <button type="button" class="rc-card__del" @click.stop="$emit('delete', report.id)" aria-label="删除">&times;</button>
    </div>

    <h3 class="rc-card__step">{{ report.stepName }}</h3>

    <div class="rc-card__metrics">
      <div class="rc-card__m">
        <span class="rc-card__ml">循环数</span>
        <span class="rc-card__mv">{{ report.summary.loops }}</span>
      </div>
      <div class="rc-card__m">
        <span class="rc-card__ml">均速</span>
        <span class="rc-card__mv">{{ report.summary.avgSpeed.toFixed(2) }}<small> m/s</small></span>
      </div>
      <div class="rc-card__m">
        <span class="rc-card__ml">对称性</span>
        <span class="rc-card__mv">{{ report.summary.symmetry }}<small> %</small></span>
      </div>
      <div class="rc-card__m">
        <span class="rc-card__ml">时长</span>
        <span class="rc-card__mv">{{ report.summary.totalTime.toFixed(1) }}<small> s</small></span>
      </div>
      <div class="rc-card__m">
        <span class="rc-card__ml">峰值加速度</span>
        <span class="rc-card__mv">{{ report.summary.peakAccel.toFixed(2) }}<small> m/s²</small></span>
      </div>
    </div>

    <a :href="'/#/report/' + encodeURIComponent(report.jobId)" class="rc-card__link" @click.stop>查看详情 &rarr;</a>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  report: { type: Object, required: true },
  selected: { type: Boolean, default: false },
})
defineEmits(['toggle-select', 'delete'])
const modeMap = { eval: '练习评估', practice: '自由练习', test: '能力测试' }
const modeLabel = computed(() => modeMap[props.report.mode] || props.report.mode)
</script>

<style scoped>
.rc-card {
  background: #fff;
  border: 1px solid rgba(0,0,0,0.07);
  border-radius: 10px;
  padding: 18px;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.rc-card:hover { border-color: rgba(0,0,0,0.13); box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
.rc-card--sel { border-color: #2563eb; box-shadow: 0 0 0 2px rgba(37,99,235,0.10); }

.rc-card__bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.rc-card__check { position: relative; display: flex; }
.rc-card__check input { position: absolute; opacity: 0; }
.rc-card__checkmk {
  width: 18px; height: 18px;
  border: 2px solid #cbd5e1;
  border-radius: 5px;
  transition: background 0.12s, border-color 0.12s;
}
.rc-card--sel .rc-card__checkmk { background: #2563eb; border-color: #2563eb; }
.rc-card__date { font-size: 13px; font-weight: 500; color: #1e293b; }
.rc-card__mode {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 4px;
  color: #475569;
  background: #f1f5f9;
}
.rc-card__mode[data-mode="test"] { color: #7c3aed; background: #f5f3ff; }
.rc-card__del {
  margin-left: auto;
  border: none;
  background: transparent;
  font-size: 18px;
  color: #94a3b8;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  line-height: 1;
  transition: color 0.12s;
}
.rc-card__del:hover { color: #dc2626; }

.rc-card__step {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
  margin: 0 0 14px;
}

.rc-card__metrics {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 10px 14px;
  margin-bottom: 14px;
}
.rc-card__m { display: flex; flex-direction: column; gap: 2px; }
.rc-card__ml { font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.04em; }
.rc-card__mv { font-size: 18px; font-weight: 600; color: #1e293b; }
.rc-card__mv small { font-size: 12px; font-weight: 400; color: #94a3b8; }

.rc-card__link {
  font-size: 13px;
  font-weight: 500;
  color: #2563eb;
  text-decoration: none;
  transition: opacity 0.12s;
}
.rc-card__link:hover { opacity: 0.7; }
</style>
