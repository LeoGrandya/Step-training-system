/** 运行时必需。按路由自动/手动触发 driver.js 引导。 */
import { nextTick } from 'vue';
import { getTrainingMode, hasSession } from '../stores/storage.js';
import { GUIDE_STAGES, getGuideStage, setGuideStage, wasGuideDismissed } from './guideProgress.js';
import { startAuthGuide } from './authGuide.js';
import { startModePickerGuide, startWorkspaceGuide } from './trainingGuide.js';

let activeDriver = null;
let trainingHasMode = () => false;

export function setTrainingHasMode(checker) {
  trainingHasMode = checker || (() => false);
}

function destroyActiveGuide() {
  if (activeDriver?.isActive?.()) {
    activeDriver.destroy();
  }
  activeDriver = null;
}

function schedule(fn) {
  window.setTimeout(() => {
    nextTick(() => fn());
  }, 280);
}

export function scheduleGuideForRoute(to, { onGoAnalysis, trainingHasMode } = {}) {
  destroyActiveGuide();

  if (to.path === '/auth') {
    if (wasGuideDismissed('auth')) return;

    if (getGuideStage() === GUIDE_STAGES.none) {
      setGuideStage(GUIDE_STAGES.authIntro);
    }
    schedule(() => {
      activeDriver = startAuthGuide();
    });
    return;
  }

  if (to.path === '/training') {
    if (!hasSession()) return;

    const stage = getGuideStage();
    if (stage === GUIDE_STAGES.none || stage === GUIDE_STAGES.authIntro) {
      setGuideStage(GUIDE_STAGES.training);
    }

    if (getGuideStage() !== GUIDE_STAGES.training) return;
    if (wasGuideDismissed('training')) return;

    schedule(() => {
      if (trainingHasMode() || Boolean(getTrainingMode())) {
        activeDriver = startWorkspaceGuide({ onGoAnalysis });
      } else {
        activeDriver = startModePickerGuide();
      }
    });
  }
}

export function notifyTrainingModeSelected({ onGoAnalysis } = {}) {
  if (getGuideStage() !== GUIDE_STAGES.training) return;
  if (wasGuideDismissed('training')) return;

  destroyActiveGuide();
  schedule(() => {
    activeDriver = startWorkspaceGuide({ onGoAnalysis });
  });
}
