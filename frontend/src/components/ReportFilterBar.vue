<!-- 运行时必需。历史报告筛选栏：用户切换 + 档案折叠 + 模式/日期/搜索 + 重置。 -->
<template>
  <div class="report-filter-bar">
    <div class="report-filter-bar__row">
      <div class="report-filter-bar__group">
        <label class="report-filter-bar__label">用户</label>
        <select :value="userId" @change="onUserChange" class="report-filter-bar__select">
          <option v-for="u in users" :key="u.id" :value="u.id">{{ u.name || u.id }}</option>
        </select>
      </div>

      <button
        v-if="userProfile"
        type="button"
        class="report-filter-bar__profile-toggle"
        :class="{ 'report-filter-bar__profile-toggle--open': profileOpen }"
        @click="profileOpen = !profileOpen"
      >档案 {{ profileOpen ? '▾' : '▸' }}</button>

      <div class="report-filter-bar__divider"></div>

      <div class="report-filter-bar__group">
        <label class="report-filter-bar__label">模式</label>
        <select :value="filters.mode" @change="$emit('update:filters', { ...filters, mode: $event.target.value })" class="report-filter-bar__select">
          <option value="">全部</option>
          <option value="eval">练习评估</option>
          <option value="practice">自由练习</option>
          <option value="test">能力测试</option>
        </select>
      </div>

      <div class="report-filter-bar__group report-filter-bar__group--date">
        <label class="report-filter-bar__label">日期</label>
        <input type="date" :value="filters.startDate" @change="$emit('update:filters', { ...filters, startDate: $event.target.value })" class="report-filter-bar__input" />
        <span class="report-filter-bar__date-sep">至</span>
        <input type="date" :value="filters.endDate" @change="$emit('update:filters', { ...filters, endDate: $event.target.value })" class="report-filter-bar__input" />
      </div>

      <div class="report-filter-bar__group report-filter-bar__group--search">
        <label class="report-filter-bar__label sr-only">搜索步伐</label>
        <input
          type="text"
          class="report-filter-bar__input"
          placeholder="搜索步伐名称"
          :value="filters.stepName"
          @input="onSearchInput"
        />
      </div>

      <button type="button" class="secondary-button report-filter-bar__reset" @click="$emit('reset')">重置</button>
    </div>

    <div v-if="userProfile && profileOpen" class="report-filter-bar__profile">
      <div class="report-filter-bar__profile-item"><span>姓名</span><strong>{{ userProfile.name || '-' }}</strong></div>
      <div class="report-filter-bar__profile-item"><span>年龄</span><strong>{{ userProfile.age || 0 }}岁</strong></div>
      <div class="report-filter-bar__profile-item"><span>身高</span><strong>{{ (userProfile.heightCm || userProfile.height_cm || 0) }}cm</strong></div>
      <div class="report-filter-bar__profile-item"><span>体重</span><strong>{{ (userProfile.weightKg || userProfile.weight_kg || 0) }}kg</strong></div>
      <div class="report-filter-bar__profile-item"><span>持拍手</span><strong>{{ handLabel(userProfile.hand) }}</strong></div>
      <div class="report-filter-bar__profile-item"><span>级别</span><strong>{{ levelLabel(userProfile.level) }}</strong></div>
    </div>
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

const handMap = { right: '右手', left: '左手' }
const levelMap = { 'level-2': '二级', 'level-1': '一级', amateur: '业余' }

function handLabel(h) { return handMap[h] || h || '-' }
function levelLabel(l) { return levelMap[l] || l || '-' }

function onUserChange(e) {
  profileOpen.value = false
  emit('update:userId', e.target.value)
}

// 300ms 防抖，避免每次按键都触发 API 查询
function onSearchInput(e) {
  if (searchTimer) window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => {
    emit('update:filters', { ...props.filters, stepName: e.target.value })
    searchTimer = null
  }, 300)
}
</script>
