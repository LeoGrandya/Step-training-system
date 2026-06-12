<!-- 运行时必需。训练九宫格：预置/自定义步伐、计时、硬件 API、示范视频与参数持久化。 -->
<template>
  <section class="training-layout">
    <aside class="panel training-panel" data-guide="params">
      <h2>训练参数</h2>
      <label>步伐来源
        <select v-model="stepSource" :disabled="locked">
          <option value="preset">预置步伐</option>
          <option value="custom">自定义落点序列</option>
        </select>
      </label>
      <label v-if="stepSource === 'preset'">训练步伐
        <select v-model="stepType" :disabled="locked">
          <optgroup v-for="group in PRESET_STEP_OPTION_GROUPS" :key="group.label" :label="group.label">
            <option v-for="option in group.options" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </optgroup>
        </select>
        <p class="interval-recommendation">{{ stepLogicHint }}</p>
        <p v-if="stepHandRequirement" class="step-hand-requirement">{{ stepHandRequirement }}</p>
      </label>
      <template v-else>
        <label>已保存的跑动序列
          <span v-if="customFootworks.length" style="display:flex; gap:6px;">
            <select v-model="selectedCustomId" @change="applyCustomFootwork">
              <option v-for="item in customFootworks" :key="item.id" :value="item.id">
                {{ item.name }}
              </option>
            </select>
            <button type="button" class="secondary-button" @click="newCustomSequence">新建</button>
          </span>
          <button v-else type="button" class="secondary-button" @click="newCustomSequence">新建跑动序列</button>
        </label>
        <label>序列名称<input v-model.trim="customName" type="text" placeholder="给序列起个名字" /></label>
        <label>起始格<input v-model.number="customStartCell" type="number" min="1" max="9" /></label>
        <label>落点序列
          <button type="button" class="seq-preview-trigger" @click="seqPickerOpen = true">
            <span v-if="customSequence" class="seq-preview-trigger__badges">
              <span v-for="(cell, idx) in customSequence.split(',').filter(c => /^[1-9]$/.test(c.trim()))" :key="idx" class="seq-preview-trigger__badge">
                {{ cell.trim() }}
                <span v-if="idx < customSequence.split(',').filter(c => /^[1-9]$/.test(c.trim())).length - 1" class="seq-preview-trigger__arrow">&rarr;</span>
              </span>
            </span>
            <span v-else class="seq-preview-trigger__placeholder">点击九宫格选择落点序列</span>
          </button>
        </label>
        <SequenceGridPicker
          :open="seqPickerOpen"
          :modelValue="customSequence"
          :startCell="customStartCell"
          @update:modelValue="customSequence = $event"
          @close="seqPickerOpen = false"
        />
        <p v-if="customActionRequirements" class="step-hand-requirement">{{ customActionRequirements }}</p>
        <p v-if="customRhythm && customRhythm.defaultMs" class="interval-recommendation">
          节奏：{{ customRhythm.defaultMs }} ms
        </p>
        <button type="button" class="secondary-button" @click="saveCustomFootwork">保存当前序列到库</button>
      </template>
      <label>亮灯时长(ms)<input v-model.number="lightDuration" type="number" min="200" max="3000" step="50" /></label>
      <label class="interval-field">步伐间隔(ms)
        <input v-model.number="stepInterval" type="number" min="400" max="5000" step="100" />
        <p v-if="stepSource === 'preset'" class="interval-recommendation">{{ recommendedIntervalHint }}</p>
        <p v-else class="interval-recommendation">自定义序列请按难度自行调整间隔</p>
      </label>
      <label v-if="isFullTablePreset">产生多少步
        <input v-model.number="fullTableStepCount" type="number" min="5" max="99" />
      </label>
      <label v-else>循环次数<input v-model.number="loopCount" type="number" min="1" max="99" /></label>
    </aside>

    <main class="training-stage" data-guide="grid">
      <div class="status-panel">{{ statusText }}</div>
      <div class="grid-board">
        <div
          v-for="cell in 9"
          :key="cell"
          class="grid-cell"
          :class="{
            active: activeCell === cell && activeStepType === 'active',
            ready: showStartCellReady && cell === startCell && !activeCell,
          }"
        >
          {{ cell }}
        </div>
      </div>
      <RouterLink v-if="mode !== '自由练习'" class="muted-link" to="/analysis">训练结束后上传左右机位视频进行分析</RouterLink>
      <p v-else class="hint">自由练习模式默认不进入视频分析，可重新选择“练习评估”或“能力测试”。</p>
    </main>

    <aside class="panel training-panel" data-guide="controls">
      <h2>训练控制</h2>
      <button @click="prepare">{{ ready ? '取消准备' : '准备' }}</button>
      <button :disabled="!ready || running || countdown" @click="start">开始</button>
      <button :disabled="!running && !countdown" @click="stop()">停止</button>
      <div class="sequence-preview">
        <strong>当前序列</strong>
        <p>{{ sequencePreview }}</p>
      </div>
      <FootworkDemoPreview
        data-guide="demo-preview"
        :step-type="demoInitialStepType"
        @open="demoOpen = true"
      />
    </aside>

    <FootworkDemoModal
      :open="demoOpen"
      :initial-step-type="demoInitialStepType"
      @close="demoOpen = false"
    />
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import FootworkDemoModal from './FootworkDemoModal.vue';
import FootworkDemoPreview from './FootworkDemoPreview.vue';
import SequenceGridPicker from './SequenceGridPicker.vue';
import {
  createCustomFootwork,
  listCustomFootworks,
  triggerHardwareStart,
} from '../services/api.js';
import {
  getHardwareFeedbackEnabled,
  loadTrainingPrefs,
  saveTrainingPrefs,
  setHardwareFeedbackEnabled,
} from '../stores/storage.js';
import { formatRecommendedIntervalHint } from '../services/recommendedStepIntervals.js';
import { playStepCueSound } from '../services/stepCueSound.js';
import { cancelStartCueSpeech, speakStartCue } from '../services/startCueSpeech.js';
import {
  DEFAULT_FULL_TABLE_STEP_COUNT,
  PRESET_STEP_OPTION_GROUPS,
  formatTrainingStep,
  generatePresetSteps,
  getDefaultLoopCount,
  getPresetHandRequirement,
  getPresetStartCell,
  getPresetStepLogicHint,
  getPresetStepLabel,
} from '../services/presetSteps.js';

const props = defineProps({
  mode: { type: String, default: '练习评估' },
  profile: { type: Object, required: true },
  locked: { type: Boolean, default: false },
});

const activeCell = ref(0);
const activeStepType = ref('');
const ready = ref(false);
const showStartCellReady = ref(false);
const running = ref(false);
const countdown = ref(false);
const statusText = ref('请选择参数后点击“准备”。');
const stepSource = ref('preset');
const stepType = ref(resolveDefaultStepType());
const customName = ref('');
const customStartCell = ref(5);
const customSequence = ref('5,4,6,5');
const customActionRequirements = ref('');
const customRhythm = ref(null);
const lightDuration = ref(800);
const stepInterval = ref(1200);
const loopCount = ref(getDefaultLoopCount(stepType.value));
const fullTableStepCount = ref(DEFAULT_FULL_TABLE_STEP_COUNT);
const cachedSequence = ref([]);
const customFootworks = ref([]);
const selectedCustomId = ref('');
const hardwareFeedback = ref(true);
const seqPickerOpen = ref(false);
const demoOpen = ref(false);
const demoInitialStepType = computed(() => (
  stepSource.value === 'preset' ? stepType.value : 'single-step'
));
const stepLogicHint = computed(() => getPresetStepLogicHint(stepType.value));
const stepHandRequirement = computed(() => {
  const text = getPresetHandRequirement(stepType.value, profileHand.value);
  return text ? `手部要求：${text}` : '';
});

const recommendedIntervalHint = computed(() => formatRecommendedIntervalHint(stepType.value, {
  level: props.profile.level,
  mode: props.mode,
}));
let timers = [];
let currentIndex = 0;
let prefsHydrated = false;
let savePrefsTimer = null;

const profileHand = computed(() => (
  props.profile.hand === 'left' || props.profile.hand === '左手' ? 'left' : 'right'
));
const isFullTablePreset = computed(() => (
  stepSource.value === 'preset' && stepType.value === 'full-table'
));
const startCell = computed(() => (
  stepSource.value === 'custom'
    ? clampCell(customStartCell.value)
    : getPresetStartCell(stepType.value, profileHand.value)
));
const sequencePreview = computed(() => {
  const sequence = cachedSequence.value;
  if (!ready.value || !sequence.length) return '点击“准备”后生成本轮序列。';
  return sequence.map(formatTrainingStep).join(' → ');
});

watch(
  () => [props.mode, props.profile.level],
  () => {
    if (props.mode === '能力测试') {
      stepSource.value = 'preset';
      stepType.value = resolveDefaultStepType();
    }
    cancelReady('模式或资料已更新，请重新准备。');
  },
);

watch(stepType, (type) => {
  if (type !== 'full-table') {
    loopCount.value = getDefaultLoopCount(type);
  }
  if (!prefsHydrated) return;
  cancelReady('步伐类型已更新，请重新准备。');
});

watch(
  () => [
    stepSource.value,
    stepType.value,
    customName.value,
    customStartCell.value,
    customSequence.value,
    customActionRequirements.value,
    customRhythm.value,
    loopCount.value,
    fullTableStepCount.value,
    lightDuration.value,
    stepInterval.value,
    selectedCustomId.value,
    profileHand.value,
  ],
  () => {
    if (!prefsHydrated) return;
    if (ready.value || running.value) cancelReady('训练参数已更新，请重新准备。');
  },
);

watch(
  [
    stepSource,
    stepType,
    lightDuration,
    stepInterval,
    loopCount,
    fullTableStepCount,
    hardwareFeedback,
    customName,
    customStartCell,
    customSequence,
    customActionRequirements,
    customRhythm,
    selectedCustomId,
  ],
  () => {
    scheduleSaveTrainingPrefs();
  },
);

watch(hardwareFeedback, (enabled) => {
  setHardwareFeedbackEnabled(enabled);
});

function collectTrainingPrefs() {
  return {
    stepSource: stepSource.value,
    stepType: stepType.value,
    lightDuration: lightDuration.value,
    stepInterval: stepInterval.value,
    loopCount: loopCount.value,
    fullTableStepCount: fullTableStepCount.value,
    hardwareFeedback: hardwareFeedback.value,
    customName: customName.value,
    customStartCell: customStartCell.value,
    customSequence: customSequence.value,
    customActionRequirements: customActionRequirements.value,
    customRhythm: customRhythm.value,
    selectedCustomId: selectedCustomId.value,
  };
}

function scheduleSaveTrainingPrefs() {
  if (!prefsHydrated) return;
  if (savePrefsTimer) window.clearTimeout(savePrefsTimer);
  savePrefsTimer = window.setTimeout(() => {
    saveTrainingPrefs(collectTrainingPrefs());
    savePrefsTimer = null;
  }, 300);
}

function applyTrainingPrefs(prefs) {
  stepSource.value = prefs.stepSource;
  stepType.value = prefs.stepType;
  lightDuration.value = prefs.lightDuration;
  stepInterval.value = prefs.stepInterval;
  loopCount.value = prefs.loopCount;
  fullTableStepCount.value = prefs.fullTableStepCount;
  hardwareFeedback.value = prefs.hardwareFeedback;
  customName.value = prefs.customName;
  customStartCell.value = prefs.customStartCell;
  customSequence.value = prefs.customSequence;
  customActionRequirements.value = prefs.customActionRequirements || '';
  customRhythm.value = prefs.customRhythm || null;
  selectedCustomId.value = prefs.selectedCustomId;
  setHardwareFeedbackEnabled(prefs.hardwareFeedback);
}

async function loadCustomFootworks() {
  try {
    const payload = await listCustomFootworks();
    customFootworks.value = Array.isArray(payload.items) ? payload.items : [];
  } catch {
    customFootworks.value = [];
  }
}

function newCustomSequence() {
  selectedCustomId.value = '';
  customName.value = '';
  customStartCell.value = 5;
  customSequence.value = '';
  customActionRequirements.value = '';
  customRhythm.value = null;
  seqPickerOpen.value = true;
}

function applyCustomFootwork() {
  const item = customFootworks.value.find((entry) => entry.id === selectedCustomId.value);
  if (!item) return;
  customName.value = item.name || '';
  customStartCell.value = item.startCell || 5;
  customSequence.value = item.sequence || '';
  customActionRequirements.value = item.actionRequirements || '';
  customRhythm.value = item.rhythm && typeof item.rhythm === 'object' ? item.rhythm : null;
  if (customRhythm.value && Number.isFinite(Number(customRhythm.value.defaultMs))) {
    stepInterval.value = Math.min(5000, Math.max(400, Number(customRhythm.value.defaultMs)));
  }
  cancelReady('已载入自定义步伐，请重新准备。');
}

async function saveCustomFootwork() {
  const name = customName.value.trim();
  if (!name) {
    statusText.value = '请先输入序列名称。';
    return;
  }
  try {
    const result = await createCustomFootwork({
      name,
      sequence: customSequence.value,
      startCell: customStartCell.value,
      rhythm: customRhythm.value,
      actionRequirements: customActionRequirements.value,
    });
    await loadCustomFootworks();
    if (result && result.item && result.item.id) {
      selectedCustomId.value = result.item.id;
    }
    statusText.value = `「${name}」已保存。`;
  } catch (error) {
    statusText.value = error.message || '保存跑动序列失败。';
  }
}

async function callHardwareStart() {
  if (!hardwareFeedback.value) return;
  try {
    const result = await triggerHardwareStart();
    if (result && result.ok === false) {
      console.warn('硬件触发响应异常:', result.error);
    }
  } catch (error) {
    console.warn('无法连接硬件接口:', error);
  }
}

function resolveDefaultStepType() {
  if (props.mode !== '能力测试') return 'single-step';
  const byLevel = { 'level-1': 'four-point', 'level-2': 'three-point', amateur: 'two-point', '一级': 'four-point', '二级': 'three-point', '业余': 'two-point' };
  return byLevel[props.profile.level] || 'three-point';
}

function clampCell(value) {
  const n = Number.parseInt(value, 10);
  return Number.isFinite(n) && n >= 1 && n <= 9 ? n : 5;
}

function parseCustomSequence(raw) {
  return String(raw || '')
    .split(',')
    .map((part) => part.trim().toUpperCase())
    .filter(Boolean)
    .map((part) => {
      if (/^W\d+$/.test(part)) return { waitMs: Number.parseInt(part.slice(1), 10) };
      if (/^[1-9]R$/.test(part)) return null;
      if (/^[1-9]$/.test(part)) return { cell: Number.parseInt(part, 10), type: 'active' };
      return null;
    })
    .filter(Boolean);
}

function buildSequence() {
  const repeatOrSteps = stepType.value === 'full-table'
    ? fullTableStepCount.value
    : loopCount.value;
  const steps = stepSource.value === 'custom'
    ? parseCustomSequence(customSequence.value)
    : generatePresetSteps(stepType.value, profileHand.value, repeatOrSteps);
  return steps.length ? steps : [{ cell: startCell.value, type: 'active' }];
}

function runningStatusLabel() {
  if (stepSource.value === 'custom') return '自定义步伐';
  return getPresetStepLabel(stepType.value);
}

function clearTimers() {
  timers.forEach((timer) => window.clearTimeout(timer));
  timers = [];
}

function resetActiveCell() {
  activeCell.value = 0;
  activeStepType.value = '';
}

function cancelReady(message) {
  stop();
  ready.value = false;
  showStartCellReady.value = false;
  cachedSequence.value = [];
  statusText.value = message;
}

function prepare() {
  if (ready.value) {
    cancelReady('请选择参数后点击“准备”。');
    return;
  }
  cachedSequence.value = buildSequence();
  currentIndex = 0;
  resetActiveCell();
  ready.value = true;
  showStartCellReady.value = true;
  statusText.value = cachedSequence.value.length ? '准备就绪，点击“开始”。' : '序列为空，请检查参数。';
}

async function start() {
  if (!ready.value || running.value || countdown.value) return;
  if (!cachedSequence.value.length) cachedSequence.value = buildSequence();
  if (!cachedSequence.value.length) {
    statusText.value = '序列为空，请检查参数。';
    return;
  }
  currentIndex = 0;
  countdown.value = true;
  statusText.value = '正在播放开始提示…';
  await speakStartCue('开始拍摄');
  if (!countdown.value || !ready.value) return;
  if (hardwareFeedback.value) {
    statusText.value = '蜂鸣中，请准备…';
    await callHardwareStart();
    if (!countdown.value || !ready.value) return;
  }
  beginFootworkSequence();
}

function beginFootworkSequence() {
  if (!countdown.value || !ready.value) return;
  countdown.value = false;
  running.value = true;
  currentIndex = 0;
  resetActiveCell();
  statusText.value = runningStatusLabel();
  runNextStep();
}

function runNextStep() {
  if (!running.value) return;
  if (currentIndex >= cachedSequence.value.length) {
    stop('训练完成。');
    return;
  }
  const step = cachedSequence.value[currentIndex];
  currentIndex += 1;
  if (step && typeof step === 'object' && step.waitMs) {
    resetActiveCell();
    timers.push(window.setTimeout(runNextStep, step.waitMs));
    return;
  }
  if (showStartCellReady.value) showStartCellReady.value = false;
  activeCell.value = step.cell;
  activeStepType.value = step.type || 'active';
  playStepCueSound();
  timers.push(window.setTimeout(() => {
    resetActiveCell();
    timers.push(window.setTimeout(runNextStep, Math.max(0, stepInterval.value - lightDuration.value)));
  }, lightDuration.value));
}

function stop(message = '已停止，可重新开始。') {
  clearTimers();
  cancelStartCueSpeech();
  running.value = false;
  countdown.value = false;
  resetActiveCell();
  statusText.value = ready.value ? message : '请选择参数后点击“准备”。';
}

onMounted(async () => {
  applyTrainingPrefs(loadTrainingPrefs());
  if (props.mode === '能力测试') {
    stepSource.value = 'preset';
    stepType.value = resolveDefaultStepType();
  }
  prefsHydrated = true;
  await loadCustomFootworks();
});
onBeforeUnmount(() => {
  clearTimers();
  if (savePrefsTimer) window.clearTimeout(savePrefsTimer);
});
</script>
