<!-- MySQL v1 数据管理工作台：管理核心业务资源。 -->
<template>
  <section class="page-stack data-management-page">
    <header class="data-management-header">
      <div>
        <p class="eyebrow">MySQL v1</p>
        <h1>数据管理</h1>
      </div>
      <button type="button" class="secondary-button" @click="loadResources">刷新</button>
    </header>

    <div class="data-management-layout">
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

      <section class="data-management-panel">
        <div class="data-management-panel__head">
          <div>
            <h2>{{ activeResource.title }}</h2>
            <p>{{ activeResource.description }}</p>
          </div>
        </div>

        <div class="data-management-toolbar">
          <input
            v-model.trim="query.keyword"
            type="search"
            placeholder="搜索关键字..."
            @keyup.enter="loadResources"
          />
          <label
            v-for="field in activeFilterFields"
            :key="field.key"
            class="data-management-toolbar-field"
          >
            <span>{{ field.label }}</span>
            <select v-if="field.type === 'select'" v-model="query.filters[field.key]" @change="resetAndLoad">
              <option value="">全部</option>
              <option v-for="option in fieldOptions(field)" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
            <input
              v-else
              v-model.trim="query.filters[field.key]"
              :type="field.type"
              :placeholder="field.placeholder || ''"
              @keyup.enter="resetAndLoad"
            />
          </label>
          <select v-model.number="query.limit" @change="resetAndLoad">
            <option :value="10">10 条</option>
            <option :value="20">20 条</option>
            <option :value="50">50 条</option>
          </select>
          <button type="button" @click="resetAndLoad">查询</button>
          <button
            v-if="activeFilterFields.length"
            type="button"
            class="link-button"
            @click="clearFilters"
          >
            清空筛选
          </button>
        </div>

        <button
          v-if="activeResource.fields.length && activeResource.creatable !== false"
          type="button"
          class="data-management-add-btn"
          @click="openCreateModal"
        >
          + 新增记录
        </button>

        <p v-if="errorText" class="data-management-error">{{ errorText }}</p>

        <div class="data-management-table-wrap">
          <table class="data-management-table">
            <thead>
              <tr>
                <th v-for="column in activeResource.columns" :key="column">{{ COLUMN_LABELS[column] || column }}</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td :colspan="activeResource.columns.length + 1">加载中...</td>
              </tr>
              <tr v-else-if="!items.length">
                <td :colspan="activeResource.columns.length + 1">暂无数据</td>
              </tr>
              <tr v-for="item in items" v-else :key="item.id || item.jobId">
                <td v-for="column in activeResource.columns" :key="column">{{ displayValue(item[column]) }}</td>
                <td>
                  <div class="data-management-row-actions">
                    <button
                      v-if="activeResource.key === 'kinematics-datasets' && (item.syncedLeftVideoUrl || item.syncedRightVideoUrl)"
                      type="button"
                      class="secondary-button"
                      @click="openVideoPlayer(item)"
                    >
                      查看视频
                    </button>
                    <button
                      v-if="activeResource.editable !== false"
                      type="button"
                      class="secondary-button"
                      @click="editResource(item)"
                    >
                      编辑
                    </button>
                    <button
                      v-if="activeResource.key === 'footwork-types'"
                      type="button"
                      class="secondary-button"
                      @click="viewFootwork(item)"
                    >
                      查看
                    </button>
                    <button
                      v-if="activeResource.deletable !== false"
                      type="button"
                      class="danger-button"
                      :disabled="deleting"
                      @click="deleteResource(item)"
                    >
                      {{ deleting ? '删除中…' : '删除' }}
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <footer class="data-management-pagination">
          <span>共 {{ total }} 条，当前 {{ query.offset + 1 }} - {{ visibleEnd }}</span>
          <div>
            <button type="button" class="secondary-button" :disabled="query.offset <= 0" @click="prevPage">上一页</button>
            <button type="button" class="secondary-button" :disabled="visibleEnd >= total" @click="nextPage">下一页</button>
          </div>
        </footer>
      </section>
    </div>

    <!-- 新增 / 编辑弹窗 -->
    <Teleport to="body">
      <div v-if="showModal" class="data-management-modal" @click.self="closeModal">
        <div class="data-management-modal__card">
          <div class="data-management-modal__head">
            <h3>{{ viewMode ? '查看基础步伐' : (editingId ? '编辑记录' : '新增记录') }}</h3>
            <button type="button" class="link-button" @click="closeModal" aria-label="关闭">✕</button>
          </div>

          <p v-if="modalError" class="data-management-error">{{ modalError }}</p>

          <!-- 基础步伐专用：九宫格选点 -->
          <form v-if="activeResource.key === 'footwork-types'" class="data-management-form" @submit.prevent="viewMode ? closeModal() : saveResource()">
            <label class="data-management-field data-management-field--wide">
              <span>名称</span>
              <input v-model="form.name" type="text" required placeholder="例如：正手跨步" :disabled="viewMode" />
            </label>
            <label class="data-management-field">
              <span>分类</span>
              <select v-model="form.category" required :disabled="viewMode">
                <option value="">未选择</option>
                <option value="单一步伐">单一步伐</option>
                <option value="组合步伐">组合步伐</option>
              </select>
            </label>
            <label class="data-management-field">
              <span>起始格</span>
              <select v-model.number="form.defaultStartCell" :disabled="viewMode">
                <option v-for="n in 9" :key="n" :value="n">{{ n }}</option>
              </select>
            </label>
            <div class="data-management-field data-management-field--wide">
              <span>默认序列</span>
              <div class="ft-sequence-area">
                <div class="ft-grid">
                  <button
                    v-for="n in 9" :key="n" type="button"
                    class="ft-grid-cell"
                    :class="{ 'is-start': n === form.defaultStartCell, 'is-last': ftSeq.length && n === ftSeq[ftSeq.length - 1] }"
                    :disabled="viewMode"
                    @click="!viewMode && ftToggleCell(n)"
                  >
                    {{ n }}
                    <span v-if="n === form.defaultStartCell" class="ft-grid-tag">起点</span>
                  </button>
                </div>
                <div class="ft-seq-preview">
                  <template v-if="ftSeq.length">
                    <span v-for="(cell, i) in ftSeq" :key="i" class="ft-seq-badge" @click="!viewMode && ftSeq.splice(i, 1)">{{ cell }}</span>
                  </template>
                  <span v-else class="ft-seq-hint">{{ viewMode ? '无序列' : '点击九宫格添加步伐点' }}</span>
                </div>
                <button v-if="!viewMode" type="button" class="link-button ft-seq-clear" @click="ftSeq.splice(0)">清空序列</button>
              </div>
            </div>
            <label class="data-management-field data-management-field--wide">
              <span>说明</span>
              <textarea v-model="form.description" rows="2" placeholder="可选…" :disabled="viewMode"></textarea>
            </label>
            <div class="data-management-form__actions">
              <button v-if="!viewMode" type="submit" :disabled="saving">
                <span v-if="saving" class="data-management-saving-indicator"></span>
                {{ saving ? '保存中…' : (editingId ? '保存修改' : '新增记录') }}
              </button>
              <button type="button" class="secondary-button" @click="closeModal">{{ viewMode ? '关闭' : '取消' }}</button>
            </div>
          </form>

          <!-- 自定义跑动序列：九宫格选点 -->
          <form v-else-if="activeResource.key === 'routes'" class="data-management-form" @submit.prevent="saveResource">
            <label class="data-management-field data-management-field--wide">
              <span>名称</span>
              <input v-model="form.name" type="text" required placeholder="例如：正手两点" />
            </label>
            <label class="data-management-field">
              <span>关联步伐</span>
              <select v-model="form.footworkTypeId">
                <option value="">未选择</option>
                <option v-for="opt in fieldOptions({ lookup: 'footwork-types' })" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </label>
            <label class="data-management-field">
              <span>起始格</span>
              <select v-model.number="form.startCell">
                <option v-for="n in 9" :key="n" :value="n">{{ n }}</option>
              </select>
            </label>
            <div class="data-management-field data-management-field--wide">
              <span>走位序列</span>
              <div class="ft-sequence-area">
                <div class="ft-grid">
                  <button
                    v-for="n in 9" :key="n" type="button"
                    class="ft-grid-cell"
                    :class="{ 'is-start': n === (form.startCell || 5), 'is-last': ftSeq.length && n === ftSeq[ftSeq.length - 1] }"
                    @click="ftToggleCell(n)"
                  >
                    {{ n }}
                    <span v-if="n === (form.startCell || 5)" class="ft-grid-tag">起点</span>
                  </button>
                </div>
                <div class="ft-seq-preview">
                  <template v-if="ftSeq.length">
                    <span v-for="(cell, i) in ftSeq" :key="i" class="ft-seq-badge" @click="ftSeq.splice(i, 1)">{{ cell }}</span>
                  </template>
                  <span v-else class="ft-seq-hint">点击九宫格添加步伐点</span>
                </div>
                <button type="button" class="link-button ft-seq-clear" @click="ftSeq.splice(0)">清空序列</button>
              </div>
            </div>
            <label class="data-management-field">
              <span>默认间隔(ms)</span>
              <input v-model.number="form.defaultMs" type="number" min="100" max="5000" placeholder="750" />
            </label>
            <label class="data-management-field data-management-field--wide">
              <span>动作要求</span>
              <textarea v-model="form.actionRequirements" rows="2" placeholder="可选…"></textarea>
            </label>
            <div class="data-management-form__actions">
              <button type="submit" :disabled="saving">
                <span v-if="saving" class="data-management-saving-indicator"></span>
                {{ saving ? '保存中…' : (editingId ? '保存修改' : '新增记录') }}
              </button>
              <button type="button" class="secondary-button" @click="closeModal">取消</button>
            </div>
          </form>

          <!-- 通用表单 -->
          <form v-else class="data-management-form" @submit.prevent="saveResource">
            <label v-for="field in activeResource.fields" :key="field.key" class="data-management-field">
              <span>{{ field.label }}</span>
              <select v-if="field.type === 'select'" v-model="form[field.key]" :required="field.required">
                <option value="">未选择</option>
                <option v-for="option in fieldOptions(field)" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
              <textarea
                v-else-if="field.type === 'textarea' || field.type === 'json'"
                v-model="form[field.key]"
                :placeholder="field.placeholder || ''"
                rows="3"
              />
              <input
                v-else
                v-model="form[field.key]"
                :type="field.type"
                :min="field.min"
                :max="field.max"
                :required="field.required"
                :placeholder="field.placeholder || ''"
              />
            </label>
            <div class="data-management-form__actions">
              <button type="submit" :disabled="saving">
                <span v-if="saving" class="data-management-saving-indicator"></span>
                {{ saving ? '保存中…' : (editingId ? '保存修改' : '新增记录') }}
              </button>
              <button type="button" class="secondary-button" @click="closeModal">取消</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- 处理中 / 结果弹窗 -->
    <Teleport to="body">
      <div v-if="resultModal.show" class="data-management-modal" @click.self="resultModal.state !== 'processing' && dismissResultModal()">
        <div class="data-management-modal__card data-management-result-card">
          <!-- 处理中 -->
          <template v-if="resultModal.state === 'processing'">
            <p class="data-management-result-status"><span class="data-management-spinner"></span> {{ resultModal.title }}</p>
          </template>

          <!-- 成功 -->
          <template v-else-if="resultModal.state === 'success'">
            <p class="data-management-result-status is-success">✓ {{ resultModal.title }}</p>
            <button type="button" class="data-management-result-btn" @click="dismissResultModal">确定</button>
          </template>

          <!-- 删除确认 -->
          <template v-else-if="resultModal.state === 'confirm'">
            <p class="data-management-result-status is-warning">{{ resultModal.title }}</p>
            <p v-if="resultModal.desc" class="data-management-result-desc">{{ resultModal.desc }}</p>
            <div class="data-management-result-actions">
              <button type="button" class="secondary-button" @click="dismissResultModal">取消</button>
              <button type="button" class="danger-button" @click="resultModal._onConfirm">确认删除</button>
            </div>
          </template>

          <!-- 失败 -->
          <template v-else-if="resultModal.state === 'error'">
            <p class="data-management-result-status is-error">✕ 操作失败</p>
            <p class="data-management-result-desc data-management-error">{{ resultModal.error }}</p>
            <div class="data-management-result-actions">
              <button type="button" class="secondary-button" @click="dismissResultModal">关闭</button>
              <button type="button" class="data-management-result-btn" @click="retryFromResult">返回修改</button>
            </div>
          </template>
        </div>
      </div>
    </Teleport>

    <!-- 同步视频播放弹窗 -->
    <Teleport to="body">
      <div v-if="videoPlayer.show" class="data-management-modal" @click.self="videoPlayer.show = false">
        <div class="data-management-modal__card" style="max-width:720px">
          <div class="data-management-modal__head">
            <h3>同步对齐视频 — {{ videoPlayer.subjectName }}</h3>
            <button type="button" class="link-button" @click="videoPlayer.show = false" aria-label="关闭">✕</button>
          </div>
          <div class="data-management-video-grid">
            <div v-if="videoPlayer.leftUrl" class="data-management-video-item">
              <p class="data-management-video-label">左机位</p>
              <video :src="videoPlayer.leftUrl" controls preload="metadata" class="data-management-video-player" />
            </div>
            <div v-if="videoPlayer.rightUrl" class="data-management-video-item">
              <p class="data-management-video-label">右机位</p>
              <video :src="videoPlayer.rightUrl" controls preload="metadata" class="data-management-video-player" />
            </div>
            <p v-if="!videoPlayer.leftUrl && !videoPlayer.rightUrl" style="color:#94a3b8;text-align:center;grid-column:1/-1">该记录暂无同步视频（分析发生于同步视频存储功能上线前）</p>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import {
  COLUMN_LABELS,
  LOOKUP_RESOURCES,
  RESOURCE_DEFINITIONS,
  createAdminRecord,
  deleteAdminRecord,
  listAdminRecords,
  updateAdminRecord,
} from '../services/adminData.js';
import { getCurrentAccountId, setCurrentAccountId } from '../stores/storage.js';

const resources = RESOURCE_DEFINITIONS;
const visibleResources = computed(() => resources.filter(r => !r.hidden));
const activeKey = ref(visibleResources.value[0]?.key || resources[0].key);
const items = ref([]);
const total = ref(0);
const loading = ref(false);
const saving = ref(false);
const deleting = ref(false);
const errorText = ref('');
const editingId = ref('');
const showModal = ref(false);
const modalError = ref('');
const viewMode = ref(false);
const accountId = ref(getCurrentAccountId());
const form = reactive({});
const lookups = reactive({});
const query = reactive({ keyword: '', limit: 20, offset: 0, filters: {} });

// 处理中 / 结果弹窗
const resultModal = reactive({
  show: false,
  state: 'processing',   // 'processing' | 'success' | 'error' | 'confirm'
  title: '',
  desc: '',
  error: '',
  _pendingAction: null,  // retry callback
  _onConfirm: null,      // confirm callback
});

// 视频播放弹窗
const videoPlayer = reactive({
  show: false,
  leftUrl: '',
  rightUrl: '',
  subjectName: '',
});

function openVideoPlayer(item) {
  videoPlayer.leftUrl = item.syncedLeftVideoUrl || '';
  videoPlayer.rightUrl = item.syncedRightVideoUrl || '';
  videoPlayer.subjectName = item.subjectName || '';
  videoPlayer.show = true;
}

const activeResource = computed(() => resources.find((resource) => resource.key === activeKey.value) || resources[0]);
const activeFilterFields = computed(() => activeResource.value.filterFields || []);
const visibleEnd = computed(() => Math.min(total.value, query.offset + items.value.length));

// 步伐九宫格序列
const ftSeq = ref([]);

function ftToggleCell(n) {
  ftSeq.value.push(n);
}

function defaultValueFor(field) {
  if (field.type === 'json') return '';
  return '';
}

function clearForm() {
  editingId.value = '';
  modalError.value = '';
  viewMode.value = false;
  ftSeq.value = [];
  for (const key of Object.keys(form)) delete form[key];
  const rk = activeResource.value.key;
  if (rk === 'footwork-types') {
    form.name = '';
    form.category = '';
    form.defaultStartCell = 5;
    form.description = '';
  } else if (rk === 'routes') {
    form.name = '';
    form.footworkTypeId = '';
    form.startCell = 5;
    form.defaultMs = '';
    form.actionRequirements = '';
  } else {
    for (const field of activeResource.value.fields) {
      form[field.key] = defaultValueFor(field);
    }
  }
}

function openCreateModal() {
  clearForm();
  showModal.value = true;
}

function closeModal() {
  showModal.value = false;
  clearForm();
}

function saveAccountId() {
  setCurrentAccountId(accountId.value);
}

function resetFilters() {
  for (const key of Object.keys(query.filters)) delete query.filters[key];
  for (const field of activeFilterFields.value) {
    query.filters[field.key] = '';
  }
}

function clearFilters() {
  resetFilters();
  resetAndLoad();
}

function normalizeItemLabel(item) {
  return item.name || item.displayName || item.username || item.code || item.id || item.jobId;
}

function fieldOptions(field) {
  if (field.options) return field.options;
  if (!field.lookup) return [];
  return (lookups[field.lookup] || []).map((item) => ({
    value: item.id || item.jobId,
    label: normalizeItemLabel(item),
  }));
}

function parseFieldValue(field, value) {
  if (value === '') return null;
  if (field.type === 'number') {
    const next = Number(value);
    if (Number.isNaN(next)) throw new Error(`${field.label} 必须是数字`);
    return next;
  }
  if (field.type === 'json') {
    if (!String(value || '').trim()) return null;
    try {
      return JSON.parse(value);
    } catch {
      throw new Error(`${field.label} 必须是合法 JSON`);
    }
  }
  return value;
}

function buildPayload() {
  const rk = activeResource.value.key;
  if (rk === 'footwork-types') {
    const code = 'ft_' + Date.now().toString(36);
    return {
      code,
      name: (form.name || '').trim(),
      category: form.category || null,
      default_start_cell: form.defaultStartCell || 5,
      default_sequence: ftSeq.value.length ? ftSeq.value.join('-') : String(form.defaultStartCell || 5),
      description: (form.description || '').trim() || null,
    };
  }
  if (rk === 'routes') {
    return {
      name: (form.name || '').trim(),
      footworkTypeId: form.footworkTypeId || null,
      startCell: form.startCell || 5,
      sequence: ftSeq.value.length ? ftSeq.value.join(',') : '',
      defaultMs: form.defaultMs || null,
      actionRequirements: (form.actionRequirements || '').trim() || null,
    };
  }
  const payload = {};
  for (const field of activeResource.value.fields) {
    payload[field.key] = parseFieldValue(field, form[field.key]);
  }
  return payload;
}

function displayValue(value) {
  if (value === null || value === undefined || value === '') return '-';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

async function loadLookups() {
  const lookupKeys = [...new Set(resources.flatMap((resource) => resource.fields.map((field) => field.lookup).filter(Boolean)))];
  for (const key of lookupKeys) {
    const resource = LOOKUP_RESOURCES[key];
    if (!resource) continue;
    try {
      const payload = await listAdminRecords(resource, { limit: 200, offset: 0 });
      lookups[key] = payload.items || [];
    } catch {
      lookups[key] = [];
    }
  }
}

async function loadResources() {
  loading.value = true;
  errorText.value = '';
  try {
    const payload = await listAdminRecords(activeResource.value, {
      keyword: query.keyword,
      limit: query.limit,
      offset: query.offset,
      ...query.filters,
    });
    items.value = payload.items || [];
    total.value = payload.total || items.value.length;
  } catch (error) {
    items.value = [];
    total.value = 0;
    errorText.value = error.message || '加载失败';
  } finally {
    loading.value = false;
  }
}

function resetAndLoad() {
  query.offset = 0;
  loadResources();
}

function switchResource(key) {
  activeKey.value = key;
  query.keyword = '';
  query.offset = 0;
  resetFilters();
  closeModal();
  loadResources();
}

function editResource(item) {
  editingId.value = item.id || item.jobId || '';
  modalError.value = '';
  const rk = activeResource.value.key;
  if (rk === 'footwork-types') {
    form.name = item.name || '';
    form.category = item.category || '';
    form.defaultStartCell = item.defaultStartCell || 5;
    form.description = item.description || '';
    const seq = item.defaultSequence || String(item.defaultStartCell || 5);
    ftSeq.value = seq.split('-').map(Number).filter(n => n >= 1 && n <= 9);
  } else if (rk === 'routes') {
    form.name = item.name || '';
    form.footworkTypeId = item.footworkTypeId || '';
    form.startCell = item.startCell || 5;
    form.defaultMs = item.defaultMs || '';
    form.actionRequirements = item.actionRequirements || '';
    ftSeq.value = (item.sequence || '').split(',').map(Number).filter(n => n >= 1 && n <= 9);
  } else {
    for (const field of activeResource.value.fields) {
      const value = item[field.key];
      form[field.key] = field.type === 'json' && value ? JSON.stringify(value, null, 2) : value ?? '';
    }
  }
  showModal.value = true;
}

function viewFootwork(item) {
  editResource(item);
  viewMode.value = true;
}

function _showResult(state, title, desc = '', error = '') {
  resultModal.show = true;
  resultModal.state = state;
  resultModal.title = title;
  resultModal.desc = desc;
  resultModal.error = error;
}

function _showProcessing(title) {
  _showResult('processing', title);
}

function _showSuccess(title, desc = '') {
  _showResult('success', title, desc);
}

function _showError(error) {
  _showResult('error', '', '', error);
}

function dismissResultModal() {
  resultModal.show = false;
  resultModal._pendingAction = null;
  resultModal._onConfirm = null;
}

function retryFromResult() {
  const action = resultModal._pendingAction;
  resultModal.show = false;
  resultModal._pendingAction = null;
  if (action) {
    // Reopen the form modal so user can fix and resubmit
    showModal.value = true;
  }
}

// 通知 SiteNav 刷新受试者列表
function _notifySubjectChanged() {
  if (activeResource.value.key === 'subjects') {
    window.dispatchEvent(new CustomEvent('subject-changed'));
  }
}

async function saveResource() {
  saving.value = true;
  modalError.value = '';
  try {
    const payload = buildPayload();
    const isEdit = !!editingId.value;

    // 关闭表单弹窗，显示处理中弹窗
    showModal.value = false;
    _showProcessing(isEdit ? '正在保存…' : '正在创建…');

    if (isEdit) {
      await updateAdminRecord(activeResource.value, editingId.value, payload);
    } else {
      await createAdminRecord(activeResource.value, payload);
    }

    // 同步依赖数据
    _notifySubjectChanged();
    await loadLookups();
    await loadResources();

    _showSuccess(isEdit ? '已更新' : '已新增');
    clearForm();
  } catch (error) {
    resultModal._pendingAction = true;
    _showError(error.message || '保存失败');
  } finally {
    saving.value = false;
  }
}

// 生成删除确认中的人类可读记录描述
function _deleteItemLabel(item) {
  const rk = activeResource.value.key;
  if (rk === 'subjects') {
    const parts = [item.name].filter(Boolean);
    if (item.hand) parts.push(item.hand);
    if (item.level) parts.push(item.level);
    return parts.join(' / ') || item.id;
  }
  if (rk === 'routes') {
    return item.name || item.sequence || item.id;
  }
  if (rk === 'training-configs') {
    const subName = (lookups['subjects'] || []).find(s => s.id === item.subjectId)?.name;
    return [subName, item.mode].filter(Boolean).join(' / ') || item.id;
  }
  if (rk === 'evaluations') {
    const subName = (lookups['subjects'] || []).find(s => s.id === item.subjectId)?.name;
    const grade = item.grade ? `评级 ${item.grade}` : '';
    return [subName, grade].filter(Boolean).join(' / ') || item.id;
  }
  if (rk === 'accounts') {
    return [item.username, item.account].filter(Boolean).join(' / ') || item.id;
  }
  if (rk === 'roles') return item.name || item.code || item.id;
  if (rk === 'permissions') return item.name || item.code || item.id;
  return item.name || item.displayName || item.username || item.code || item.id;
}

// 各资源类型的删除后果提示
const DELETE_CONSEQUENCES = {
  subjects: '删除受试者将同时删除其关联的所有训练配置、训练视频、分析任务、运动学数据和评估记录，此操作不可恢复。',
  routes: '删除路线将同时清除其包含的所有跑动步骤，引用此路线的训练配置将失去关联。',
  'training-configs': '删除训练配置后，关联的训练视频和分析任务仍保留，但将失去配置上下文。',
  evaluations: '删除评估记录不影响关联的运动学数据和分析任务。',
  accounts: '删除账号将同时移除其角色绑定，该账号将无法登录系统。',
  roles: '删除角色将同时移除所有账号与该角色的绑定关系。',
  permissions: '删除权限点将同时移除所有角色与该权限的绑定关系。',
};

function _deleteConsequence() {
  return DELETE_CONSEQUENCES[activeResource.value.key] || '此操作不可恢复，请确认后再操作。';
}

async function deleteResource(item) {
  const itemId = item.id || item.jobId;
  if (!itemId) return;

  const label = _deleteItemLabel(item);
  const consequence = _deleteConsequence();

  resultModal.show = true;
  resultModal.state = 'confirm';
  resultModal.title = `删除「${label}」？`;
  resultModal.desc = consequence;
  resultModal._onConfirm = async () => {
    resultModal.state = 'processing';
    resultModal.title = '正在删除…';
    resultModal.desc = '';

    deleting.value = true;
    errorText.value = '';
    try {
      await deleteAdminRecord(activeResource.value, itemId);

      // 同步依赖数据
      _notifySubjectChanged();
      await loadLookups();
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

function prevPage() {
  query.offset = Math.max(0, query.offset - query.limit);
  loadResources();
}

function nextPage() {
  query.offset += query.limit;
  loadResources();
}

onMounted(async () => {
  clearForm();
  resetFilters();
  await loadLookups();
  await loadResources();
});
</script>
