/** 运行时必需。预置步伐序列生成（含全台随机步）；训练页 TrainingGrid 调用。 */
export const PRESET_STEP_TYPES = [
  'single-step',
  'side-step',
  'back-step',
  'two-point',
  'three-point',
  'four-point',
  'push-side-pounce',
  'full-table',
];

export const DEFAULT_LOOP_COUNTS = {
  single: 10,
  combo: 5,
};

export const DEFAULT_FULL_TABLE_STEP_COUNT = 30;

const SINGLE_STEP_TYPES = new Set(['single-step', 'side-step', 'back-step']);

/** 已下架预置类型，仅用于历史记录展示 */
const LEGACY_STEP_LABELS = {
  'cross-step': '交叉步',
};

export const PRESET_STEP_OPTION_GROUPS = [
  {
    label: '单一步伐',
    options: [
      { value: 'single-step', label: '1. 跨步', shortLabel: '跨步' },
      { value: 'side-step', label: '2. 并步', shortLabel: '并步' },
      { value: 'back-step', label: '3. 撤步', shortLabel: '撤步' },
    ],
  },
  {
    label: '组合步伐',
    options: [
      { value: 'two-point', label: '1. 两点跑位', shortLabel: '两点跑位' },
      { value: 'three-point', label: '2. 三点跑位', shortLabel: '三点跑位' },
      { value: 'four-point', label: '3. 四点跑位', shortLabel: '四点跑位' },
      { value: 'push-side-pounce', label: '4. 推侧扑', shortLabel: '推侧扑' },
      { value: 'full-table', label: '5. 全台摆速', shortLabel: '全台摆速' },
    ],
  },
];

export const PRESET_STEP_OPTIONS = PRESET_STEP_OPTION_GROUPS.flatMap((group) =>
  group.options.map(({ value, shortLabel }) => ({ value, label: shortLabel })),
);

const PRESET_STEP_LABEL_BY_VALUE = new Map(
  PRESET_STEP_OPTION_GROUPS.flatMap((group) =>
    group.options.map((option) => [option.value, option.shortLabel]),
  ),
);

export function getPresetStepLabel(stepType) {
  return LEGACY_STEP_LABELS[stepType]
    || PRESET_STEP_LABEL_BY_VALUE.get(stepType)
    || '预置步伐';
}

export function getDefaultLoopCount(type) {
  return SINGLE_STEP_TYPES.has(type) ? DEFAULT_LOOP_COUNTS.single : DEFAULT_LOOP_COUNTS.combo;
}

function isLeftHand(hand) {
  return hand === 'left' || hand === '左手';
}

function isRightHand(hand) {
  return !isLeftHand(hand);
}

export function getPresetStartCell(_type, _hand = 'right') {
  return 5;
}

const PRESET_STEP_LOGIC_HINTS = {
  'single-step': '从 1,2,3,4,6 随机选目标，每步归中',
  'side-step': '从除中心外的 8 格随机选目标，每步归中',
  'back-step': '随机退至 7,8,9，每步归中',
  'two-point': '4 ↔ 6 交替跑位',
  'three-point': '6 → 5 → 4 → 5 循环',
  'four-point': '5 → 4 → 5 → 6 循环',
  'push-side-pounce': '5 → 4 → 6 循环',
  'full-table': '4, 5, 6 随机，同格不三连',
};

const PRESET_HAND_REQUIREMENTS = {
  'side-step': '上前一步跨步 + 后撤步并步',
  'two-point': '两个正手',
  'three-point': '三个正手',
  'four-point': '一反一侧身一反手一正手',
  'push-side-pounce': '一反一侧一正手扑一反手还原',
};

export function getPresetStepLogicHint(type) {
  return PRESET_STEP_LOGIC_HINTS[type] || '';
}

export function getPresetHandRequirement(type, hand = 'right') {
  if (type === 'back-step') {
    return isLeftHand(hand)
      ? '正手，左脚后撤步（左手为例）'
      : '正手，右脚后撤步（右手为例）';
  }
  return PRESET_HAND_REQUIREMENTS[type] || '';
}

export function generatePresetSteps(type, hand = 'right', repeat, random = Math.random) {
  const n = normalizeRepeat(repeat, getDefaultLoopCount(type));
  const rightHand = isRightHand(hand);

  switch (type) {
    case 'single-step':
      return generateRandomActiveWithCenterSteps([1, 2, 3, 4, 6], n, random);
    case 'side-step':
      return generateRandomActiveWithCenterSteps([1, 2, 3, 4, 6, 7, 8, 9], n, random);
    case 'back-step':
      return repeatPattern(n, () => [
        active(randomItem([7, 8, 9], random)),
        active(5),
      ]);
    case 'two-point':
      return repeatPattern(n, rightHand
        ? [active(4), active(6)]
        : [active(6), active(4)]);
    case 'three-point':
      return repeatPattern(n, rightHand
        ? [6, 5, 4, 5, 6].map(active)
        : [4, 5, 6, 5, 4].map(active));
    case 'four-point':
      return repeatPattern(n, rightHand
        ? [5, 4, 5, 6, 5].map(active)
        : [5, 6, 5, 4, 5].map(active));
    case 'push-side-pounce':
      return repeatPattern(n, rightHand
        ? [active(5), active(4), active(6)]
        : [active(5), active(6), active(4)]);
    case 'full-table':
      return generateFullTableSteps(n, random);
    default:
      return generatePresetSteps('single-step', hand, repeat, random);
  }
}

export function formatTrainingStep(step) {
  if (step && typeof step === 'object' && step.waitMs) return `W${step.waitMs}`;
  if (!step || typeof step !== 'object') return String(step || '');
  return String(step.cell);
}

function normalizeRepeat(value, fallback) {
  const n = Number.parseInt(value, 10);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

function active(cell) {
  return { cell, type: 'active' };
}

/** 全台摆速：首步 4/6 二选一，之后从 [4,5,6] 随机，同格最多连续 2 次 */
export function generateFullTableSteps(totalSteps, random = Math.random) {
  const n = normalizeRepeat(totalSteps, DEFAULT_FULL_TABLE_STEP_COUNT);
  const steps = [];
  steps.push(active(random() < 0.5 ? 4 : 6));
  const pool = [4, 5, 6];
  while (steps.length < n) {
    let banned = [];
    const len = steps.length;
    if (len >= 2 && steps[len - 1].cell === steps[len - 2].cell) {
      banned = [steps[len - 1].cell];
    }
    const allowed = pool.filter((cell) => !banned.includes(cell));
    steps.push(active(randomItem(allowed, random)));
  }
  return steps;
}

function repeatPattern(count, pattern) {
  const steps = [];
  for (let i = 0; i < count; i += 1) {
    const chunk = typeof pattern === 'function' ? pattern(i) : pattern;
    const cells = chunk.map((step) => ({ ...step }));
    if (steps.length > 0 && cells.length > 0 && cells[0].cell === steps[steps.length - 1].cell) {
      steps.push(...cells.slice(1));
    } else {
      steps.push(...cells);
    }
  }
  return steps;
}

function generateRandomActiveWithCenterSteps(targets, repeatEach, random) {
  const pool = [];
  for (let i = 0; i < repeatEach; i += 1) pool.push(...targets);

  const steps = [];
  while (pool.length) {
    const index = Math.min(pool.length - 1, Math.floor(random() * pool.length));
    const [target] = pool.splice(index, 1);
    steps.push(active(target), active(5));
  }
  return steps;
}

function randomItem(items, random) {
  return items[Math.min(items.length - 1, Math.floor(random() * items.length))];
}
