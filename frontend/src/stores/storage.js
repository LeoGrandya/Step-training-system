/** 运行时必需。localStorage/session 键与读写：登录态、档案、训练参数、硬件反馈开关。 */
import { DEFAULT_FULL_TABLE_STEP_COUNT } from '../services/presetSteps.js';

export const STORAGE_KEYS = {
  session: 'ai_sport_lab.session',
  profile: 'ai_sport_lab.profile',
  trainingMode: 'ai_sport_lab.training_mode',
  currentJobId: 'ai_sport_lab.current_job_id',
  currentUserId: 'pp-current-user-id',
  currentAccountId: 'ai_sport_lab.current_account_id',
  currentSubjectId: 'ai_sport_lab.current_subject_id',
  hardwareFeedback: 'ai_sport_lab.hardware_feedback',
  trainingPrefs: 'ai_sport_lab.training_prefs',
  pose3dProfile: 'pp-footwork-base-profile',
  pose3dTrainingMode: 'pp-footwork-training-mode',
  pose3dCurrentMode: 'pp-flow-current-mode',
  pose3dFunnelState: 'pp-footwork-funnel-state',
};

const POSE3D_STORAGE_VERSION = 1;
const ALLOWED_TRAINING_MODES = ['练习评估', '自由练习', '能力测试'];

export function createDefaultProfile() {
  return {
    name: '',
    age: 25,
    heightCm: 170,
    weightKg: 65,
    hand: 'right',
    years: 0,
    level: 'amateur',
  };
}

function readJson(key, fallback) {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function writeJson(key, value) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // localStorage may be full or blocked
  }
}

function nowIso() {
  return new Date().toISOString();
}

function writeSessionValue(key, value) {
  try {
    window.sessionStorage.setItem(key, value);
  } catch {
    // Session storage can be blocked; the localStorage state is still enough for the prototype.
  }
}

export function hasSession() {
  if (getCurrentAccountId()) return true;
  const userId = getCurrentUserId();
  if (userId) return true;
  const session = readJson(STORAGE_KEYS.session, null);
  if (session?.loggedIn) {
    if (session?.accountId) {
      setCurrentAccountId(String(session.accountId));
      return true;
    }
    if (session?.userId) {
      setCurrentUserId(String(session.userId));
      return true;
    }
  }
  return false;
}

export function loginAccountSession(account) {
  writeJson(STORAGE_KEYS.session, {
    loggedIn: true,
    accountId: account.id || '',
    loginAt: nowIso(),
  });
  setCurrentAccountId(account.id || '');
}

export function logoutAccountSession() {
  try { window.localStorage.removeItem(STORAGE_KEYS.session); } catch {}
  setCurrentAccountId('');
  setCurrentUserId('');
  setCurrentSubjectId('');
}

export function getCurrentUserId() {
  try {
    return window.sessionStorage.getItem(STORAGE_KEYS.currentUserId) || '';
  } catch {
    return '';
  }
}

export function setCurrentUserId(userId) {
  try {
    if (userId) {
      window.sessionStorage.setItem(STORAGE_KEYS.currentUserId, userId);
    } else {
      window.sessionStorage.removeItem(STORAGE_KEYS.currentUserId);
    }
  } catch {
    // sessionStorage may be blocked in embedded contexts.
  }
}

export function getCurrentAccountId() {
  try {
    return window.localStorage.getItem(STORAGE_KEYS.currentAccountId) || '';
  } catch {
    return '';
  }
}

export function setCurrentAccountId(accountId) {
  try {
    if (accountId) {
      window.localStorage.setItem(STORAGE_KEYS.currentAccountId, String(accountId).trim());
    } else {
      window.localStorage.removeItem(STORAGE_KEYS.currentAccountId);
    }
  } catch {
    // localStorage may be blocked in embedded contexts.
  }
}

export function getCurrentSubjectId() {
  try {
    return window.localStorage.getItem(STORAGE_KEYS.currentSubjectId) || '';
  } catch {
    return '';
  }
}

export function setCurrentSubjectId(subjectId) {
  try {
    if (subjectId) {
      window.localStorage.setItem(STORAGE_KEYS.currentSubjectId, subjectId);
    } else {
      window.localStorage.removeItem(STORAGE_KEYS.currentSubjectId);
    }
  } catch {
    // localStorage may be blocked.
  }
}

export function getHardwareFeedbackEnabled() {
  const raw = window.localStorage.getItem(STORAGE_KEYS.hardwareFeedback);
  return raw !== '0';
}

export function setHardwareFeedbackEnabled(enabled) {
  try { window.localStorage.setItem(STORAGE_KEYS.hardwareFeedback, enabled ? '1' : '0'); } catch {}
}

export function loginSession(name, userId = '') {
  writeJson(STORAGE_KEYS.session, {
    loggedIn: true,
    name: String(name || '训练用户').trim() || '训练用户',
    userId: userId || getCurrentUserId(),
    loginAt: nowIso(),
  });
  if (userId) setCurrentUserId(userId);
}

export function logoutSession() {
  try { window.localStorage.removeItem(STORAGE_KEYS.session); } catch {}
  setCurrentUserId('');
}

export function readPose3dProfile() {
  const payload = readJson(STORAGE_KEYS.pose3dProfile, null);
  if (!payload || payload.version !== POSE3D_STORAGE_VERSION || !payload.data) return {};
  return payload.data;
}

export function savePose3dProfile(profile) {
  const normalized = { ...createDefaultProfile(), ...profile };
  writeJson(STORAGE_KEYS.pose3dProfile, {
    version: POSE3D_STORAGE_VERSION,
    savedAt: nowIso(),
    data: normalized,
  });
  const hasMode = Boolean(readPose3dTrainingMode());
  try { window.localStorage.setItem(STORAGE_KEYS.pose3dFunnelState, hasMode ? 'done' : 'need_mode'); } catch {}
  return normalized;
}

export function getProfile() {
  return { ...createDefaultProfile(), ...readJson(STORAGE_KEYS.profile, {}), ...readPose3dProfile() };
}

export function saveProfile(profile) {
  const normalized = { ...createDefaultProfile(), ...profile };
  writeJson(STORAGE_KEYS.profile, normalized);
  savePose3dProfile(normalized);
  return normalized;
}

export function readPose3dTrainingMode() {
  const payload = readJson(STORAGE_KEYS.pose3dTrainingMode, null);
  if (!payload || payload.version !== POSE3D_STORAGE_VERSION) return '';
  return ALLOWED_TRAINING_MODES.includes(payload.mode) ? payload.mode : '';
}

export function getTrainingMode() {
  return readPose3dTrainingMode() || window.localStorage.getItem(STORAGE_KEYS.trainingMode) || '';
}

export function saveTrainingMode(mode, extra = {}) {
  if (!ALLOWED_TRAINING_MODES.includes(mode)) return '';
  try { window.localStorage.setItem(STORAGE_KEYS.trainingMode, mode); } catch {}
  writeJson(STORAGE_KEYS.pose3dTrainingMode, {
    version: POSE3D_STORAGE_VERSION,
    savedAt: nowIso(),
    mode,
    extra: { ...extra },
  });
  writeSessionValue(STORAGE_KEYS.pose3dCurrentMode, mode);
  try { window.localStorage.setItem(STORAGE_KEYS.pose3dFunnelState, 'done'); } catch {}
  return mode;
}

export function saveCurrentJobId(jobId) {
  try { window.localStorage.setItem(STORAGE_KEYS.currentJobId, jobId); } catch {}
}

export function getCurrentJobId() {
  return window.localStorage.getItem(STORAGE_KEYS.currentJobId) || '';
}

export function createDefaultTrainingPrefs() {
  return {
    stepSource: 'preset',
    stepType: 'single-step',
    lightDuration: 800,
    stepInterval: 1200,
    loopCount: 10,
    fullTableStepCount: DEFAULT_FULL_TABLE_STEP_COUNT,
    hardwareFeedback: true,
    customName: '',
    customStartCell: 5,
    customSequence: '5,4,6,5',
    customActionRequirements: '',
    customRhythm: null,
    selectedCustomId: '',
  };
}

function clampInt(value, min, max, fallback) {
  const n = Number.parseInt(value, 10);
  if (!Number.isFinite(n)) return fallback;
  return Math.min(max, Math.max(min, n));
}

export function loadTrainingPrefs() {
  const defaults = createDefaultTrainingPrefs();
  const raw = readJson(STORAGE_KEYS.trainingPrefs, null);
  if (!raw || typeof raw !== 'object') return defaults;
  return {
    stepSource: raw.stepSource === 'custom' ? 'custom' : 'preset',
    stepType: typeof raw.stepType === 'string' ? raw.stepType : defaults.stepType,
    lightDuration: clampInt(raw.lightDuration, 200, 3000, defaults.lightDuration),
    stepInterval: clampInt(raw.stepInterval, 400, 5000, defaults.stepInterval),
    loopCount: clampInt(raw.loopCount, 1, 99, defaults.loopCount),
    fullTableStepCount: clampInt(raw.fullTableStepCount, 5, 99, defaults.fullTableStepCount),
    hardwareFeedback: raw.hardwareFeedback !== false,
    customName: typeof raw.customName === 'string' ? raw.customName : '',
    customStartCell: clampInt(raw.customStartCell, 1, 9, defaults.customStartCell),
    customSequence: typeof raw.customSequence === 'string' ? raw.customSequence : defaults.customSequence,
    customActionRequirements: typeof raw.customActionRequirements === 'string' ? raw.customActionRequirements : '',
    customRhythm: raw.customRhythm && typeof raw.customRhythm === 'object' ? raw.customRhythm : null,
    selectedCustomId: typeof raw.selectedCustomId === 'string' ? raw.selectedCustomId : '',
  };
}

export function saveTrainingPrefs(prefs) {
  writeJson(STORAGE_KEYS.trainingPrefs, prefs);
}
