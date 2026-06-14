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

// 每个资源定义说明：
//   endpoint      — API 路径前缀（CRUD 自动拼 /{id}）
//   columns       — 表格展示列
//   fields        — 新增/编辑表单字段
//   filterFields  — 筛选条件（可选）
//   supportsKeyword — 后端是否支持 ?keyword= 搜索（当前全部支持）
//   creatable / editable / deletable — 默认 true，可设为 false 禁用

export const RESOURCE_DEFINITIONS = [
  {
    key: 'subjects',
    title: '受试者',
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
          { value: '右手', label: '右手' },
          { value: '左手', label: '左手' },
        ],
      }),
      selectField('level', '水平', {
        options: [
          { value: '业余', label: '业余' },
          { value: '二级', label: '二级' },
          { value: '一级', label: '一级' },
        ],
      }),
      numberField('years', '训练年限'),
    ],
    filterFields: [
      selectField('hand', '持拍手', {
        options: [
          { value: '右手', label: '右手' },
          { value: '左手', label: '左手' },
        ],
      }),
      selectField('level', '水平', {
        options: [
          { value: '业余', label: '业余' },
          { value: '二级', label: '二级' },
          { value: '一级', label: '一级' },
        ],
      }),
    ],
  },
  {
    key: 'footwork-types',
    title: '基础步伐',
    endpoint: '/api/v1/footwork-types',
    description: '所有路线、训练配置和评估记录复用的步伐字典。',
    deletable: false,
    columns: ['code', 'name', 'category', 'defaultStartCell', 'defaultSequence', 'updatedAt'],
    fields: [
      textField('code', '编码', { required: true }),
      textField('name', '名称', { required: true }),
      textField('category', '分类'),
      numberField('defaultStartCell', '默认起点'),
      textField('defaultSequence', '默认序列'),
      textareaField('description', '说明'),
    ],
    filterFields: [
      selectField('category', '分类', {
        options: [
          { value: '基础步伐', label: '基础步伐' },
          { value: '步法模式', label: '步法模式' },
        ],
      }),
    ],
  },
  {
    key: 'routes',
    title: '自定义跑动序列',
    endpoint: '/api/v1/routes',
    description: '步伐训练路线、跑动序列、节奏和动作要求。',
    columns: ['name', 'footworkTypeId', 'sequence', 'startCell', 'isCustom', 'updatedAt'],
    fields: [
      textField('name', '路线名称', { required: true }),
      selectField('footworkTypeId', '关联步伐', { lookup: 'footwork-types' }),
      textField('sequence', '路线序列', { required: true, placeholder: '1,5,9,5' }),
      numberField('startCell', '起始宫格', { required: true, min: 1, max: 9 }),
      numberField('defaultMs', '默认步间隔（ms）', { min: 100, max: 5000, placeholder: '750' }),
      textareaField('actionRequirements', '动作要求'),
    ],
    filterFields: [selectField('footworkTypeId', '关联步伐', { lookup: 'footwork-types' })],
  },
  {
    key: 'training-configs',
    title: '训练配置',
    endpoint: '/api/v1/training-configs',
    description: '运动员、步伐、路线和训练参数的组合配置。',
    columns: ['subjectId', 'footworkTypeId', 'routeDefinitionId', 'mode', 'analysisProfile', 'updatedAt'],
    fields: [
      selectField('subjectId', '受试者', { lookup: 'subjects', required: true }),
      selectField('footworkTypeId', '基础步伐', { lookup: 'footwork-types' }),
      selectField('routeDefinitionId', '训练路线', { lookup: 'routes' }),
      selectField('mode', '训练模式', {
        options: [
          { value: '练习评估', label: '练习评估' },
          { value: '自由练习', label: '自由练习' },
          { value: '能力测试', label: '能力测试' },
        ],
      }),
      selectField('analysisProfile', '分析档位', {
        options: [
          { value: '快速', label: '快速' },
          { value: '均衡', label: '均衡' },
          { value: '高质量', label: '高质量' },
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
          { value: '练习评估', label: '练习评估' },
          { value: '自由练习', label: '自由练习' },
          { value: '能力测试', label: '能力测试' },
        ],
      }),
    ],
  },
  {
    key: 'training-videos',
    title: '训练视频',
    endpoint: '/api/v1/training-videos',
    description: '训练视频原始资源与左右机位文件信息，供运动学数据回溯。',
    hidden: true,
    columns: ['subjectId', 'trainingConfigId', 'leftOriginalName', 'rightOriginalName', 'createdAt'],
    fields: [
      selectField('subjectId', '受试者', { lookup: 'subjects', required: true }),
      selectField('trainingConfigId', '训练配置', { lookup: 'training-configs' }),
      textField('leftOriginalName', '左机位原始文件'),
      textField('rightOriginalName', '右机位原始文件'),
    ],
    filterFields: [
      selectField('subjectId', '受试者', { lookup: 'subjects' }),
      selectField('trainingConfigId', '训练配置', { lookup: 'training-configs' }),
    ],
  },
  {
    key: 'kinematics-datasets',
    title: '运动学数据',
    endpoint: '/api/v1/kinematics-datasets',
    description: '分析完成的运动学结果，含受试者、步法、评分与同步视频播放。',
    columns: ['subjectName', 'stepName', 'mode', 'profile', 'grade', 'leftVideoName', 'rightVideoName', 'syncedLeftVideoUrl', 'syncedRightVideoUrl', 'createdAt'],
    creatable: false,
    editable: false,
    deletable: false,
    fields: [],
    filterFields: [selectField('subjectId', '受试者', { lookup: 'subjects' }), textField('jobId', '分析任务 ID')],
  },
  {
    key: 'evaluations',
    title: '效果评估',
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
    endpoint: '/api/v1/accounts',
    description: '最小 RBAC 的登录账号，不等同于受试者。注册通过登录页完成。',
    columns: ['account', 'username', 'status', 'updatedAt'],
    creatable: false,  // 创建账号走注册流程，此处仅管理已有账号
    fields: [
      textField('account', '账号', { required: true }),
      textField('username', '用户名', { required: true }),
      selectField('status', '状态', {
        options: [
          { value: '启用', label: '启用' },
          { value: '禁用', label: '禁用' },
        ],
      }),
    ],
  },
  {
    key: 'roles',
    title: '角色',
    endpoint: '/api/v1/roles',
    description: '最小权限模型中的角色集合。',
    columns: ['code', 'name'],
    fields: [textField('code', '编码', { required: true }), textField('name', '名称', { required: true })],
  },
  {
    key: 'permissions',
    title: '权限',
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
  subjectName: '受试者',
  stepName: '步伐名称',
  profile: '分析档位',
  syncedLeftVideoUrl: '左同步视频',
  syncedRightVideoUrl: '右同步视频',
  leftVideoName: '左机位视频',
  rightVideoName: '右机位视频',
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
