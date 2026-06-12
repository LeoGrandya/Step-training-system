<!-- 运行时必需。历史报告筛选栏：Linear 风格。 -->
<template>
  <div class="rfb" :class="{ 'rfb--profile-open': profileOpen }">
    <div class="rfb__row">
      <div class="rfb__group">
        <label class="rfb__lbl">受试者</label>
        <select :value="userId" @change="onUserChange" class="rfb__sel">
          <option v-for="u in users" :key="u.id" :value="u.id">{{ u.displayName || u.name || u.id }}</option>
        </select>
      </div>
      <button v-if="userProfile" type="button" class="rfb__prof-btn" :class="{ 'rfb__prof-btn--open': profileOpen }" @click="profileOpen = !profileOpen">档案 {{ profileOpen ? '▾' : '▸' }}</button>
      <span class="rfb__sep" />
      <div class="rfb__group">
        <label class="rfb__lbl">模式</label>
        <select :value="filters.mode" @change="$emit('update:filters', { ...filters, mode: $event.target.value })" class="rfb__sel">
          <option value="">全部</option>
          <option value="eval">练习评估</option>
          <option value="practice">自由练习</option>
          <option value="test">能力测试</option>
        </select>
      </div>
      <div class="rfb__group rfb__group--date">
        <label class="rfb__lbl">日期</label>
        <input type="date" :value="filters.startDate" @change="$emit('update:filters', { ...filters, startDate: $event.target.value })" class="rfb__inp" />
        <span class="rfb__date-sep">至</span>
        <input type="date" :value="filters.endDate" @change="$emit('update:filters', { ...filters, endDate: $event.target.value })" class="rfb__inp" />
      </div>
      <div class="rfb__group rfb__group--search">
        <input type="text" class="rfb__inp" placeholder="搜索步伐名称" :value="filters.stepName" @input="onSearchInput" />
      </div>
      <button type="button" class="rfb__rst" @click="$emit('reset')">重置</button>
    </div>

    <Transition name="rfb-prof">
      <div v-if="userProfile && profileOpen" class="rfb__prof">
        <div class="rfb__prof-item"><span>姓名</span><strong>{{ userProfile.name || '-' }}</strong></div>
        <div class="rfb__prof-item"><span>年龄</span><strong>{{ userProfile.age || 0 }}岁</strong></div>
        <div class="rfb__prof-item"><span>身高</span><strong>{{ (userProfile.heightCm || userProfile.height_cm || 0) }}cm</strong></div>
        <div class="rfb__prof-item"><span>体重</span><strong>{{ (userProfile.weightKg || userProfile.weight_kg || 0) }}kg</strong></div>
        <div class="rfb__prof-item"><span>持拍手</span><strong>{{ handLabel(userProfile.hand) }}</strong></div>
        <div class="rfb__prof-item"><span>级别</span><strong>{{ levelLabel(userProfile.level) }}</strong></div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const props = defineProps({
  userId: { type: String, default: '' },
  users: { type: Array, default: () => [] },
  userProfile: { type: Object, default: null },
  filters: { type: Object, default: () => ({ mode: '', startDate: '', endDate: '', stepName: '' }) },
})
const emit = defineEmits(['update:userId', 'update:filters', 'reset'])
const profileOpen = ref(false)
let searchTimer = null
const handMap = { '右手': '右手', '左手': '左手' }
const levelMap = { '二级': '二级', '一级': '一级', '业余': '业余' }
function handLabel(h) { return handMap[h] || h || '-' }
function levelLabel(l) { return levelMap[l] || l || '-' }
function onUserChange(e) { profileOpen.value = false; emit('update:userId', e.target.value) }
function onSearchInput(e) {
  if (searchTimer) window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => { emit('update:filters', { ...props.filters, stepName: e.target.value }); searchTimer = null }, 300)
}
</script>

<style scoped>
.rfb {
  background: #fff;
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 20px;
}
.rfb__row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.rfb__group { display: flex; align-items: center; gap: 6px; }
.rfb__lbl { font-size: 12px; color: #94a3b8; white-space: nowrap; }
.rfb__sel, .rfb__inp {
  padding: 6px 10px;
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 6px;
  font-size: 13px;
  font-family: inherit;
  color: #1e293b;
  background: #fff;
  outline: none;
  transition: border-color 0.15s;
}
.rfb__sel:focus, .rfb__inp:focus { border-color: #2563eb; }
.rfb__inp { width: 140px; }
.rfb__date-sep { font-size: 12px; color: #94a3b8; }
.rfb__sep { width: 1px; height: 24px; background: rgba(0,0,0,0.06); }
.rfb__prof-btn {
  border: none;
  background: #f1f5f9;
  color: #475569;
  font-size: 12px;
  padding: 5px 10px;
  border-radius: 5px;
  cursor: pointer;
  transition: background 0.12s;
}
.rfb__prof-btn:hover { background: #e2e8f0; }
.rfb__rst {
  border: 1px solid rgba(0,0,0,0.08);
  background: #fff;
  color: #64748b;
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.12s;
}
.rfb__rst:hover { background: #f8fafc; }

.rfb__prof {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid rgba(0,0,0,0.05);
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.rfb__prof-item { display: flex; flex-direction: column; gap: 2px; }
.rfb__prof-item span { font-size: 11px; color: #94a3b8; }
.rfb__prof-item strong { font-size: 14px; font-weight: 500; color: #1e293b; }

.rfb-prof-enter-active, .rfb-prof-leave-active { transition: opacity 0.2s ease, max-height 0.25s ease; overflow: hidden; }
.rfb-prof-enter-from, .rfb-prof-leave-to { opacity: 0; max-height: 0; }
</style>
