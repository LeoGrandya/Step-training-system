<!-- 运行时必需。步伐示范视频弹窗（多步伐切换）。 -->
<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="footwork-demo-overlay"
      role="presentation"
      @click.self="emit('close')"
    >
      <div
        class="footwork-demo-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="footwork-demo-title"
      >
        <header class="footwork-demo-dialog__header">
          <h2 id="footwork-demo-title">步伐示范</h2>
          <button type="button" class="footwork-demo-dialog__close" @click="emit('close')">关闭</button>
        </header>

        <div class="footwork-demo-dialog__body">
          <nav class="footwork-demo-list" aria-label="选择步伐">
            <div v-for="group in demoGroups" :key="group.label" class="footwork-demo-list__group">
              <p class="footwork-demo-list__group-label">{{ group.label }}</p>
              <button
                v-for="option in group.options"
                :key="option.value"
                type="button"
                class="footwork-demo-list__item"
                :class="{ 'is-active': selectedStepType === option.value }"
                :aria-selected="selectedStepType === option.value"
                @click="selectStep(option.value)"
              >
                {{ option.label }}
              </button>
            </div>
          </nav>

          <div class="footwork-demo-player">
            <h3 class="footwork-demo-player__title">{{ playerTitle }}</h3>
            <div class="footwork-demo-player__stage">
              <video
                v-show="videoStatus === 'ready'"
                :key="selectedStepType"
                class="footwork-demo-player__video"
                :src="videoUrl"
                controls
                playsinline
                preload="metadata"
                @loadeddata="onVideoLoaded"
                @error="onVideoError"
              />
              <p v-if="videoStatus === 'loading'" class="footwork-demo-player__placeholder">加载中…</p>
              <div v-else-if="videoStatus === 'empty'" class="footwork-demo-player__placeholder">
                <strong>暂无教程</strong>
                <span>请将示范视频放到 <code>app/public/videos/footwork/{{ selectedStepType }}.mp4</code>，详见项目根目录「最小启动方式.md」。</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { getFootworkDemoVideoUrl, listFootworkDemoGroups } from '../services/footworkDemoVideos.js';
import { getPresetStepLabel } from '../services/presetSteps.js';

const props = defineProps({
  open: { type: Boolean, default: false },
  initialStepType: { type: String, default: 'single-step' },
});

const emit = defineEmits(['close']);

const demoGroups = listFootworkDemoGroups();
const selectedStepType = ref('single-step');
const videoStatus = ref('loading');

const videoUrl = computed(() => getFootworkDemoVideoUrl(selectedStepType.value));
const playerTitle = computed(() => getPresetStepLabel(selectedStepType.value));

watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) return;
    selectedStepType.value = props.initialStepType || 'single-step';
    videoStatus.value = 'loading';
  },
);

watch(selectedStepType, () => {
  videoStatus.value = 'loading';
});

function selectStep(value) {
  selectedStepType.value = value;
}

function onVideoLoaded() {
  videoStatus.value = 'ready';
}

function onVideoError() {
  videoStatus.value = 'empty';
}

function onKeydown(event) {
  if (event.key === 'Escape' && props.open) emit('close');
}

onMounted(() => window.addEventListener('keydown', onKeydown));
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown));
</script>
