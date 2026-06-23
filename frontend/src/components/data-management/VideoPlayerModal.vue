<!-- 同步视频播放弹窗：左右双机位视频并排展示。 -->
<template>
  <Teleport to="body">
    <div v-if="show" class="data-management-modal" @click.self="$emit('close')">
      <div class="data-management-modal__card" style="max-width:720px">
        <div class="data-management-modal__head">
          <h3>同步对齐视频 — {{ subjectName }}</h3>
          <button type="button" class="link-button" @click="$emit('close')" aria-label="关闭">&#10007;</button>
        </div>
        <div class="data-management-video-grid">
          <div v-if="leftUrl" class="data-management-video-item">
            <p class="data-management-video-label">左机位</p>
            <video :src="leftUrl" controls preload="metadata" class="data-management-video-player" />
          </div>
          <div v-if="rightUrl" class="data-management-video-item">
            <p class="data-management-video-label">右机位</p>
            <video :src="rightUrl" controls preload="metadata" class="data-management-video-player" />
          </div>
          <p v-if="!leftUrl && !rightUrl" style="color:#94a3b8;text-align:center;grid-column:1/-1">
            该记录暂无同步视频（分析发生于同步视频存储功能上线前）
          </p>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
defineProps({
  show: { type: Boolean, default: false },
  leftUrl: { type: String, default: '' },
  rightUrl: { type: String, default: '' },
  subjectName: { type: String, default: '' },
});

defineEmits(['close']);
</script>
