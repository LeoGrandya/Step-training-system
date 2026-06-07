<!-- 运行时必需。训练页右下角示范视频预览。 -->
<template>
  <button
    type="button"
    class="footwork-demo-preview"
    :aria-label="ariaLabel"
    @click="emit('open')"
  >
    <span class="footwork-demo-preview__label">{{ stepLabel }} · 步伐示范</span>
    <div :key="stepType" class="footwork-demo-preview__media">
      <img
        v-if="showPosterImage"
        class="footwork-demo-preview__thumb"
        :src="posterUrl"
        alt=""
        @load="onPosterLoad"
        @error="onPosterError"
      />
      <video
        v-if="showVideoElement"
        class="footwork-demo-preview__thumb"
        :src="videoUrl"
        muted
        playsinline
        preload="metadata"
        @loadeddata="onVideoLoad"
        @error="onVideoError"
      />
      <div v-if="mediaState === 'empty'" class="footwork-demo-preview__fallback">
        <span class="footwork-demo-preview__fallback-title">暂无教程</span>
        <span class="footwork-demo-preview__fallback-hint">点击可查看全部步伐</span>
      </div>
      <p v-else-if="mediaState === 'loading'" class="footwork-demo-preview__loading">加载预览…</p>
      <div class="footwork-demo-preview__overlay" aria-hidden="true">
        <span class="footwork-demo-preview__play">▶</span>
        <span class="footwork-demo-preview__hint">点击播放</span>
      </div>
    </div>
  </button>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { getFootworkDemoPosterUrl, getFootworkDemoVideoUrl } from '../services/footworkDemoVideos.js';
import { getPresetStepLabel } from '../services/presetSteps.js';

const props = defineProps({
  stepType: { type: String, default: 'single-step' },
});

const emit = defineEmits(['open']);

const mediaState = ref('loading');
const showPosterImage = ref(true);
const showVideoElement = ref(false);

const posterUrl = computed(() => getFootworkDemoPosterUrl(props.stepType));
const videoUrl = computed(() => getFootworkDemoVideoUrl(props.stepType));
const stepLabel = computed(() => getPresetStepLabel(props.stepType));
const ariaLabel = computed(() => `查看${stepLabel.value}步伐示范`);

function resetMedia() {
  mediaState.value = 'loading';
  showPosterImage.value = true;
  showVideoElement.value = false;
}

function onPosterLoad() {
  mediaState.value = 'poster';
  showVideoElement.value = false;
}

function onPosterError() {
  showPosterImage.value = false;
  showVideoElement.value = true;
  if (mediaState.value !== 'video') {
    mediaState.value = 'loading';
  }
}

function onVideoLoad() {
  mediaState.value = 'video';
}

function onVideoError() {
  showVideoElement.value = false;
  mediaState.value = 'empty';
}

watch(
  () => props.stepType,
  () => resetMedia(),
  { immediate: true },
);
</script>
