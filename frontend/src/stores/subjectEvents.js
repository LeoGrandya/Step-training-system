/** 受试者变更通知 — 替代 window.CustomEvent('subject-changed')，所有通信方通过 import 可追踪。 */
import { ref } from 'vue';

export const subjectChangeCounter = ref(0);

export function notifySubjectChanged() {
  subjectChangeCounter.value++;
}
