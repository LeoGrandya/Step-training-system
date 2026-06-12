/** 运行时必需。按步伐类型/等级/模式推荐训练间隔（仅 UI 提示）。 */
import { getPresetStepLabel } from './presetSteps.js';

/** 业余 · 练习评估 基准步伐间隔（ms） */
const STEP_INTERVAL_BASE_MS = {
  'single-step': 1500,
  'side-step': 1300,
  'back-step': 1600,
  'two-point': 1400,
  'three-point': 1500,
  'four-point': 1550,
  'push-side-pounce': 1700,
  'full-table': 1350,
};

const LEVEL_OFFSET_MS = {
  amateur: 0,
  'level-2': -120,
  'level-1': -240,
  '业余': 0,
  '二级': -120,
  '一级': -240,
};

const MODE_OFFSET_MS = {
  eval: 0,
  free: 180,
  test: -120,
  '练习评估': 0,
  '自由练习': 180,
  '能力测试': -120,
};

const LEVEL_LABELS = {
  amateur: '业余',
  'level-2': '二级',
  'level-1': '一级',
  '业余': '业余',
  '二级': '二级',
  '一级': '一级',
};

const MODE_LABELS = {
  eval: '练习评估',
  free: '自由练习',
  test: '能力测试',
};

const INTERVAL_MIN_MS = 400;
const INTERVAL_MAX_MS = 5000;

function clampIntervalMs(value) {
  const rounded = Math.round(value / 10) * 10;
  return Math.min(INTERVAL_MAX_MS, Math.max(INTERVAL_MIN_MS, rounded));
}

/**
 * @param {string} stepType
 * @param {{ level?: string, mode?: string }} [ctx]
 * @returns {number}
 */
export function getRecommendedStepIntervalMs(stepType, ctx = {}) {
  const base = STEP_INTERVAL_BASE_MS[stepType] ?? STEP_INTERVAL_BASE_MS['single-step'];
  const level = ctx.level || 'amateur';
  const mode = ctx.mode || 'eval';
  const raw = base
    + (LEVEL_OFFSET_MS[level] ?? 0)
    + (MODE_OFFSET_MS[mode] ?? 0);
  return clampIntervalMs(raw);
}

/**
 * @param {string} stepType
 * @param {{ level?: string, mode?: string }} [ctx]
 * @returns {string}
 */
export function formatRecommendedIntervalHint(stepType, ctx = {}) {
  const ms = getRecommendedStepIntervalMs(stepType, ctx);
  const stepLabel = getPresetStepLabel(stepType);
  const levelLabel = LEVEL_LABELS[ctx.level] || LEVEL_LABELS.amateur;
  const modeLabel = MODE_LABELS[ctx.mode] || MODE_LABELS.eval;
  return `推荐：${stepLabel} · ${ms} ms（${levelLabel} · ${modeLabel}）`;
}

export const RECOMMENDED_INTERVAL_STEP_BASE_MS = { ...STEP_INTERVAL_BASE_MS };
