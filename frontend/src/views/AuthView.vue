<!-- 运行时必需。登录/注册页。 -->
<template>
  <section class="auth-page">
    <div class="auth-card">
      <div class="auth-copy" data-guide="auth-intro">
        <p class="eyebrow">AI-Sport Lab</p>
        <h1>登录后进入训练闭环</h1>
      </div>
      <form class="auth-form" @submit.prevent="submit">
        <h2>{{ mode === 'login' ? '账号登录' : '账号注册' }}</h2>
        <input v-model.trim="name" type="text" placeholder="用户名" required />
        <input v-if="mode === 'register'" v-model.trim="email" type="email" placeholder="邮箱（可选）" />
        <input v-model="password" type="password" placeholder="密码（本地占位，暂不校验）" required />
        <button type="submit" :disabled="submitting" data-guide="auth-submit">
          {{ submitting ? '处理中...' : (mode === 'login' ? '进入训练' : '完成注册') }}
        </button>
        <button type="button" class="link-button" @click="toggleMode">
          {{ mode === 'login' ? '还没有账号？立即注册' : '已有账号？立即登录' }}
        </button>
        <p v-if="message" class="hint">{{ message }}</p>
        <p class="hint">账号档案保存在 pose3d 后端 SQLite，登录后可在训练页同步基础资料。</p>
      </form>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { GUIDE_STAGES, setGuideStage } from '../guides/guideProgress.js';
import {
  getProfile,
  loginSession,
  savePose3dProfile,
  saveProfile,
  setCurrentUserId,
} from '../stores/storage.js';
import { registerOrLoginByName, syncUserProfile } from '../services/users.js';

const route = useRoute();
const router = useRouter();
const mode = ref('login');
const name = ref('');
const email = ref('');
const password = ref('');
const submitting = ref(false);
const message = ref('');

function toggleMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login';
  message.value = '';
}

async function submit() {
  const displayName = name.value || '训练用户';
  submitting.value = true;
  message.value = '';
  try {
    const profile = getProfile();
    const nextProfile = profile.name ? profile : { ...profile, name: displayName };
    const user = await registerOrLoginByName(displayName, nextProfile);
    setCurrentUserId(user.id);
    loginSession(user.name || displayName, user.id);
    const syncedProfile = {
      ...nextProfile,
      name: user.name || displayName,
      age: user.age ?? nextProfile.age,
      heightCm: user.heightCm ?? nextProfile.heightCm,
      weightKg: user.weightKg ?? nextProfile.weightKg,
      hand: user.hand || nextProfile.hand,
      years: user.years ?? nextProfile.years,
      level: user.level || nextProfile.level,
    };
    saveProfile(syncedProfile);
    savePose3dProfile(syncedProfile);
    if (mode.value === 'register') {
      await syncUserProfile(user.id, syncedProfile);
    }
    setGuideStage(GUIDE_STAGES.training);
    router.push(String(route.query.redirect || '/training?selectMode=1'));
  } catch (error) {
    message.value = error.message || '登录失败，请稍后重试。';
  } finally {
    submitting.value = false;
  }
}
</script>
