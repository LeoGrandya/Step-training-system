<!-- MySQL v1 数据管理工作台：管理核心业务资源。筛选面板由 ResourceTable 承载。 -->
<template>
  <section class="page-stack data-management-page">
    <header class="data-management-header">
      <div>
        <h1>数据管理</h1>
      </div>
      <button type="button" class="secondary-button" @click="loadResources">刷新</button>
    </header>

    <div class="data-management-layout">
      <!-- 左侧资源导航 -->
      <aside class="data-management-sidebar" aria-label="资源类型">
        <button
          v-for="resource in visibleResources"
          :key="resource.key"
          type="button"
          class="data-management-tab"
          :class="{ 'is-active': resource.key === activeKey }"
          @click="switchResource(resource.key)"
        >
          <span>{{ resource.title }}</span>
        </button>
      </aside>

      <!-- 右侧内容区 -->
      <ResourceTable
        :key="activeKey"
        :resource="activeResource"
        :items="items"
        :total="total"
        :loading-state="loadingState"
        :error-text="errorText"
        :deleting="deleting"
        :filters="filterAggregations"
        :initial-keyword="currentQuery.keyword"
        :initial-limit="currentQuery.limit"
        :initial-offset="currentQuery.offset"
        :initial-filters="currentQuery.filters"
        :initial-sort-by="currentQuery.sortBy"
        :initial-sort-order="currentQuery.sortOrder"
        @search="onTableSearch"
        @create="openCreateModal"
        @edit="editResource"
        @delete="deleteResource"
        @view-video="openVideoPlayer"
        @view-footwork="viewFootwork"
      />
    </div>

    <!-- 新增 / 编辑弹窗 -->
    <Teleport to="body">
      <div v-if="showModal" class="data-management-modal" @click.self="closeModal">
        <div class="data-management-modal__card">
          <div class="data-management-modal__head">
            <h3>{{ viewMode ? '查看基础步伐' : (editingId ? '编辑记录' : '新增记录') }}</h3>
            <button type="button" class="link-button" @click="closeModal" aria-label="关闭">&#10007;</button>
          </div>

          <p v-if="modalError" class="data-management-error">{{ modalError }}</p>

          <FootworkForm
            v-if="activeResource.key === 'footwork-types'"
            ref="formRef"
            :initial-data="formInitialData"
            :editing-id="editingId"
            :saving="saving"
            :view-mode="viewMode"
            @submit="onFormSubmit"
            @cancel="closeModal"
          />
          <RouteForm
            v-else-if="activeResource.key === 'routes'"
            ref="formRef"
            :initial-data="formInitialData"
            :editing-id="editingId"
            :saving="saving"
            :lookups="formLookups"
            @submit="onFormSubmit"
            @cancel="closeModal"
          />
          <ResourceForm
            v-else
            ref="formRef"
            :resource="activeResource"
            :initial-data="formInitialData"
            :editing-id="editingId"
            :saving="saving"
            :lookups="formLookups"
            @submit="onGenericFormSubmit"
            @cancel="closeModal"
          />
        </div>
      </div>
    </Teleport>

    <!-- 通用结果弹窗 -->
    <ResultModal
      :show="resultModal.show"
      :state="resultModal.state"
      :title="resultModal.title"
      :desc="resultModal.desc"
      :error="resultModal.error"
      :confirm-label="resultModal._confirmLabel || ''"
      @dismiss="dismissResultModal"
      @confirm="resultModal._onConfirm?.()"
      @retry="retryFromResult"
    />

    <!-- 视频播放弹窗 -->
    <VideoPlayerModal
      :show="videoPlayer.show"
      :left-url="videoPlayer.leftUrl"
      :right-url="videoPlayer.rightUrl"
      :subject-name="videoPlayer.subjectName"
      @close="videoPlayer.show = false"
    />
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import {
  LOOKUP_RESOURCES,
  RESOURCE_DEFINITIONS,
  createAdminRecord,
  deleteAdminRecord,
  listAdminRecords,
  parseFilterAggregations,
  updateAdminRecord,
} from '../services/adminData.js';
import { notifySubjectChanged } from '../stores/subjectEvents.js';
import ResourceTable from '../components/data-management/ResourceTable.vue';
import ResourceForm from '../components/data-management/ResourceForm.vue';
import FootworkForm from '../components/data-management/FootworkForm.vue';
import RouteForm from '../components/data-management/RouteForm.vue';
import ResultModal from '../components/data-management/ResultModal.vue';
import VideoPlayerModal from '../components/data-management/VideoPlayerModal.vue';

// ---- 资源与状态 ----
const resources = RESOURCE_DEFINITIONS;
const visibleResources = computed(() => resources.filter(r => !r.hidden));
const activeKey = ref(visibleResources.value[0]?.key || resources[0].key);
const activeResource = computed(() => resources.find(r => r.key === activeKey.value) || resources[0]);
const items = ref([]);
const total = ref(0);
const errorText = ref('');
const saving = ref(false);
const deleting = ref(false);

// 加载状态枚举
const loadingState = ref('initial'); // 'initial' | 'refreshing' | 'paginating' | 'idle'

// 当前查询参数（keyword / limit / offset / filters / sortBy / sortOrder）
const currentQuery = ref({
  keyword: '',
  limit: 20,
  offset: 0,
  filters: {},
  sortBy: '',
  sortOrder: 'asc',
});

// 筛选聚合数据（后端返回的 filters 字段）
const filterAggregations = ref([]);

// 表单 lookups（仅用于编辑/新增表单的下拉选项，不用筛选面板）
const formLookups = reactive({});

// ---- 表单弹窗 ----
const showModal = ref(false);
const editingId = ref('');
const modalError = ref('');
const viewMode = ref(false);
const formInitialData = ref({});
const formRef = ref(null);

// ---- 结果弹窗 ----
const resultModal = reactive({
  show: false,
  state: 'processing',
  title: '',
  desc: '',
  error: '',
  _pendingAction: null,
  _onConfirm: null,
});

// ---- 视频播放弹窗 ----
const videoPlayer = reactive({
  show: false,
  leftUrl: '',
  rightUrl: '',
  subjectName: '',
});

// ---- 表单 lookups 加载（仅编辑/新增表单需要，不影响筛选面板） ----
async function loadFormLookups() {
  const lookupKeys = [...new Set(activeResource.value.fields.map(f => f.lookup).filter(Boolean))];
  for (const key of lookupKeys) {
    const resource = LOOKUP_RESOURCES[key];
    if (!resource) continue;
    try {
      const payload = await listAdminRecords(resource, { limit: 200, offset: 0 });
      formLookups[key] = payload.items || [];
    } catch {
      formLookups[key] = [];
    }
  }
}

// ---- 数据加载 ----
async function loadResources() {
  if (loadingState.value === 'idle') {
    loadingState.value = 'refreshing';
  }
  errorText.value = '';
  try {
    const queryParams = {
      keyword: currentQuery.value.keyword,
      limit: currentQuery.value.limit,
      offset: currentQuery.value.offset,
      ...currentQuery.value.filters,
    };
    if (currentQuery.value.sortBy) {
      queryParams.sortBy = currentQuery.value.sortBy;
      queryParams.sortOrder = currentQuery.value.sortOrder;
    }

    const payload = await listAdminRecords(activeResource.value, queryParams);
    items.value = payload.items || [];
    total.value = payload.total || items.value.length;
    // 解析后端返回的筛选聚合
    filterAggregations.value = parseFilterAggregations(payload.filters);
  } catch (error) {
    items.value = [];
    total.value = 0;
    filterAggregations.value = [];
    errorText.value = translateError(activeResource.value, error.message || '加载失败');
  } finally {
    loadingState.value = 'idle';
  }
}

// ---- 表格事件 ----
function onTableSearch(query) {
  const isPageChange =
    query.offset !== currentQuery.value.offset &&
    query.limit === currentQuery.value.limit &&
    query.keyword === currentQuery.value.keyword &&
    JSON.stringify(query.filters) === JSON.stringify(currentQuery.value.filters) &&
    query.sortBy === currentQuery.value.sortBy &&
    query.sortOrder === currentQuery.value.sortOrder;

  currentQuery.value = query;
  if (isPageChange) {
    loadingState.value = 'paginating';
  } else {
    loadingState.value = 'refreshing';
  }
  loadResources();
}

// ---- 资源切换 ----
function switchResource(key) {
  activeKey.value = key;
  currentQuery.value = { keyword: '', limit: 20, offset: 0, filters: {}, sortBy: '', sortOrder: 'asc' };
  filterAggregations.value = [];
  closeModal();
  loadingState.value = 'initial';
  loadFormLookups();
  loadResources();
}

// ---- 表单生命周期 ----
function resolveInitialData(resource, item) {
  if (resource.applyEditData) return resource.applyEditData(item);
  if (resource.getInitialData) return resource.getInitialData();
  const data = {};
  for (const field of resource.fields) {
    const value = item ? item[field.key] : undefined;
    data[field.key] = field.type === 'json' && value ? JSON.stringify(value, null, 2) : (value ?? '');
  }
  return data;
}

function openCreateModal() {
  editingId.value = '';
  modalError.value = '';
  viewMode.value = false;
  formInitialData.value = resolveInitialData(activeResource.value, null);
  showModal.value = true;
}

function editResource(item) {
  editingId.value = item.id || item.jobId || '';
  modalError.value = '';
  viewMode.value = false;
  formInitialData.value = resolveInitialData(activeResource.value, item);
  showModal.value = true;
}

function viewFootwork(item) {
  editResource(item);
  viewMode.value = true;
}

function closeModal() {
  showModal.value = false;
  editingId.value = '';
  viewMode.value = false;
  formInitialData.value = {};
  formRef.value = null;
}

// ---- 保存 ----
function buildPayload(resource, formData, ftSeqArr) {
  if (resource.buildPayload) return resource.buildPayload(formData, ftSeqArr);
  const payload = {};
  for (const field of resource.fields) {
    payload[field.key] = parseFieldValue(field, formData[field.key]);
  }
  return payload;
}

function parseFieldValue(field, value) {
  if (value === '' || value === null || value === undefined) return null;
  if (field.type === 'number') {
    const next = Number(value);
    if (Number.isNaN(next)) throw new Error(`${field.label} 必须是数字`);
    return next;
  }
  if (field.type === 'json') {
    if (!String(value || '').trim()) return null;
    try { return JSON.parse(value); } catch {
      throw new Error(`${field.label} 必须是合法 JSON`);
    }
  }
  return value;
}

function onGenericFormSubmit(formData) {
  onFormSubmit({ formData, ftSeqArr: [] });
}

async function onFormSubmit({ formData, ftSeqArr }) {
  saving.value = true;
  modalError.value = '';
  try {
    const payload = buildPayload(activeResource.value, formData, ftSeqArr);
    const isEdit = !!editingId.value;

    showModal.value = false;
    _showProcessing(isEdit ? '正在保存…' : '正在创建…');

    if (isEdit) {
      await updateAdminRecord(activeResource.value, editingId.value, payload);
    } else {
      await createAdminRecord(activeResource.value, payload);
    }

    _notifySubjectChanged();
    await loadFormLookups();
    await loadResources();

    _showSuccess(isEdit ? '已更新' : '已新增');
    editingId.value = '';
    formInitialData.value = {};
  } catch (error) {
    resultModal._pendingAction = true;
    _showError(error.message || '保存失败');
  } finally {
    saving.value = false;
  }
}

// ---- 删除 ----
function _deleteItemLabel(item) {
  const rk = activeResource.value.key;
  if (rk === 'subjects') {
    const parts = [item.name].filter(Boolean);
    if (item.hand) parts.push(item.hand);
    if (item.level) parts.push(item.level);
    return parts.join(' / ') || item.id;
  }
  if (rk === 'routes') return item.name || item.sequence || item.id;
  if (rk === 'training-configs') {
    const subName = (formLookups['subjects'] || []).find(s => s.id === item.subjectId)?.name;
    return [subName, item.mode].filter(Boolean).join(' / ') || item.id;
  }
  if (rk === 'evaluations') {
    const subName = (formLookups['subjects'] || []).find(s => s.id === item.subjectId)?.name;
    const grade = item.grade ? `评级 ${item.grade}` : '';
    return [subName, grade].filter(Boolean).join(' / ') || item.id;
  }
  if (rk === 'accounts') return [item.username, item.account].filter(Boolean).join(' / ') || item.id;
  if (rk === 'roles') return item.name || item.code || item.id;
  if (rk === 'permissions') return item.name || item.code || item.id;
  return item.name || item.displayName || item.username || item.code || item.id;
}

const DELETE_CONSEQUENCES = {
  subjects: '删除受试者将同时删除其关联的所有训练配置、训练视频、分析任务、运动学数据和评估记录，此操作不可恢复。',
  routes: '删除路线将同时清除其包含的所有跑动步骤，引用此路线的训练配置将失去关联。',
  'training-configs': '删除训练配置后，关联的训练视频和分析任务仍保留，但将失去配置上下文。',
  evaluations: '删除评估记录不影响关联的运动学数据和分析任务。',
  accounts: '删除账号将同时移除其角色绑定，该账号将无法登录系统。',
  roles: '删除角色将同时移除所有账号与该角色的绑定关系。',
  permissions: '删除权限点将同时移除所有角色与该权限的绑定关系。',
};

const HIGH_RISK_KEYS = ['subjects', 'accounts'];
const HIGH_RISK_CONFIRM_LABEL = {
  subjects: 'deleteConfirmResourceName',
  accounts: 'deleteConfirmResourceName',
};

function deleteResource(item) {
  const itemId = item.id || item.jobId;
  if (!itemId) return;

  const label = _deleteItemLabel(item);
  const consequence = DELETE_CONSEQUENCES[activeResource.value.key] || '此操作不可恢复，请确认后再操作。';
  const isHighRisk = HIGH_RISK_KEYS.includes(activeResource.value.key);

  resultModal.show = true;
  resultModal.state = 'confirm';
  resultModal.title = `删除「${label}」？`;
  resultModal.desc = consequence;
  resultModal._confirmLabel = isHighRisk ? label : '';
  resultModal._onConfirm = async () => {
    resultModal.state = 'processing';
    resultModal.title = '正在删除…';
    resultModal.desc = '';
    deleting.value = true;
    errorText.value = '';
    try {
      await deleteAdminRecord(activeResource.value, itemId);
      _notifySubjectChanged();
      await loadFormLookups();
      await loadResources();
      _showSuccess('已删除');
    } catch (error) {
      resultModal.show = false;
      errorText.value = error.message || '删除失败';
    } finally {
      deleting.value = false;
    }
  };
}

// ---- 结果弹窗辅助 ----
function _showProcessing(title) { resultModal.show = true; resultModal.state = 'processing'; resultModal.title = title; }
function _showSuccess(title) { resultModal.show = true; resultModal.state = 'success'; resultModal.title = title; }
function _showError(error) { resultModal.show = true; resultModal.state = 'error'; resultModal.error = error; }

function dismissResultModal() {
  resultModal.show = false;
  resultModal._pendingAction = null;
  resultModal._onConfirm = null;
}

function retryFromResult() {
  resultModal.show = false;
  resultModal._pendingAction = null;
  showModal.value = true;
}

// ---- 错误转译 ----
const ERROR_TRANSLATIONS = {
  '关联数据不存在': '所选关联记录已被删除或不存在，请刷新页面后重试',
  '编码已存在': '该编码已被使用，请更换编码',
  '请填写名称': '请填写名称',
  '名称与序列组合已存在': '该名称与序列组合已存在，请更换名称或修改序列',
  '被其他记录引用，无法删除': '该记录被其他数据引用，无法删除。请先删除关联数据',
  '数据格式无效': '数据格式不正确，请检查输入',
};

function translateError(resource, rawError) {
  for (const [key, translation] of Object.entries(ERROR_TRANSLATIONS)) {
    if (rawError.includes(key)) return translation;
  }
  if (resource.key === 'subjects' && rawError.includes('同名')) {
    return '此账号下已存在同名受试者，请更换名称或补充年龄、身高等区分信息';
  }
  return rawError;
}

// ---- 跨组件通信 ----
function _notifySubjectChanged() {
  if (activeResource.value.key === 'subjects') {
    notifySubjectChanged();
  }
}

function openVideoPlayer(item) {
  videoPlayer.leftUrl = item.syncedLeftVideoUrl || '';
  videoPlayer.rightUrl = item.syncedRightVideoUrl || '';
  videoPlayer.subjectName = item.subjectName || '';
  videoPlayer.show = true;
}

// ---- 初始化 ----
onMounted(async () => {
  loadingState.value = 'initial';
  await loadFormLookups();
  await loadResources();
});
</script>
