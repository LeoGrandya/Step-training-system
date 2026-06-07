/** 路由守卫共享状态：未登录时弹出模态框的触发信号，以及登录态。 */
import { ref } from 'vue';
import { hasSession } from '../stores/storage.js';

export const authGuardRedirect = ref('');

export const isLoggedIn = ref(hasSession());

export function refreshLoginState() {
  isLoggedIn.value = hasSession();
}
