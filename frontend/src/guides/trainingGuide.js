import {
  GUIDE_STAGES,
  getGuideStage,
  markGuideDismissed,
  setGuideStage,
  shouldAutoStartTraining,
} from './guideProgress.js';
import { startGuide } from './createGuideDriver.js';

export function getModePickerSteps({ onComplete } = {}) {
  return [
    {
      element: '[data-guide="mode-picker"]',
      popover: {
        title: '选择训练模式',
        description: '建议新手选择「练习评估」：可自由配置步伐，训练后可上传视频分析。自由练习侧重热身；能力测试会锁定标准步伐。',
        side: 'bottom',
        align: 'center',
        doneBtnText: '下一步',
        onNextClick: (_element, _step, { driver: activeDriver }) => {
          onComplete?.();
          activeDriver.destroy();
        },
      },
    },
  ];
}

export function getWorkspaceSteps({ onGoAnalysis, onComplete } = {}) {
  return [
    {
      element: '[data-guide="params"]',
      popover: {
        title: '训练参数',
        description: '选择预置步伐或自定义序列，并设置亮灯时长、步伐间隔与循环次数。',
        side: 'right',
        align: 'start',
      },
    },
    {
      element: '[data-guide="grid"]',
      popover: {
        title: '九宫格跑位',
        description: '中间状态栏会提示当前阶段。准备后起始格会高亮，开始后按序列依次亮灯。',
        side: 'left',
        align: 'center',
      },
    },
    {
      element: '[data-guide="controls"]',
      popover: {
        title: '训练控制',
        description: '先点「准备」生成本轮序列，再点「开始」：播放「开始拍摄」→ 蜂鸣 → 步伐亮灯。训练中可随时停止。',
        side: 'left',
        align: 'start',
      },
    },
    {
      element: '[data-guide="demo-preview"]',
      popover: {
        title: '步伐示范',
        description: '可先观看当前步伐的示范视频，再开始训练。',
        side: 'left',
        align: 'end',
      },
    },
    {
      element: '[data-guide="demo-preview"]',
      popover: {
        title: '下一步：视频分析',
        description: '训练完成后，可上传左右机位视频进行双目分析。',
        side: 'left',
        align: 'end',
        doneBtnText: '去上传分析',
        onNextClick: (_element, _step, { driver: activeDriver }) => {
          onComplete?.();
          setGuideStage(GUIDE_STAGES.analysis);
          activeDriver.destroy();
          onGoAnalysis?.();
        },
      },
    },
  ];
}

export function startModePickerGuide({ force = false } = {}) {
  if (!force && !shouldAutoStartTraining()) return null;
  if (getGuideStage() === GUIDE_STAGES.done) return null;

  const element = document.querySelector('[data-guide="mode-picker"]');
  if (!element) return null;

  let completedNaturally = false;

  return startGuide(getModePickerSteps({
    onComplete: () => {
      completedNaturally = true;
    },
  }), {
    onDestroyed: () => {
      if (completedNaturally) return;
      if (getGuideStage() === GUIDE_STAGES.analysis) return;
      markGuideDismissed('training');
    },
  });
}

export function startWorkspaceGuide({ force = false, onGoAnalysis } = {}) {
  if (!force && !shouldAutoStartTraining()) return null;
  if (getGuideStage() === GUIDE_STAGES.done) return null;

  const required = ['[data-guide="params"]', '[data-guide="grid"]', '[data-guide="controls"]'];
  if (!required.every((selector) => document.querySelector(selector))) return null;

  let completedNaturally = false;

  return startGuide(getWorkspaceSteps({
    onGoAnalysis,
    onComplete: () => {
      completedNaturally = true;
    },
  }), {
    onDestroyed: () => {
      if (completedNaturally) return;
      if (getGuideStage() === GUIDE_STAGES.analysis) return;
      markGuideDismissed('training');
    },
  });
}

export function replayTrainingGuide({ hasSelectedMode, onGoAnalysis }) {
  setGuideStage(GUIDE_STAGES.training);
  window.setTimeout(() => {
    if (hasSelectedMode) {
      startWorkspaceGuide({ force: true, onGoAnalysis });
    } else {
      startModePickerGuide({ force: true });
    }
  }, 200);
}
