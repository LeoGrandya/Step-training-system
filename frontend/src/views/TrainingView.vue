<!-- 运行时必需。训练模式页：档案 + 模式选择 + TrainingGrid。 -->
<template>
  <section class="page-stack training-page">
    <header class="training-header">
      <div class="training-header__center">
        <p class="eyebrow">训练模式</p>
        <h1>九宫格步伐训练</h1>
        <p class="profile-summary">{{ profileSummary }}</p>
      </div>
      <button class="training-header__edit" @click="editingProfile = !editingProfile">
        {{ editingProfile ? '收起资料' : '修改基础信息' }}
      </button>
    </header>

    <ProfileForm
      v-if="editingProfile || !profile.name"
      class="profile-form--expanded"
      :profile="profile"
      @save="saveProfileAndClose"
    />

    <section v-if="profile.name && !selectedMode" class="mode-picker" data-guide="mode-picker">
      <div class="mode-picker__intro">
        <p class="eyebrow">选择训练模式</p>
        <h2>请选择所需的训练模式</h2>
      </div>
      <div class="mode-picker__grid">
        <button v-for="modeItem in modes" :key="modeItem.value" class="mode-card mode-card--choice" @click="chooseMode(modeItem.value)">
          <span>{{ modeItem.kicker }}</span>
          <strong>{{ modeItem.label }}</strong>
          <small>{{ modeItem.desc }}</small>
        </button>
      </div>
    </section>

    <section v-if="profile.name && selectedMode" class="page-stack training-workspace">
      <div class="training-actions">
        <button type="button" class="secondary-button" @click="replayGuide">新手引导</button>
        <button class="secondary-button" @click="selectedMode = ''">重新选择模式</button>
        <RouterLink v-if="analysisVisible" class="secondary-action" to="/analysis">上传视频分析</RouterLink>
      </div>
      <TrainingGrid :mode="selectedMode" :profile="profile" :locked="selectedMode === 'test'" />
    </section>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { notifyTrainingModeSelected, setTrainingHasMode } from '../guides/guideScheduler.js';
import { replayTrainingGuide } from '../guides/trainingGuide.js';
import ProfileForm from '../components/ProfileForm.vue';
import TrainingGrid from '../components/TrainingGrid.vue';
import { getProfile, getTrainingMode, saveProfile, saveTrainingMode, getCurrentSubjectId } from '../stores/storage.js';
import { request } from '../services/api.js';
import { subjectChangeCounter } from '../stores/subjectEvents.js';

const route = useRoute();
const router = useRouter();
const profile = ref(getProfile());
const selectedMode = ref(route.query.selectMode ? '' : getTrainingMode());
const editingProfile = ref(!profile.value.name);

async function loadSubjectProfile() {
  const subjectId = getCurrentSubjectId();
  if (!subjectId) return;
  try {
    const response = await fetch(`/api/users/${encodeURIComponent(subjectId)}`);
    const payload = await response.json().catch(() => ({}));
    if (response.ok && payload.ok && payload.user) {
      const u = payload.user;
      const p = {
        name: u.name || '',
        age: u.age ?? 25,
        heightCm: u.heightCm ?? 170,
        weightKg: u.weightKg ?? 65,
        hand: u.hand || '右手',
        years: u.years ?? 0,
        level: u.level || '业余',
      };
      profile.value = p;
      saveProfile(p); // 同步到本地缓存
      editingProfile.value = !p.name;
    }
  } catch {}
}

async function saveProfileToAPI(nextProfile) {
  const subjectId = getCurrentSubjectId();
  if (subjectId) {
    await request(`/api/users/${encodeURIComponent(subjectId)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(nextProfile),
    });
  }
}

const modes = [
  { value: '练习评估', kicker: 'Eval', label: '练习评估', desc: '开放步伐配置，训练后保留视频分析入口。' },
  { value: '自由练习', kicker: 'Free', label: '自由练习', desc: '用于热身和纯训练，默认隐藏分析入口。' },
  { value: '能力测试', kicker: 'Test', label: '能力测试', desc: '按等级锁定标准步伐，并保留分析入口生成报告。' },
];

const modeMap = {
  eval: '练习评估',
  free: '自由练习',
  test: '能力测试',
  '练习评估': '练习评估',
  '自由练习': '自由练习',
  '能力测试': '能力测试',
};

const handLabel = computed(() => (profile.value.hand === '左手' ? '左手持拍' : '右手持拍'));
const levelLabel = computed(() => {
  const map = { '业余': '业余', '二级': '二级', '一级': '一级' };
  return map[profile.value.level] || '业余';
});
const currentModeLabel = computed(() => modeMap[selectedMode.value] || '未选择模式');
const profileSummary = computed(() => {
  const name = profile.value.name || '训练用户';
  return `${name} · ${handLabel.value} · ${profile.value.years} 年训练 · ${levelLabel.value} · ${currentModeLabel.value}`;
});
const analysisVisible = computed(() => selectedMode.value !== '自由练习' && selectedMode.value !== 'free');

function goAnalysis() {
  router.push('/analysis');
}

function chooseMode(mode) {
  selectedMode.value = saveTrainingMode(mode, { baseLevel: profile.value.level || '' });
  notifyTrainingModeSelected({ onGoAnalysis: goAnalysis });
}

function replayGuide() {
  replayTrainingGuide({
    hasSelectedMode: Boolean(selectedMode.value),
    onGoAnalysis: goAnalysis,
  });
}

onMounted(async () => {
  setTrainingHasMode(() => Boolean(selectedMode.value));
  await loadSubjectProfile();
});
watch(subjectChangeCounter, loadSubjectProfile);

watch(selectedMode, () => {
  setTrainingHasMode(() => Boolean(selectedMode.value));
});

async function saveProfileAndClose(nextProfile) {
  profile.value = saveProfile(nextProfile);
  editingProfile.value = false;
  if (selectedMode.value) saveTrainingMode(selectedMode.value, { baseLevel: profile.value.level || '' });
  await saveProfileToAPI(nextProfile);
}
</script>
