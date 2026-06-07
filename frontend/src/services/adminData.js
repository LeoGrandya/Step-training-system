/** MySQL v1 管理台数据源配置与通用 CRUD 请求。 */
import { request } from './api.js';

function textField(key, label, extra = {}) {
  return { key, label, type: 'text', ...extra };
}

function numberField(key, label, extra = {}) {
  return { key, label, type: 'number', ...extra };
}

function selectField(key, label, extra = {}) {
  return { key, label, type: 'select', ...extra };
}

function textareaField(key, label, extra = {}) {
  return { key, label, type: 'textarea', ...extra };
}

function jsonField(key, label, extra = {}) {
  return { key, label, type: 'json', ...extra };
}

export const RESOURCE_DEFINITIONS = [
  {
    key: 'subjects',
    title: '受试者',
    owner: '陈彦竹',
    endpoint: '/api/v1/subjects',
    description: '训练、分析、评估全链路的受试者基础信息。',
    columns: ['name', 'age', 'hand', 'level', 'years', 'updatedAt'],
    fields: [
      textField('name', '姓名', { required: true }),
      numberField('age', '年龄'),
      numberField('heightCm', '身高 cm'),
      numberField('weightKg', '体重 kg'),
      selectField('hand', '持拍手', {
        options: [
          { value: 'right', label: '右手' },
          { value: 'left', label: '左手' },
        ],
      }),
      selectField('level', '水平', {
        options: [
          { value: 'amateur', label: '业余' },
          { value: 'level-2', label: '二级' },
          { value: 'level-1', label: '一级' },
        ],
      }),
      numberField('years', '训练年限'),
    ],
    filterFields: [
      selectField('hand', '持拍手', {
        options: [
          { value: 'right', label: '右手' },
          { value: 'left', label: '左手' },
        ],
      }),
      selectField('level', '水平', {
        options: [
          { value: 'amateur', label: '业余' },
          { value: 'level-2', label: '二级' },
          { value: 'level-1', label: '一级' },
        ],
      }),
    ],
  },
  {
    key: 'footwork-types',
    title: '基础步伐',
    owner: '陈彦竹',
    endpoint: '/api/v1/footwork-types',
    description: '所有路线、训练配置和评估记录复用的步伐字典。',
    columns: ['code', 'name', 'category', 'defaultStartCell', 'defaultSequence', 'updatedAt'],
    fields: [
      textField('code', '编码', { required: true }),
      textField('name', '名称', { required: true }),
      textField('category', '分类'),
      numberField('defaultStartCell', '默认起点'),
      textField('defaultSequence', '默认序列'),
      textareaField('description', '说明'),
    ],
    filterFields: [textField('category', '分类')],
  },
  {
    key: 'routes',
    title: '自定义跑动序列',
    owner: '雷润华',
    endpoint: '/api/v1/routes',
    description: '步伐训练路线、跑动序列、节奏和动作要求。',
    columns: ['name', 'footworkTypeId', 'sequence', 'startCell', 'isCustom', 'updatedAt'],
    fields: [
      textField('name', '路线名称', { required: true }),
      selectField('footworkTypeId', '关联步伐', { lookup: 'footwork-types' }),
      textField('sequence', '路线序列', { required: true, placeholder: '1,5,9,5' }),
      numberField('startCell', '起始宫格', { required: true, min: 1, max: 9 }),
      jsonField('rhythm', '节奏 JSON', { placeholder: '{"defaultMs":750}' }),
      textareaField('actionRequirements', '动作要求'),
    ],
    filterFields: [selectField('footworkTypeId', '关联步伐', { lookup: 'footwork-types' })],
  },
  {
    key: 'training-configs',
    title: '训练配置',
    owner: '金彦廷',
    endpoint: '/api/v1/training-configs',
    description: '运动员、步伐、路线和训练参数的组合配置。',
    columns: ['subjectId', 'footworkTypeId', 'routeDefinitionId', 'mode', 'analysisProfile', 'updatedAt'],
    fields: [
      selectField('subjectId', '受试者', { lookup: 'subjects', required: true }),
      selectField('footworkTypeId', '基础步伐', { lookup: 'footwork-types' }),
      selectField('routeDefinitionId', '训练路线', { lookup: 'routes' }),
      selectField('mode', '训练模式', {
        options: [
          { value: 'eval', label: '练习评估' },
          { value: 'free', label: '自由练习' },
          { value: 'test', label: '能力测试' },
        ],
      }),
      selectField('analysisProfile', '分析档位', {
        options: [
          { value: 'fast', label: 'fast' },
          { value: 'balanced', label: 'balanced' },
          { value: 'quality', label: 'quality' },
        ],
      }),
      numberField('stepIntervalMs', '步间隔 ms'),
      numberField('loopCount', '循环次数'),
      numberField('fullTableStepCount', '全台步数'),
      jsonField('configSnapshot', '配置快照 JSON'),
    ],
    filterFields: [
      selectField('subjectId', '受试者', { lookup: 'subjects' }),
      selectField('footworkTypeId', '基础步伐', { lookup: 'footwork-types' }),
      selectField('routeDefinitionId', '训练路线', { lookup: 'routes' }),
      selectField('mode', '训练模式', {
        options: [
          { value: 'eval', label: '练习评估' },
          { value: 'free', label: '自由练习' },
          { value: 'test', label: '能力测试' },
        ],
      }),
    ],
  },
  {
    key: 'training-videos',
    title: '训练视频',
    owner: '金彦廷',
    endpoint: '/api/v1/training-videos',
    description: '视频文件仍在文件系统，MySQL 只保存路径、状态和关联关系。',
    columns: ['subjectId', 'trainingConfigId', 'leftOriginalName', 'rightOriginalName', 'status', 'createdAt'],
    creatable: false,
    fields: [
      selectField('subjectId', '受试者', { lookup: 'subjects' }),
      selectField('trainingConfigId', '训练配置', { lookup: 'training-configs' }),
      textField('leftVideoPath', '左机位路径'),
      textField('rightVideoPath', '右机位路径'),
      textField('leftOriginalName', '左机位文件名'),
      textField('rightOriginalName', '右机位文件名'),
      textField('status', '状态'),
    ],
    filterFields: [
      selectField('subjectId', '受试者', { lookup: 'subjects' }),
      selectField('trainingConfigId', '训练配置', { lookup: 'training-configs' }),
      textField('status', '状态'),
    ],
  },
  {
    key: 'kinematics-datasets',
    title: '运动学数据',
    owner: '许婉其',
    endpoint: '/api/v1/kinematics-datasets',
    description: '分析完成后的 CSV/JSON 产物索引和关键摘要。',
    columns: ['subjectId', 'jobId', 'trainingVideoId', 'frameMetricsPath', 'sessionSummaryPath', 'createdAt'],
    creatable: false,
    editable: false,
    deletable: false,
    fields: [],
    filterFields: [selectField('subjectId', '受试者', { lookup: 'subjects' }), textField('jobId', '分析任务 ID')],
  },
  {
    key: 'evaluations',
    title: '效果评估',
    owner: '郝雨萱',
    endpoint: '/api/v1/evaluations',
    description: '基于运动学数据的训练效果评估记录。',
    columns: ['subjectId', 'analysisJobId', 'kinematicsDatasetId', 'score', 'grade', 'createdAt'],
    fields: [
      selectField('subjectId', '受试者', { lookup: 'subjects', required: true }),
      textField('analysisJobId', '分析任务 ID'),
      selectField('kinematicsDatasetId', '运动学数据', { lookup: 'kinematics-datasets' }),
      selectField('footworkTypeId', '基础步伐', { lookup: 'footwork-types' }),
      selectField('routeDefinitionId', '训练路线', { lookup: 'routes' }),
      numberField('score', '评分'),
      textField('grade', '等级'),
      jsonField('summary', '评估摘要 JSON'),
      jsonField('suggestions', '建议 JSON'),
    ],
    filterFields: [
      selectField('subjectId', '受试者', { lookup: 'subjects' }),
      selectField('kinematicsDatasetId', '运动学数据', { lookup: 'kinematics-datasets' }),
      textField('grade', '等级'),
    ],
  },
  {
    key: 'accounts',
    title: '账号',
    owner: '金彦廷',
    endpoint: '/api/v1/accounts',
    description: '最小 RBAC 的登录账号，不等同于受试者。',
    columns: ['account', 'username', 'status', 'updatedAt'],
    fields: [
      textField('account', '账号', { required: true }),
      textField('passwordHash', '密码哈希', { required: true }),
      textField('username', '用户名', { required: true }),
      selectField('status', '状态', {
        options: [
          { value: 'active', label: 'active' },
          { value: 'disabled', label: 'disabled' },
        ],
      }),
    ],
  },
  {
    key: 'roles',
    title: '角色',
    owner: '金彦廷',
    endpoint: '/api/v1/roles',
    description: '最小权限模型中的角色集合。',
    columns: ['code', 'name'],
    fields: [textField('code', '编码', { required: true }), textField('name', '名称', { required: true })],
  },
  {
    key: 'permissions',
    title: '权限',
    owner: '金彦廷',
    endpoint: '/api/v1/permissions',
    description: '后端接口权限点字典。',
    columns: ['code', 'name'],
    fields: [textField('code', '编码', { required: true }), textField('name', '名称', { required: true })],
  },
];

export const COLUMN_LABELS = {
  id: 'ID',
  name: '名称',
  code: '编码',
  category: '分类',
  description: '说明',
  updatedAt: '更新时间',
  createdAt: '创建时间',
  status: '状态',
  isCustom: '自定义',
  age: '年龄',
  hand: '持拍手',
  level: '水平',
  years: '训练年限',
  heightCm: '身高',
  weightKg: '体重',
  defaultStartCell: '默认起点',
  defaultSequence: '默认序列',
  footworkTypeId: '关联步伐',
  sequence: '走位序列',
  startCell: '起始宫格',
  subjectId: '受试者',
  routeDefinitionId: '训练路线',
  mode: '训练模式',
  analysisProfile: '分析档位',
  leftOriginalName: '左机位',
  rightOriginalName: '右机位',
  trainingConfigId: '训练配置',
  jobId: '分析任务',
  trainingVideoId: '训练视频',
  frameMetricsPath: '帧指标',
  sessionSummaryPath: '汇总',
  analysisJobId: '分析任务',
  kinematicsDatasetId: '运动学数据',
  score: '评分',
  grade: '等级',
  username: '用户名',
  account: '账号',
  displayName: '用户名',
};

export const LOOKUP_RESOURCES = Object.fromEntries(RESOURCE_DEFINITIONS.map((item) => [item.key, item]));

function appendQuery(endpoint, query = {}) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === '') continue;
    params.set(key, value);
  }
  const suffix = params.toString();
  return suffix ? `${endpoint}?${suffix}` : endpoint;
}

export function listAdminRecords(resource, query = {}) {
  return request(appendQuery(resource.endpoint, query));
}

export function getTrainingStats() {
  return request('/api/v1/training-stats');
}

export function createAdminRecord(resource, payload) {
  return request(resource.endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function updateAdminRecord(resource, itemId, payload) {
  return request(`${resource.endpoint}/${encodeURIComponent(itemId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function deleteAdminRecord(resource, itemId) {
  return request(`${resource.endpoint}/${encodeURIComponent(itemId)}`, { method: 'DELETE' });
}
