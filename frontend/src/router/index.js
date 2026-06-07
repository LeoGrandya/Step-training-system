/** 运行时必需。Hash 路由表、登录守卫、上传页离开确认、新手引导调度。 */
import { createRouter, createWebHashHistory } from 'vue-router';
import AccountView from '../views/AccountView.vue';
import AuthView from '../views/AuthView.vue';
import AnalysisView from '../views/AnalysisView.vue';
import DataManagementView from '../views/DataManagementView.vue';
import LegacyHtmlView from '../views/LegacyHtmlView.vue';
import ReportHistoryView from '../views/ReportHistoryView.vue';
import TrainingView from '../views/TrainingView.vue';
import { scheduleGuideForRoute } from '../guides/guideScheduler.js';
import { hasSession } from '../stores/storage.js';
import { authGuardRedirect } from './guard.js';

const routes = [
  { path: '/', redirect: '/home' },
  { path: '/home', component: LegacyHtmlView, meta: { fullFrame: true, legacyFile: 'home.html' } },
  { path: '/product', component: LegacyHtmlView, meta: { fullFrame: true, legacyFile: 'product.html' } },
  { path: '/training', component: TrainingView, meta: { requiresAuth: true } },
  { path: '/analysis', component: AnalysisView, meta: { requiresAuth: true } },
  { path: '/data-management', component: DataManagementView, meta: { requiresAuth: true } },
  { path: '/report-history', component: ReportHistoryView, meta: { requiresAuth: true } },
  { path: '/account', component: AccountView, meta: { requiresAuth: true } },
  { path: '/loading', component: LegacyHtmlView, meta: { fullFrame: true, legacyFile: 'loading.html', requiresAuth: true } },
  { path: '/report/:jobId?', component: LegacyHtmlView, meta: { fullFrame: true, legacyFile: 'report.html', requiresAuth: true } },
  { path: '/settings', component: LegacyHtmlView, meta: { fullFrame: true, legacyFile: 'settings.html', requiresAuth: true } },
  { path: '/team', component: LegacyHtmlView, meta: { fullFrame: true, legacyFile: 'team.html' } },
  { path: '/auth', component: AuthView },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

router.beforeEach(async (to, from) => {
  if (from.path === '/analysis' && to.path !== '/analysis') {
    try {
      if (window.sessionStorage.getItem('ai_sport_lab.analysis_guard') === 'submitting') {
        const shouldLeave = window.confirm('视频正在上传，离开页面可能中断提交，确定要离开吗？');
        if (!shouldLeave) return false;
      }
    } catch (error) {
      // ignore sessionStorage errors
    }
  }

  if (!to.meta.requiresAuth) return true;

  if (!hasSession()) {
    authGuardRedirect.value = to.fullPath;
    return false;
  }

  return true;
});

router.afterEach((to) => {
  scheduleGuideForRoute(to, {
    onGoAnalysis: () => {
      router.push('/analysis');
    },
  });
});

export default router;
