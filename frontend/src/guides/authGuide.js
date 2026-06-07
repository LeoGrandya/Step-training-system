import { GUIDE_STAGES, getGuideStage, markGuideDismissed, setGuideStage, shouldAutoStartAuth } from './guideProgress.js';
import { startGuide } from './createGuideDriver.js';

export function startAuthGuide({ force = false } = {}) {
  if (!force && !shouldAutoStartAuth()) return null;
  if (getGuideStage() === GUIDE_STAGES.done) return null;

  let completedNaturally = false;

  const steps = [
    {
      element: '[data-guide="auth-intro"]',
      popover: {
        title: '欢迎使用 AI-Sport Lab',
        description: '这里可以登录或注册。账号仅保存在本机浏览器，用于进入训练与分析流程。',
        side: 'bottom',
        align: 'start',
      },
    },
    {
      element: '[data-guide="auth-submit"]',
      popover: {
        title: '进入训练',
        description: '填写用户名和密码后点击此处登录。登录成功后将进入训练模式选择。',
        side: 'top',
        align: 'center',
        doneBtnText: '知道了',
        onNextClick: (_element, _step, { driver: activeDriver }) => {
          completedNaturally = true;
          setGuideStage(GUIDE_STAGES.training);
          activeDriver.destroy();
        },
      },
    },
  ];

  return startGuide(steps, {
    onDestroyed: () => {
      if (completedNaturally) return;
      markGuideDismissed('auth');
      const stage = getGuideStage();
      if (stage === GUIDE_STAGES.none || stage === GUIDE_STAGES.authIntro) {
        setGuideStage(GUIDE_STAGES.training);
      }
    },
  });
}
