/** 运行时必需。新手引导完成状态（localStorage）。 */
export const GUIDE_STORAGE_KEY = 'ai_sport_lab.guide_v1';
export const GUIDE_VERSION = 'v1';

export const GUIDE_STAGES = {
  none: 'none',
  authIntro: 'auth_intro',
  training: 'training',
  analysis: 'analysis',
  done: 'done',
};

const DEFAULT_DISMISSED = {
  auth: false,
  training: false,
  analysis: false,
};

function normalizeState(parsed) {
  return {
    version: GUIDE_VERSION,
    stage: parsed?.stage || GUIDE_STAGES.none,
    dismissed: { ...DEFAULT_DISMISSED, ...(parsed?.dismissed || {}) },
  };
}

function readState() {
  try {
    const raw = window.localStorage.getItem(GUIDE_STORAGE_KEY);
    if (!raw) {
      return { version: GUIDE_VERSION, stage: GUIDE_STAGES.none, dismissed: { ...DEFAULT_DISMISSED } };
    }
    const parsed = JSON.parse(raw);
    if (parsed.version !== GUIDE_VERSION) {
      return { version: GUIDE_VERSION, stage: GUIDE_STAGES.none, dismissed: { ...DEFAULT_DISMISSED } };
    }
    return normalizeState(parsed);
  } catch {
    return { version: GUIDE_VERSION, stage: GUIDE_STAGES.none, dismissed: { ...DEFAULT_DISMISSED } };
  }
}

function writeState(state) {
  window.localStorage.setItem(GUIDE_STORAGE_KEY, JSON.stringify({
    version: GUIDE_VERSION,
    stage: state.stage,
    dismissed: { ...DEFAULT_DISMISSED, ...(state.dismissed || {}) },
  }));
}

export function getGuideStage() {
  return readState().stage;
}

export function setGuideStage(stage) {
  const state = readState();
  writeState({ ...state, stage });
}

export function resetGuide() {
  writeState({ version: GUIDE_VERSION, stage: GUIDE_STAGES.none, dismissed: { ...DEFAULT_DISMISSED } });
}

export function markGuideDone() {
  const state = readState();
  writeState({ ...state, stage: GUIDE_STAGES.done });
}

export function markGuideDismissed(scope) {
  const state = readState();
  writeState({
    ...state,
    dismissed: { ...state.dismissed, [scope]: true },
  });
}

export function wasGuideDismissed(scope) {
  return Boolean(readState().dismissed?.[scope]);
}

export function shouldAutoStartAuth() {
  if (wasGuideDismissed('auth')) return false;
  const stage = getGuideStage();
  return stage === GUIDE_STAGES.none || stage === GUIDE_STAGES.authIntro;
}

export function shouldAutoStartTraining() {
  if (wasGuideDismissed('training')) return false;
  return getGuideStage() === GUIDE_STAGES.training;
}

export function shouldAutoStartAnalysis() {
  if (wasGuideDismissed('analysis')) return false;
  return getGuideStage() === GUIDE_STAGES.analysis;
}
