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

// 列定义辅助：{ key, label, sortable?, sortField? }
function col(key, label, extra = {}) {
  return { key, label, ...extra };
}

// 筛选字段辅助：filterField(key, label, extra)
function filterField(key, label, extra = {}) {
  return { key, label, ...extra };
}

// 每个资源定义说明：
//   endpoint      — API 路径前缀（CRUD 自动拼 /{id}）
//   columns       — 表格展示列 [{key, label, sortable?, sortField?}]
//   fields        — 新增/编辑表单字段
//   filterFields  — 筛选字段 [{key, label, lookupTable?}]，选项+计数由后端 /api/v1/{resource} 的 filters 字段返回
//   creatable / editable / deletable — 默认 true，可设为 false 禁用

export const RESOURCE_DEFINITIONS = [
  {
    key: 'subjects',
    title: '受试者',
    endpoint: '/api/v1/subjects',
    description: '训练、分析、评估全链路的受试者基础信息。',
    columns: [
      col('displayName', '受试者', { sortable: true, sortField: 'name' }),
      col('age', '年龄', { sortable: true }),
      col('hand', '持拍手'),
      col('level', '水平'),
      col('years', '训练年限', { sortable: true }),
      col('updatedAt', '更新时间', { sortable: true, sortField: 'updated_at' }),
    ],
    fields: [
      textField('name', '姓名', { required: true }),
      numberField('age', '年龄'),
      numberField('heightCm', '身高 cm'),
      numberField('weightKg', '体重 kg'),
      selectField('hand', '持拍手', { options: [{ value: '右手', label: '右手' }, { value: '左手', label: '左手' }] }),
      selectField('level', '水平', { options: [{ value: '业余', label: '业余' }, { value: '二级', label: '二级' }, { value: '一级', label: '一级' }] }),
      numberField('years', '训练年限'),
    ],
    filterFields: [
      filterField('hand', '持拍手'),
      filterField('level', '水平'),
    ],
  },
  {
    key: 'footwork-types',
    title: '基础步伐',
    endpoint: '/api/v1/footwork-types',
    description: '所有路线、训练配置和评估记录复用的步伐字典。',
    deletable: false,
    creatable: false,
    editable: false,
    columns: [
      col('code', '编码', { sortable: true }),
      col('name', '名称', { sortable: true }),
      col('category', '分类'),
      col('defaultStartCell', '默认起点'),
      col('defaultSequence', '默认序列'),
      col('updatedAt', '更新时间', { sortable: true, sortField: 'updated_at' }),
    ],
    fields: [
      textField('code', '编码', { required: true }),
      textField('name', '名称', { required: true }),
      textField('category', '分类'),
      numberField('defaultStartCell', '默认起点'),
      textField('defaultSequence', '默认序列'),
      textareaField('description', '说明'),
    ],
    filterFields: [
      filterField('category', '分类'),
    ],
    getInitialData() {
      return { form: { name: '', category: '', defaultStartCell: 5, description: '' }, ftSeq: [] };
    },
    applyEditData(item) {
      const seq = (item.defaultSequence || String(item.defaultStartCell || 5)).split('-').map(Number).filter(n => n >= 1 && n <= 9);
      return { form: { name: item.name || '', category: item.category || '', defaultStartCell: item.defaultStartCell || 5, description: item.description || '' }, ftSeq: seq };
    },
    buildPayload(formData, ftSeqArr) {
      const code = 'ft_' + Date.now().toString(36);
      return { code, name: (formData.name || '').trim(), category: formData.category || null, default_start_cell: formData.defaultStartCell || 5, default_sequence: ftSeqArr.length ? ftSeqArr.join('-') : String(formData.defaultStartCell || 5), description: (formData.description || '').trim() || null };
    },
  },
  {
    key: 'routes',
    title: '自定义跑动序列',
    endpoint: '/api/v1/routes',
    description: '步伐训练路线、跑动序列、节奏和动作要求。',
    columns: [
      col('name', '路线名称', { sortable: true }),
      col('footworkTypeId', '关联步伐'),
      col('sequence', '走位序列'),
      col('startCell', '起始宫格'),
      col('isCustom', '自定义'),
      col('updatedAt', '更新时间', { sortable: true, sortField: 'updated_at' }),
    ],
    fields: [
      textField('name', '路线名称', { required: true }),
      selectField('footworkTypeId', '关联步伐', { lookup: 'footwork-types' }),
      textField('sequence', '路线序列', { required: true, placeholder: '1,5,9,5' }),
      numberField('startCell', '起始宫格', { required: true, min: 1, max: 9 }),
      numberField('defaultMs', '默认步间隔（ms）', { min: 100, max: 5000, placeholder: '750' }),
      textareaField('actionRequirements', '动作要求'),
    ],
    filterFields: [
      filterField('footworkTypeId', '关联步伐', { lookupTable: 'footwork-types' }),
    ],
    getInitialData() {
      return { form: { name: '', footworkTypeId: '', startCell: 5, defaultMs: '', actionRequirements: '' }, ftSeq: [] };
    },
    applyEditData(item) {
      const seq = (item.sequence || '').split(',').map(Number).filter(n => n >= 1 && n <= 9);
      return { form: { name: item.name || '', footworkTypeId: item.footworkTypeId || '', startCell: item.startCell || 5, defaultMs: item.defaultMs || '', actionRequirements: item.actionRequirements || '' }, ftSeq: seq };
    },
    buildPayload(formData, ftSeqArr) {
      return { name: (formData.name || '').trim(), footworkTypeId: formData.footworkTypeId || null, startCell: formData.startCell || 5, sequence: ftSeqArr.length ? ftSeqArr.join(',') : '', defaultMs: formData.defaultMs || null, actionRequirements: (formData.actionRequirements || '').trim() || null };
    },
  },
  {
    key: 'training-configs',
    title: '训练配置',
    endpoint: '/api/v1/training-configs',
    description: '运动员、步伐、路线和训练参数的组合配置。',
    columns: [
      col('subjectId', '受试者'),
      col('footworkTypeId', '基础步伐'),
      col('routeDefinitionId', '训练路线'),
      col('mode', '训练模式'),
      col('analysisProfile', '分析档位'),
      col('updatedAt', '更新时间', { sortable: true, sortField: 'updated_at' }),
    ],
    fields: [
      selectField('subjectId', '受试者', { lookup: 'subjects', required: true }),
      selectField('footworkTypeId', '基础步伐', { lookup: 'footwork-types' }),
      selectField('routeDefinitionId', '训练路线', { lookup: 'routes' }),
      selectField('mode', '训练模式', { options: [{ value: '练习评估', label: '练习评估' }, { value: '自由练习', label: '自由练习' }, { value: '能力测试', label: '能力测试' }] }),
      selectField('analysisProfile', '分析档位', { options: [{ value: '快速', label: '快速' }, { value: '均衡', label: '均衡' }, { value: '高质量', label: '高质量' }] }),
      numberField('stepIntervalMs', '步间隔 ms'),
      numberField('loopCount', '循环次数'),
      numberField('fullTableStepCount', '全台步数'),
      jsonField('configSnapshot', '配置快照 JSON'),
    ],
    filterFields: [
      filterField('subjectId', '受试者', { lookupTable: 'subjects' }),
      filterField('footworkTypeId', '基础步伐', { lookupTable: 'footwork-types' }),
      filterField('routeDefinitionId', '训练路线', { lookupTable: 'routes' }),
      filterField('mode', '训练模式'),
    ],
  },
  {
    key: 'training-videos',
    title: '训练视频',
    endpoint: '/api/v1/training-videos',
    description: '训练视频原始资源与左右机位文件信息，供运动学数据回溯。',
    hidden: true,
    columns: [
      col('subjectId', '受试者'),
      col('trainingConfigId', '训练配置'),
      col('leftOriginalName', '左机位'),
      col('rightOriginalName', '右机位'),
      col('createdAt', '创建时间', { sortable: true, sortField: 'created_at' }),
    ],
    fields: [
      selectField('subjectId', '受试者', { lookup: 'subjects', required: true }),
      selectField('trainingConfigId', '训练配置', { lookup: 'training-configs' }),
      textField('leftOriginalName', '左机位原始文件'),
      textField('rightOriginalName', '右机位原始文件'),
    ],
    filterFields: [
      filterField('subjectId', '受试者', { lookupTable: 'subjects' }),
      filterField('trainingConfigId', '训练配置', { lookupTable: 'training-configs' }),
    ],
  },
  {
    key: 'kinematics-datasets',
    title: '运动学数据',
    endpoint: '/api/v1/kinematics-datasets',
    description: '分析完成的运动学结果，含受试者、步法、评分与同步视频播放。',
    columns: [
      col('subjectName', '受试者'),
      col('stepName', '步伐名称'),
      col('mode', '报告模式'),
      col('profile', '分析档位'),
      col('grade', '等级'),
      col('createdAt', '创建时间', { sortable: true, sortField: 'created_at' }),
    ],
    creatable: false,
    editable: false,
    fields: [],
    filterFields: [
      filterField('subjectId', '受试者', { lookupTable: 'subjects' }),
      filterField('jobId', '分析任务 ID', { type: 'text' }),
    ],
  },
  {
    key: 'evaluations',
    title: '效果评估',
    endpoint: '/api/v1/evaluations',
    description: '基于运动学数据的训练效果评估记录。',
    columns: [
      col('subjectId', '受试者'),
      col('analysisJobId', '分析任务'),
      col('kinematicsDatasetId', '运动学数据'),
      col('score', '评分', { sortable: true }),
      col('grade', '等级'),
      col('createdAt', '创建时间', { sortable: true, sortField: 'created_at' }),
    ],
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
      filterField('subjectId', '受试者', { lookupTable: 'subjects' }),
      filterField('kinematicsDatasetId', '运动学数据', { lookupTable: 'kinematics-datasets' }),
      filterField('grade', '等级', { type: 'text' }),
    ],
  },
  {
    key: 'accounts',
    title: '账号',
    endpoint: '/api/v1/accounts',
    description: '最小 RBAC 的登录账号，不等同于受试者。注册通过登录页完成。',
    columns: [
      col('account', '账号', { sortable: true }),
      col('username', '用户名', { sortable: true }),
      col('status', '状态'),
      col('updatedAt', '更新时间', { sortable: true, sortField: 'updated_at' }),
    ],
    creatable: false,
    fields: [
      textField('account', '账号', { required: true }),
      textField('username', '用户名', { required: true }),
      selectField('status', '状态', { options: [{ value: '启用', label: '启用' }, { value: '禁用', label: '禁用' }] }),
    ],
    filterFields: [
      filterField('status', '状态'),
    ],
  },
  {
    key: 'roles',
    title: '角色',
    endpoint: '/api/v1/roles',
    description: '最小权限模型中的角色集合。',
    columns: [
      col('code', '编码', { sortable: true }),
      col('name', '名称', { sortable: true }),
    ],
    fields: [textField('code', '编码', { required: true }), textField('name', '名称', { required: true })],
  },
  {
    key: 'permissions',
    title: '权限',
    endpoint: '/api/v1/permissions',
    description: '后端接口权限点字典。',
    columns: [
      col('code', '编码', { sortable: true }),
      col('name', '名称', { sortable: true }),
    ],
    fields: [textField('code', '编码', { required: true }), textField('name', '名称', { required: true })],
  },
];

// 保留 COLUMN_LABELS 用于表单字段标签和向后兼容
export const COLUMN_LABELS = {
  id: 'ID', name: '名称', code: '编码', category: '分类', description: '说明',
  updatedAt: '更新时间', createdAt: '创建时间', status: '状态', isCustom: '自定义',
  age: '年龄', hand: '持拍手', level: '水平', years: '训练年限', heightCm: '身高', weightKg: '体重',
  defaultStartCell: '默认起点', defaultSequence: '默认序列',
  footworkTypeId: '关联步伐', sequence: '走位序列', startCell: '起始宫格',
  subjectId: '受试者', routeDefinitionId: '训练路线', mode: '训练模式', analysisProfile: '分析档位',
  leftOriginalName: '左机位', rightOriginalName: '右机位', trainingConfigId: '训练配置',
  jobId: '分析任务', trainingVideoId: '训练视频', frameMetricsPath: '帧指标', sessionSummaryPath: '汇总',
  analysisJobId: '分析任务', kinematicsDatasetId: '运动学数据', score: '评分', grade: '等级',
  username: '用户名', account: '账号', displayName: '受试者', subjectName: '受试者',
  stepName: '步伐名称', profile: '分析档位',
  syncedLeftVideoUrl: '左同步视频', syncedRightVideoUrl: '右同步视频',
  leftVideoName: '左机位视频', rightVideoName: '右机位视频',
};

// 资源快速查找（key → definition）
export const LOOKUP_RESOURCES = Object.fromEntries(RESOURCE_DEFINITIONS.map((item) => [item.key, item]));

// 将后端 filter 聚合数据转为前端 chip 格式：{key, label, options: [{value, label, count}]}
export function parseFilterAggregations(rawFilters) {
  if (!Array.isArray(rawFilters)) return [];
  return rawFilters.map(group => ({
    key: group.key,
    label: group.label,
    options: (group.options || []).map(opt => ({
      value: String(opt.value ?? ''),
      label: opt.label ?? String(opt.value ?? ''),
      count: Number(opt.count) || 0,
    })),
  }));
}

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
