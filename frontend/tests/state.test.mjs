import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  createDefaultProfile,
  createDefaultTrainingPrefs,
  STORAGE_KEYS,
} from '../src/stores/storage.js';
import { NAV_ITEMS, TRAINING_DROPDOWN } from '../src/router/nav.js';
import {
  DEFAULT_FULL_TABLE_STEP_COUNT,
  DEFAULT_LOOP_COUNTS,
  PRESET_STEP_OPTION_GROUPS,
  PRESET_STEP_OPTIONS,
  PRESET_STEP_TYPES,
  formatTrainingStep,
  generateFullTableSteps,
  generatePresetSteps,
  getPresetHandRequirement,
  getPresetStartCell,
  getPresetStepLogicHint,
  getPresetStepLabel,
} from '../src/services/presetSteps.js';
import {
  formatRecommendedIntervalHint,
  getRecommendedStepIntervalMs,
} from '../src/services/recommendedStepIntervals.js';
import { getFootworkDemoPosterUrl, getFootworkDemoVideoUrl } from '../src/services/footworkDemoVideos.js';

const testDir = dirname(fileURLToPath(import.meta.url));
const appRoot = resolve(testDir, '..');
const projectRoot = resolve(appRoot, '../site');

test('default profile has the fields required by the training page', () => {
  const profile = createDefaultProfile();

  assert.equal(profile.name, '');
  assert.equal(profile.hand, 'right');
  assert.equal(profile.level, 'amateur');
  assert.equal(profile.years, 0);
});

test('Vue nav keeps the same official order', () => {
  assert.deepEqual(
    NAV_ITEMS.map((item) => item.label),
    ['首页', '产品介绍', '团队介绍'],
  );
  assert.deepEqual(
    TRAINING_DROPDOWN.map((item) => item.label),
    ['训练模式', '视频上传分析', '数据管理', '历史报告'],
  );
});

test('data management page exposes the MySQL v1 resource workbench', () => {
  const router = readFileSync(resolve(appRoot, 'src/router/index.js'), 'utf8');
  const navItems = readFileSync(resolve(appRoot, 'src/router/nav.js'), 'utf8');
  const viewPath = resolve(appRoot, 'src/views/DataManagementView.vue');
  const servicePath = resolve(appRoot, 'src/services/adminData.js');

  assert.equal(existsSync(viewPath), true);
  assert.equal(existsSync(servicePath), true);
  assert.match(router, /import DataManagementView/);
  assert.match(router, /path:\s*'\/data-management',\s*component:\s*DataManagementView/);
  assert.match(navItems, /TRAINING_DROPDOWN/);
  assert.match(navItems, /数据管理/);

  const view = readFileSync(viewPath, 'utf8');
  const service = readFileSync(servicePath, 'utf8');
  for (const key of [
    'subjects',
    'footwork-types',
    'routes',
    'training-configs',
    'training-videos',
    'kinematics-datasets',
    'evaluations',
    'accounts',
    'roles',
    'permissions',
  ]) {
    assert.match(view + service, new RegExp(key));
  }

  assert.match(view, /loadResources/);
  assert.match(view, /saveResource/);
  assert.match(view, /deleteResource/);
  assert.match(view, /keyword/);
  assert.match(view, /limit/);
  assert.match(view, /offset/);
});

test('only non-business legacy html pages keep iframe sources', () => {
  const router = readFileSync(resolve(appRoot, 'src/router/index.js'), 'utf8');
  const view = readFileSync(resolve(appRoot, 'src/views/LegacyHtmlView.vue'), 'utf8');

  for (const route of ['home', 'product', 'training', 'analysis', 'report-history', 'loading', 'report', 'settings', 'team', 'auth']) {
    assert.match(router, new RegExp(`path:\\s*'/${route}`));
  }

  assert.match(router, /import AuthView/);
  assert.match(router, /import AnalysisView/);
  assert.match(router, /import ReportHistoryView/);
  assert.match(router, /import TrainingView/);
  assert.match(router, /path:\s*'\/auth',\s*component:\s*AuthView/);
  assert.match(router, /path:\s*'\/training',\s*component:\s*TrainingView/);
  assert.match(router, /path:\s*'\/analysis',\s*component:\s*AnalysisView/);
  assert.match(router, /path:\s*'\/report-history',\s*component:\s*ReportHistoryView/);
  assert.doesNotMatch(router, /legacyFile:\s*'upload\.html'/);
  assert.doesNotMatch(router, /legacyFile:\s*'report-history\.html'/);
  assert.doesNotMatch(router, /legacyFile:\s*'auth\.html'/);
  assert.doesNotMatch(router, /legacyFile:\s*'training\.html'/);

  for (const file of ['home.html', 'product.html', 'loading.html', 'settings.html', 'team.html']) {
    assert.match(view, new RegExp(file.replace('.', '\\.')));
  }
  assert.doesNotMatch(view, /upload\.html/);
  assert.doesNotMatch(view, /report-history\.html/);
});

test('storage keys are centralized under one namespace', () => {
  assert.equal(STORAGE_KEYS.session, 'ai_sport_lab.session');
  assert.equal(STORAGE_KEYS.profile, 'ai_sport_lab.profile');
  assert.equal(STORAGE_KEYS.currentJobId, 'ai_sport_lab.current_job_id');
  assert.equal(STORAGE_KEYS.pose3dProfile, 'pp-footwork-base-profile');
  assert.equal(STORAGE_KEYS.pose3dTrainingMode, 'pp-footwork-training-mode');
  assert.equal(STORAGE_KEYS.pose3dFunnelState, 'pp-footwork-funnel-state');
  assert.equal(STORAGE_KEYS.trainingPrefs, 'ai_sport_lab.training_prefs');

  const storage = readFileSync(resolve(appRoot, 'src/stores/storage.js'), 'utf8');
  assert.match(storage, /loadTrainingPrefs/);
  assert.match(storage, /saveTrainingPrefs/);
  assert.match(storage, /readJson\(STORAGE_KEYS\.profile[\s\S]*readPose3dProfile\(\)/);
  assert.match(storage, /return readPose3dTrainingMode\(\) \|\| window\.localStorage\.getItem/);
});

test('business Vue pages expose pose3d-compatible flows', () => {
  const auth = readFileSync(resolve(appRoot, 'src/views/AuthView.vue'), 'utf8');
  const training = readFileSync(resolve(appRoot, 'src/views/TrainingView.vue'), 'utf8');
  const grid = readFileSync(resolve(appRoot, 'src/components/TrainingGrid.vue'), 'utf8');
  assert.match(auth, /savePose3dProfile/);
  assert.match(training, /eval/);
  assert.match(training, /free/);
  assert.match(training, /test/);
  assert.match(training, /baseLevel/);
  assert.doesNotMatch(grid, /startHardware/);
  assert.match(grid, /customSequence/);
});

test('home CTA and auth flow enter the current training mode selection route', () => {
  const home = readFileSync(resolve(projectRoot, 'home.html'), 'utf8');
  const auth = readFileSync(resolve(appRoot, 'src/views/AuthView.vue'), 'utf8');
  const training = readFileSync(resolve(appRoot, 'src/views/TrainingView.vue'), 'utf8');

  assert.match(home, /#\/training\?selectMode=1/);
  assert.doesNotMatch(home, /window\.location\.href='training\.html'/);
  assert.doesNotMatch(auth, /兼容 pose3d/);
  assert.match(auth, /redirect \|\| '\/training\?selectMode=1'/);
  assert.match(training, /route\.query\.selectMode/);
});

test('home and product marketing CTAs use current routes', () => {
  const home = readFileSync(resolve(projectRoot, 'home.html'), 'utf8');
  const product = readFileSync(resolve(projectRoot, 'product.html'), 'utf8');
  const auth = readFileSync(resolve(appRoot, 'src/views/AuthView.vue'), 'utf8');

  assert.match(home, /#\/product/);
  assert.doesNotMatch(home, /href="#"/);
  assert.doesNotMatch(product, /auth\.html/);
  assert.match(product, /#\/training\?selectMode=1/);
  assert.doesNotMatch(product, /<a[^>]*href="#training-modes"[^>]*>可下滑浏览产品功能/);
  assert.match(product, /可下滑浏览产品功能/);
  assert.doesNotMatch(product, />浏览功能</);
  assert.match(product, /id="training-modes"/);
  assert.doesNotMatch(product, /href="#features"/);
  assert.doesNotMatch(auth, /onMounted\([\s\S]*hasSession/);
});

test('training page uses the compact header and centered mode picker layout', () => {
  const training = readFileSync(resolve(appRoot, 'src/views/TrainingView.vue'), 'utf8');
  const styles = readFileSync(resolve(appRoot, 'src/styles/main.css'), 'utf8');

  assert.match(training, /training-header/);
  assert.match(training, /profile-summary/);
  assert.match(training, /请选择所需的训练模式/);
  assert.match(training, /mode-picker/);
  assert.match(training, /training-actions/);
  assert.doesNotMatch(training, /按 pose3d 的资料确认/);
  assert.doesNotMatch(training, /profile-strip/);

  assert.match(styles, /\.training-header/);
  assert.match(styles, /\.mode-picker/);
  assert.match(styles, /\.profile-summary/);
});

test('analysis page uses Vue upload flow with inline progress monitor', () => {
  const analysis = readFileSync(resolve(appRoot, 'src/views/AnalysisView.vue'), 'utf8');
  const upload = readFileSync(resolve(appRoot, 'src/composables/useAnalysisUpload.js'), 'utf8');
  const job = readFileSync(resolve(appRoot, 'src/composables/useAnalysisJob.js'), 'utf8');
  const uploadZone = readFileSync(resolve(appRoot, 'src/components/AnalysisUploadZone.vue'), 'utf8');
  const paramsPanel = readFileSync(resolve(appRoot, 'src/components/AnalysisParamsPanel.vue'), 'utf8');
  const progressPanel = readFileSync(resolve(appRoot, 'src/components/AnalysisProgressPanel.vue'), 'utf8');
  const styles = readFileSync(resolve(appRoot, 'src/styles/main.css'), 'utf8');
  const router = readFileSync(resolve(appRoot, 'src/router/index.js'), 'utf8');

  assert.match(router, /path:\s*'\/analysis',\s*component:\s*AnalysisView/);
  assert.doesNotMatch(router, /legacyFile:\s*'upload\.html'/);

  assert.match(analysis, /analysis-header/);
  assert.match(analysis, /双目视频分析/);
  assert.match(analysis, /RouterLink to="\/report-history"/);
  assert.match(analysis, /AnalysisUploadZone/);
  assert.match(analysis, /camera="left"/);
  assert.match(analysis, /camera="right"/);
  assert.match(analysis, /accept="\.json,application\/json"/);
  assert.match(analysis, /AnalysisProgressPanel/);
  assert.match(analysis, /AnalysisParamsPanel/);
  assert.match(analysis, /AnalysisRecentList/);
  assert.match(analysis, /beforeunload/);
  assert.match(analysis, /setSubmittingGuard/);
  assert.match(analysis, /clearAnalysisGuard/);
  assert.match(analysis, /analysisGeneration/);
  assert.match(analysis, /restoreActiveJobIfAny/);
  assert.match(analysis, /saveCurrentJobId/);
  assert.match(analysis, /router\.push\('\/report\/' \+ encodeURIComponent\(jid\)\)/);

  assert.match(uploadZone, /camera === 'left'/);
  assert.match(uploadZone, /type\.startsWith\('video\/'\)/);
  assert.match(upload, /createAnalysisJob/);
  assert.match(upload, /new FormData/);
  assert.match(upload, /left_video/);
  assert.match(upload, /right_video/);
  assert.match(upload, /profile_json/);
  assert.match(upload, /training_mode/);
  assert.match(upload, /analysis_profile/);
  assert.match(upload, /stereo_params_matlab_json/);
  assert.match(upload, /AbortController/);
  assert.match(upload, /cancelSubmit/);

  assert.match(job, /ACTIVE_KEY = 'ai_sport_lab\.active_analysis'/);
  assert.match(job, /GUARD_KEY = 'ai_sport_lab\.analysis_guard'/);
  assert.match(job, /normalizeProgress/);
  assert.match(job, /estimated_duration_s/);
  assert.match(job, /writeActiveJob/);
  assert.match(job, /restoreActiveJobIfAny/);
  assert.match(job, /\/cancel/);
  assert.match(job, /cancelJob/);

  assert.match(paramsPanel, /analysisProfile/);
  assert.match(paramsPanel, /trainingMode/);
  assert.match(progressPanel, /analysis-progress/);
  assert.match(progressPanel, /progress \+ '%'/);
  assert.match(progressPanel, /取消分析/);

  assert.match(router, /analysis_guard.*submitting/);
  assert.match(router, /视频正在上传，离开页面可能中断提交/);

  assert.match(styles, /\.analysis-header/);
  assert.match(styles, /\.analysis-upload-grid/);
  assert.match(styles, /\.analysis-calibration-field/);
  assert.match(styles, /\.analysis-submit-row/);
  assert.match(styles, /\.analysis-progress/);
  assert.match(styles, /\.analysis-header__history-link/);
});

test('Vue business nav matches the legacy home nav structure and styling hooks', () => {
  const nav = readFileSync(resolve(appRoot, 'src/components/SiteNav.vue'), 'utf8');
  const navItems = readFileSync(resolve(appRoot, 'src/router/nav.js'), 'utf8');
  const styles = readFileSync(resolve(appRoot, 'src/styles/main.css'), 'utf8');

  assert.match(nav, /site-nav__logo/);
  assert.match(nav, /huibu-logo\.png/);
  assert.match(nav, /慧步乒乓/);
  assert.match(readFileSync(resolve(appRoot, 'index.html'), 'utf8'), /<title>慧步乒乓<\/title>/);
  assert.match(nav, /site-nav__auth/);
  assert.match(nav, /site-nav__dropdown-trigger/);
  assert.match(nav, /脚步训练/);
  assert.match(navItems, /TRAINING_DROPDOWN/);
  assert.doesNotMatch(navItems, /auth:\s*true/);

  assert.match(styles, /\.site-nav[\s\S]*box-shadow:\s*0 1px 2px/);
  assert.match(styles, /\.site-nav[\s\S]*position:\s*sticky/);
  assert.match(styles, /\.site-nav__logo[\s\S]*height:\s*32px/);
  assert.match(styles, /\.site-nav__auth[\s\S]*background:\s*#2563eb/);
  assert.doesNotMatch(styles, /\.site-nav__link\.router-link-active[^{]*\{[^}]*background:\s*#eff6ff/);
});

test('legacy html keeps original page styles but points business entries to Vue routes', () => {
  const nav = readFileSync(resolve(projectRoot, 'assets/js/nav.js'), 'utf8');
  const files = ['home.html', 'product.html', 'team.html', 'report.html'];

  assert.equal(existsSync(resolve(projectRoot, 'auth.html')), false);

  for (const file of files) {
    const text = readFileSync(resolve(projectRoot, file), 'utf8');
    assert.doesNotMatch(text, /window\.location\.replace\('http:\/\/127\.0\.0\.1:5173/);
  }

  assert.match(nav, /href: 'home\.html'/);
  assert.match(nav, /href: 'product\.html'/);
  assert.match(nav, /href: '\/#\/training'/);
  assert.match(nav, /href: '\/#\/analysis'/);
  assert.match(nav, /href: 'team\.html'/);
  assert.match(nav, /href: '\/#\/auth'/);
  assert.match(nav, /target="_top"/);
});

test('preset footwork library mirrors the pose3d stepLibrary behavior', () => {
  assert.deepEqual(PRESET_STEP_TYPES, [
    'single-step',
    'side-step',
    'back-step',
    'two-point',
    'three-point',
    'four-point',
    'push-side-pounce',
    'full-table',
  ]);
  assert.equal(DEFAULT_LOOP_COUNTS.single, 10);
  assert.equal(DEFAULT_LOOP_COUNTS.combo, 5);

  assert.equal(PRESET_STEP_OPTION_GROUPS.length, 2);
  assert.equal(PRESET_STEP_OPTION_GROUPS[0].label, '单一步伐');
  assert.equal(PRESET_STEP_OPTION_GROUPS[1].label, '组合步伐');
  assert.deepEqual(
    PRESET_STEP_OPTION_GROUPS.flatMap((group) => group.options.map((option) => option.value)),
    PRESET_STEP_TYPES,
  );
  assert.equal(PRESET_STEP_OPTION_GROUPS[0].options.length, 3);
  assert.equal(PRESET_STEP_OPTION_GROUPS[0].options[0].label, '1. 跨步');
  assert.equal(PRESET_STEP_OPTION_GROUPS[0].options[2].label, '3. 撤步');
  assert.equal(PRESET_STEP_OPTION_GROUPS[1].options[0].label, '1. 两点跑位');
  assert.equal(PRESET_STEP_OPTION_GROUPS[1].options[4].label, '5. 全台摆速');
  assert.equal(getPresetStepLabel('single-step'), '跨步');
  assert.equal(getPresetStepLabel('full-table'), '全台摆速');
  assert.equal(getPresetStepLabel('cross-step'), '交叉步');
  assert.match(getPresetStepLogicHint('side-step'), /除中心外的 8 格/);
  assert.equal(getPresetHandRequirement('two-point'), '两个正手');
  assert.equal(getPresetHandRequirement('single-step'), '');
  assert.match(getPresetHandRequirement('back-step', 'right'), /右脚后撤步（右手为例）/);
  assert.match(getPresetHandRequirement('back-step', 'left'), /左脚后撤步（左手为例）/);
  assert.equal(getPresetStartCell('single-step', 'right'), 5);
  assert.deepEqual(generatePresetSteps('two-point', 'left', 2), [
    { cell: 6, type: 'active' },
    { cell: 4, type: 'active' },
    { cell: 6, type: 'active' },
    { cell: 4, type: 'active' },
  ]);
  assert.deepEqual(generatePresetSteps('three-point', 'right', 1), [
    { cell: 6, type: 'active' },
    { cell: 5, type: 'active' },
    { cell: 4, type: 'active' },
    { cell: 5, type: 'active' },
    { cell: 6, type: 'active' },
  ]);
  assert.deepEqual(generatePresetSteps('four-point', 'right', 1), [
    { cell: 5, type: 'active' },
    { cell: 4, type: 'active' },
    { cell: 5, type: 'active' },
    { cell: 6, type: 'active' },
    { cell: 5, type: 'active' },
  ]);
  assert.deepEqual(generatePresetSteps('four-point', 'right', 2), [
    { cell: 5, type: 'active' },
    { cell: 4, type: 'active' },
    { cell: 5, type: 'active' },
    { cell: 6, type: 'active' },
    { cell: 5, type: 'active' },
    { cell: 4, type: 'active' },
    { cell: 5, type: 'active' },
    { cell: 6, type: 'active' },
    { cell: 5, type: 'active' },
  ]);
  assert.deepEqual(generatePresetSteps('three-point', 'right', 2), [
    { cell: 6, type: 'active' },
    { cell: 5, type: 'active' },
    { cell: 4, type: 'active' },
    { cell: 5, type: 'active' },
    { cell: 6, type: 'active' },
    { cell: 5, type: 'active' },
    { cell: 4, type: 'active' },
    { cell: 5, type: 'active' },
    { cell: 6, type: 'active' },
  ]);
  assert.deepEqual(generatePresetSteps('push-side-pounce', 'right', 1), [
    { cell: 5, type: 'active' },
    { cell: 4, type: 'active' },
    { cell: 6, type: 'active' },
  ]);

  assert.equal(DEFAULT_FULL_TABLE_STEP_COUNT, 30);
  const fullTable = generatePresetSteps('full-table', 'right', 30);
  assert.equal(fullTable.length, 30);
  assert.ok(fullTable[0].cell === 4 || fullTable[0].cell === 6);
  for (let i = 2; i < fullTable.length; i += 1) {
    const a = fullTable[i - 2].cell;
    const b = fullTable[i - 1].cell;
    const c = fullTable[i].cell;
    if (a === b && b === c) {
      assert.fail(`full-table has three consecutive ${a} at index ${i - 2}`);
    }
  }
  for (let trial = 0; trial < 20; trial += 1) {
    const seq = generateFullTableSteps(30, () => Math.random());
    assert.equal(seq.length, 30);
    for (let i = 2; i < seq.length; i += 1) {
      if (seq[i - 2].cell === seq[i - 1].cell && seq[i - 1].cell === seq[i].cell) {
        assert.fail(`random full-table triple ${seq[i].cell}`);
      }
    }
  }

  const single = generatePresetSteps('single-step', 'right', 1, () => 0);
  assert.deepEqual(single, [
    { cell: 1, type: 'active' },
    { cell: 5, type: 'active' },
    { cell: 2, type: 'active' },
    { cell: 5, type: 'active' },
    { cell: 3, type: 'active' },
    { cell: 5, type: 'active' },
    { cell: 4, type: 'active' },
    { cell: 5, type: 'active' },
    { cell: 6, type: 'active' },
    { cell: 5, type: 'active' },
  ]);

  const allPresetSteps = PRESET_STEP_TYPES.flatMap((type) => generatePresetSteps(type, 'right', 1, () => 0));
  assert.equal(allPresetSteps.some((step) => step.type === 'return'), false);
  assert.equal(formatTrainingStep({ cell: 5, type: 'return' }), '5');
});

test('training prefs default includes full-table step count', () => {
  const prefs = createDefaultTrainingPrefs();
  assert.equal(prefs.fullTableStepCount, 30);
  assert.equal(prefs.loopCount, 10);
  assert.equal(prefs.stepSource, 'preset');
});

test('footwork demo videos use stepType filenames in public folder', () => {
  const footworkDir = resolve(appRoot, 'public/videos/footwork');
  for (const stepType of ['two-point', 'three-point', 'four-point', 'push-side-pounce', 'full-table']) {
    assert.ok(existsSync(resolve(footworkDir, `${stepType}.mp4`)), `${stepType}.mp4`);
    assert.equal(getFootworkDemoVideoUrl(stepType), `/videos/footwork/${stepType}.mp4`);
  }
});

test('recommended step intervals vary by step type level and mode', () => {
  assert.equal(getRecommendedStepIntervalMs('single-step', { level: 'amateur', mode: 'eval' }), 1500);
  assert.equal(getRecommendedStepIntervalMs('side-step', { level: 'level-1', mode: 'test' }), 940);
  assert.equal(getRecommendedStepIntervalMs('push-side-pounce', { level: 'amateur', mode: 'free' }), 1880);
  assert.match(
    formatRecommendedIntervalHint('two-point', { level: 'level-2', mode: 'eval' }),
    /推荐：两点跑位 · 1280 ms（二级 · 练习评估）/,
  );
});

test('training grid uses preset library and stable board layout hooks', () => {
  const grid = readFileSync(resolve(appRoot, 'src/components/TrainingGrid.vue'), 'utf8');
  const styles = readFileSync(resolve(appRoot, 'src/styles/main.css'), 'utf8');

  assert.match(grid, /recommendedIntervalHint/);
  assert.match(grid, /interval-recommendation/);
  assert.match(grid, /step-hand-requirement/);
  assert.match(grid, /stepHandRequirement/);
  assert.match(grid, /getPresetHandRequirement/);
  assert.match(styles, /\.step-hand-requirement/);
  assert.match(grid, /formatRecommendedIntervalHint/);
  assert.match(grid, /playStepCueSound/);
  assert.match(grid, /generatePresetSteps/);
  assert.match(grid, /fullTableStepCount/);
  assert.match(grid, /isFullTablePreset/);
  assert.match(grid, /产生多少步/);
  assert.match(grid, /loadTrainingPrefs/);
  assert.match(grid, /saveTrainingPrefs/);
  assert.match(grid, /getPresetStartCell/);
  assert.match(grid, /cachedSequence/);
  assert.match(grid, /showStartCellReady/);
  assert.match(grid, /<optgroup/);
  assert.match(grid, /PRESET_STEP_OPTION_GROUPS/);
  assert.match(grid, /runningStatusLabel/);
  assert.match(grid, /getPresetStepLabel/);
  assert.doesNotMatch(grid, /训练进行中/);
  assert.match(grid, /speakStartCue/);
  assert.match(grid, /beginFootworkSequence/);
  assert.match(grid, /startCueSpeech/);
  assert.doesNotMatch(grid, /READY_GO_PREPHASE_MS/);
  assert.match(grid, /FootworkDemoModal/);
  assert.match(grid, /FootworkDemoPreview/);
  assert.doesNotMatch(grid, /footwork-demo-trigger/);
  assert.match(grid, /countdown/);
  assert.doesNotMatch(grid, /Ready Go!/);
  assert.doesNotMatch(grid, /5R/);
  assert.doesNotMatch(grid, /activeStepType\.value = 'return'/);
  assert.doesNotMatch(grid, /return:\s*activeCell/);
  assert.doesNotMatch(grid, /activeCell\.value = startCell\.value/);
  assert.doesNotMatch(grid, /function presetSequence/);
  assert.deepEqual(
    PRESET_STEP_OPTIONS.map((option) => option.value),
    PRESET_STEP_TYPES,
  );

  assert.match(styles, /\.training-stage[\s\S]*min-height:/);
  assert.match(styles, /\.grid-board[\s\S]*width:\s*clamp/);
  assert.match(styles, /\.grid-cell\.ready[\s\S]*background:\s*#fef3c7/);
  assert.match(styles, /\.sequence-preview[\s\S]*max-height:/);
  assert.match(styles, /\.sequence-preview[\s\S]*overflow-y:\s*auto/);
  assert.match(styles, /\.footwork-demo-preview/);
  assert.match(styles, /\.footwork-demo-overlay/);
  assert.match(styles, /\.interval-recommendation/);

  assert.equal(getFootworkDemoVideoUrl('single-step'), '/videos/footwork/single-step.mp4');
  assert.equal(getFootworkDemoPosterUrl('single-step'), '/videos/footwork/single-step.jpg');
});

test('onboarding guide modules and anchors exist across Vue routes', () => {
  const guideProgress = readFileSync(resolve(appRoot, 'src/guides/guideProgress.js'), 'utf8');
  const trainingGuide = readFileSync(resolve(appRoot, 'src/guides/trainingGuide.js'), 'utf8');
  const auth = readFileSync(resolve(appRoot, 'src/views/AuthView.vue'), 'utf8');
  const training = readFileSync(resolve(appRoot, 'src/views/TrainingView.vue'), 'utf8');
  const grid = readFileSync(resolve(appRoot, 'src/components/TrainingGrid.vue'), 'utf8');
  const router = readFileSync(resolve(appRoot, 'src/router/index.js'), 'utf8');
  const main = readFileSync(resolve(appRoot, 'src/main.js'), 'utf8');
  const guideDriver = readFileSync(resolve(appRoot, 'src/guides/createGuideDriver.js'), 'utf8');
  const packageJson = JSON.parse(readFileSync(resolve(appRoot, 'package.json'), 'utf8'));

  assert.match(guideProgress, /ai_sport_lab\.guide_v1/);
  assert.match(guideProgress, /analysis:\s*'analysis'/);
  assert.match(guideProgress, /shouldAutoStartAnalysis/);
  assert.ok(packageJson.dependencies?.['driver.js']);
  assert.match(main, /import\s+['"]driver\.js\/dist\/driver\.css['"]/);
  assert.match(guideDriver, /import\s*\{\s*driver\s*\}\s*from\s*['"]driver\.js['"]/);
  assert.match(trainingGuide, /data-guide="mode-picker"/);
  assert.match(auth, /data-guide="auth-intro"/);
  assert.match(auth, /data-guide="auth-submit"/);
  assert.match(training, /data-guide="mode-picker"/);
  assert.match(training, /新手引导/);
  assert.match(grid, /data-guide="params"/);
  assert.match(grid, /data-guide="grid"/);
  assert.match(grid, /data-guide="controls"/);
  assert.match(grid, /data-guide="demo-preview"/);
  assert.match(router, /scheduleGuideForRoute/);
  assert.match(router, /onGoAnalysis/);
  assert.match(router, /router\.push\('\/analysis'\)/);
  assert.equal(existsSync(resolve(projectRoot, 'upload.html')), false);
});

test('App.vue always renders SiteNav regardless of fullFrame routes', () => {
  const app = readFileSync(resolve(appRoot, 'src/App.vue'), 'utf8');
  const styles = readFileSync(resolve(appRoot, 'src/styles/main.css'), 'utf8');
  const legacyView = readFileSync(resolve(appRoot, 'src/views/LegacyHtmlView.vue'), 'utf8');

  assert.match(app, /<SiteNav\s*\/>/);
  assert.doesNotMatch(app, /v-if="!route\.meta\.fullFrame"/);
  assert.match(styles, /--site-nav-height:\s*72px/);
  assert.match(styles, /height:\s*calc\(100vh - var\(--site-nav-height\)\)/);
  assert.match(legacyView, /embedded/);
});

test('legacy embedded mode hides duplicate nav and resolves assets from site root', () => {
  const legacyCss = readFileSync(resolve(projectRoot, 'assets/css/main.css'), 'utf8');
  const mainJs = readFileSync(resolve(projectRoot, 'assets/js/main.js'), 'utf8');
  const v1 = readFileSync(resolve(appRoot, '../web_1/v1.py'), 'utf8');

  assert.match(legacyCss, /html\[data-embedded='1'\]\s*#site-nav/);
  assert.match(mainJs, /embedded/);
  assert.match(mainJs, /dataset\.embedded\s*=\s*'1'/);
  assert.match(v1, /_inject_legacy_html_base/);
  assert.match(v1, /<base href="\/">/);
});

test('product marketing page avoids legacy html dead links', () => {
  const product = readFileSync(resolve(projectRoot, 'product.html'), 'utf8');

  assert.match(product, /href="\/#\/product"/);
  assert.doesNotMatch(product, /href="product\.html"/);
  assert.doesNotMatch(product, /href="home\.html"/);
  assert.doesNotMatch(product, /href="team\.html"/);
  assert.match(product, /href="\/#\/team"/);
});

test('guide progress tracks per-page dismiss state for auto guides', async () => {
  const guideProgress = readFileSync(resolve(appRoot, 'src/guides/guideProgress.js'), 'utf8');
  const authGuide = readFileSync(resolve(appRoot, 'src/guides/authGuide.js'), 'utf8');
  const trainingGuide = readFileSync(resolve(appRoot, 'src/guides/trainingGuide.js'), 'utf8');
  const scheduler = readFileSync(resolve(appRoot, 'src/guides/guideScheduler.js'), 'utf8');

  assert.match(guideProgress, /markGuideDismissed/);
  assert.match(guideProgress, /wasGuideDismissed/);
  assert.match(guideProgress, /dismissed/);
  assert.match(guideProgress, /shouldAutoStartAnalysis/);
  assert.match(authGuide, /markGuideDismissed\('auth'\)/);
  assert.match(trainingGuide, /markGuideDismissed\('training'\)/);
  assert.match(scheduler, /wasGuideDismissed\('auth'\)/);
  assert.match(scheduler, /wasGuideDismissed\('training'\)/);
  assert.match(trainingGuide, /force:\s*true/);

  const storage = new Map();
  globalThis.window = {
    localStorage: {
      getItem: (key) => storage.get(key) ?? null,
      setItem: (key, value) => {
        storage.set(key, value);
      },
    },
  };

  const {
    GUIDE_STAGES,
    getGuideStage,
    markGuideDismissed,
    resetGuide,
    setGuideStage,
    shouldAutoStartAuth,
    shouldAutoStartAnalysis,
    shouldAutoStartTraining,
    wasGuideDismissed,
  } = await import('../src/guides/guideProgress.js');

  resetGuide();
  assert.equal(shouldAutoStartAuth(), true);
  markGuideDismissed('auth');
  assert.equal(wasGuideDismissed('auth'), true);
  assert.equal(shouldAutoStartAuth(), false);

  resetGuide();
  setGuideStage(GUIDE_STAGES.training);
  assert.equal(shouldAutoStartTraining(), true);
  markGuideDismissed('training');
  assert.equal(shouldAutoStartTraining(), false);
  assert.equal(getGuideStage(), GUIDE_STAGES.training);

  resetGuide();
  setGuideStage(GUIDE_STAGES.analysis);
  assert.equal(shouldAutoStartAnalysis(), true);
  markGuideDismissed('analysis');
  assert.equal(wasGuideDismissed('analysis'), true);
  assert.equal(shouldAutoStartAnalysis(), false);
  assert.equal(getGuideStage(), GUIDE_STAGES.analysis);

  delete globalThis.window;
});

test('report page drops iframe nav and Vue analysis links to report history', () => {
  const report = readFileSync(resolve(projectRoot, 'report.html'), 'utf8');
  const analysis = readFileSync(resolve(appRoot, 'src/views/AnalysisView.vue'), 'utf8');
  const reportHistory = readFileSync(resolve(appRoot, 'src/views/ReportHistoryView.vue'), 'utf8');
  const reportHistoryStore = readFileSync(resolve(appRoot, 'src/composables/useReportHistory.js'), 'utf8');
  const reportCard = readFileSync(resolve(appRoot, 'src/components/ReportCard.vue'), 'utf8');
  const reportFilter = readFileSync(resolve(appRoot, 'src/components/ReportFilterBar.vue'), 'utf8');
  const reportCompare = readFileSync(resolve(appRoot, 'src/components/ReportCompareModal.vue'), 'utf8');
  const reportJs = readFileSync(resolve(projectRoot, 'assets/js/pages/report.js'), 'utf8');
  const router = readFileSync(resolve(appRoot, 'src/router/index.js'), 'utf8');
  const legacyView = readFileSync(resolve(appRoot, 'src/views/LegacyHtmlView.vue'), 'utf8');
  const v1 = readFileSync(resolve(appRoot, '../web_1/v1.py'), 'utf8');
  const styles = readFileSync(resolve(appRoot, 'src/styles/main.css'), 'utf8');

  assert.doesNotMatch(report, /id="site-nav"/);
  assert.doesNotMatch(report, /nav\.js/);
  assert.match(analysis, /\/report-history/);
  assert.match(analysis, /历史报告/);
  assert.match(styles, /analysis-header__history-link/);
  assert.match(router, /path:\s*'\/report-history'/);
  assert.match(router, /component:\s*ReportHistoryView/);
  assert.doesNotMatch(router, /legacyFile:\s*'report-history\.html'/);
  assert.doesNotMatch(legacyView, /report-history\.html/);
  assert.doesNotMatch(v1, /report-history\.html/);
  assert.equal(existsSync(resolve(projectRoot, 'report-history.html')), false);
  assert.match(reportHistory, /ReportFilterBar/);
  assert.match(reportHistory, /ReportCard/);
  assert.match(reportHistory, /ReportCompareModal/);
  assert.match(reportHistory, /fetchReports/);
  assert.match(reportHistory, /deleteReport/);
  assert.match(reportHistory, /compareReports/);
  assert.match(reportHistoryStore, /\/api\/reports\?user_id=/);
  assert.match(reportHistoryStore, /\/api\/reports\/compare\?ids=/);
  assert.match(reportHistoryStore, /method:\s*'DELETE'/);
  assert.match(reportCard, /\/#\/report\//);
  assert.match(reportCard, /查看详情/);
  assert.match(reportFilter, /update:filters/);
  assert.match(reportCompare, /useRadarChart/);
  assert.match(reportJs, /saveReportToUserHistory/);
  assert.match(reportJs, /POST/);
});

test('analysis header stays centered and loading progress uses backend fraction with real ETA', () => {
  const analysis = readFileSync(resolve(appRoot, 'src/views/AnalysisView.vue'), 'utf8');
  const job = readFileSync(resolve(appRoot, 'src/composables/useAnalysisJob.js'), 'utf8');
  const loading = readFileSync(resolve(projectRoot, 'loading.html'), 'utf8');
  const loadingJs = readFileSync(resolve(projectRoot, 'assets/js/pages/loading.js'), 'utf8');
  const monitorJs = readFileSync(resolve(projectRoot, 'assets/js/analysisJobMonitor.js'), 'utf8');
  const styles = readFileSync(resolve(appRoot, 'src/styles/main.css'), 'utf8');
  const v1 = readFileSync(resolve(appRoot, '../web_1/v1.py'), 'utf8');

  assert.match(analysis, /analysis-header/);
  assert.match(analysis, /analysis-header__meta/);
  assert.match(analysis, /analysis-header__history-link/);
  assert.match(analysis, /estimatedDurationSeconds/);
  assert.match(analysis, /job\.start/);
  assert.match(styles, /\.analysis-header[\s\S]*justify-items:\s*center/);
  assert.match(styles, /\.analysis-header[\s\S]*text-align:\s*center/);
  assert.match(styles, /analysis-header__history-link:hover/);
  assert.match(loading, /id="loading-eta"/);
  assert.match(loading, /analysisJobMonitor\.js/);
  assert.doesNotMatch(loading, /预计约需30秒/);
  assert.match(loadingJs, /AnalysisJobMonitor\.createAnalysisJobMonitor/);
  assert.match(job, /normalizeProgress/);
  assert.match(job, /estimated_duration_s/);
  assert.match(job, /预计还需/);
  assert.match(monitorJs, /normalizeProgress/);
  assert.match(monitorJs, /estimated_duration_s/);
  assert.match(monitorJs, /预计还需/);
  assert.match(v1, /"estimated_duration_s": meta\.get\("estimated_duration_s"\)/);
  assert.match(v1, /cancel_analysis_job/);
  assert.match(v1, /error_code="CANCELLED"/);
});

test('risk fixes wire training config upload and custom route display metadata', () => {
  const analysis = readFileSync(resolve(appRoot, 'src/views/AnalysisView.vue'), 'utf8');
  const paramsPanel = readFileSync(resolve(appRoot, 'src/components/AnalysisParamsPanel.vue'), 'utf8');
  const upload = readFileSync(resolve(appRoot, 'src/composables/useAnalysisUpload.js'), 'utf8');
  const grid = readFileSync(resolve(appRoot, 'src/components/TrainingGrid.vue'), 'utf8');
  const adminData = readFileSync(resolve(appRoot, 'src/services/adminData.js'), 'utf8');

  assert.match(paramsPanel, /trainingConfigId/);
  assert.match(paramsPanel, /trainingConfigs/);
  assert.match(paramsPanel, /update:trainingConfigId/);
  assert.match(analysis, /trainingConfigId/);
  assert.match(upload, /training_config_id/);

  assert.match(grid, /customActionRequirements/);
  assert.match(grid, /actionRequirements/);
  assert.match(grid, /customRhythm/);
  assert.match(grid, /defaultMs/);

  assert.match(adminData, /training-stats/);
  assert.match(adminData, /filterFields/);
});

test('pose3d report route uses the new real-data dashboard', () => {
  const router = readFileSync(resolve(appRoot, 'src/router/index.js'), 'utf8');
  const viewPath = resolve(appRoot, 'src/views/PingpongReportView.vue');
  const adapterPath = resolve(appRoot, 'src/services/reportAdapter.js');

  assert.equal(existsSync(viewPath), true);
  assert.equal(existsSync(adapterPath), true);
  assert.match(router, /import PingpongReportView/);
  assert.match(router, /path:\s*'\/report\/:jobId\?'/);
  assert.match(router, /component:\s*PingpongReportView/);
  assert.doesNotMatch(router, /path:\s*'\/report\/:jobId\?'[\s\S]*legacyFile:\s*'report\.html'/);

  const view = readFileSync(viewPath, 'utf8');
  const adapter = readFileSync(adapterPath, 'utf8');
  assert.match(view, /getAnalysisResult/);
  assert.match(view, /getReportUi/);
  assert.match(view, /buildPose3dReportModel/);
  assert.match(view, /StatsOverview/);
  assert.match(view, /FootworkHeatmap/);
  assert.match(view, /RadarMetrics/);
  assert.match(view, /FootPressure/);
  assert.match(view, /TablePlacement/);
  assert.match(view, /PeriodTiming/);
  assert.match(view, /DisplacementTrajectory/);
  assert.match(view, /SpeedAcceleration/);
  assert.match(view, /FlightParameters/);
  assert.match(view, /JointBiomechanics/);
  assert.match(view, /EfficiencyEvaluation/);
  assert.match(view, /ComparisonComprehensive/);

  assert.match(adapter, /summaryMetrics/);
  assert.match(adapter, /derivedStats/);
  assert.match(adapter, /qualityFlags/);
  assert.match(adapter, /timeseries/);
  assert.match(adapter, /universal2/);
  assert.doesNotMatch(view + adapter, /Math\.random|mock|fixture|hardcoded/i);
});
