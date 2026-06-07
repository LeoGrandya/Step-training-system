<!-- MySQL v1 数据管理工作台：按 5 人分工管理核心业务资源。 -->
<template>
  <section class="page-stack data-management-page">
    <header class="data-management-header">
      <div>
        <p class="eyebrow">MySQL v1</p>
        <h1>数据管理</h1>
      </div>
      <label class="data-management-account">
        <span>权限账号 ID</span>
        <input v-model.trim="accountId" type="text" placeholder="acct_..." @change="saveAccountId" />
      </label>
      <button type="button" class="secondary-button" @click="loadResources">刷新</button>
    </header>

    <div class="data-management-layout">
      <aside class="data-management-sidebar" aria-label="资源类型">
        <button
          v-for="resource in resources"
          :key="resource.key"
          type="button"
          class="data-management-tab"
          :class="{ 'is-active': resource.key === activeKey }"
          @click="switchResource(resource.key)"
        >
          <span>{{ resource.title }}</span>
          <small>{{ resource.owner }}</small>
        </button>
      </aside>

      <section class="data-management-panel">
        <div class="data-management-panel__head">
          <div>
            <p class="eyebrow">{{ activeResource.owner }}</p>
            <h2>{{ activeResource.title }}</h2>
            <p>{{ activeResource.description }}</p>
          </div>
          <div class="data-management-search">
            <input v-model.trim="query.keyword" type="search" placeholder="关键字搜索" @keyup.enter="loadResources" />
            <select v-model.number="query.limit" @change="resetAndLoad">
              <option :value="10">10 条</option>
              <option :value="20">20 条</option>
              <option :value="50">50 条</option>
            </select>
            <button type="button" @click="resetAndLoad">查询</button>
          </div>
        </div>

        <div v-if="activeFilterFields.length" class="data-management-filters">
          <label v-for="field in activeFilterFields" :key="field.key" class="data-management-field">
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
          <button type="button" class="secondary-button" @click="clearFilters">清空筛选</button>
        </div>

        <p v-if="errorText" class="data-management-error">{{ errorText }}</p>

        <form
          v-if="activeResource.fields.length && (activeResource.creatable !== false || activeResource.editable !== false)"
          class="data-management-form"
          @submit.prevent="saveResource"
        >
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
            <button type="submit" :disabled="saving || activeResource.creatable === false && !editingId">
              {{ editingId ? '保存修改' : '新增记录' }}
            </button>
            <button type="button" class="secondary-button" @click="clearForm">清空</button>
            <span v-if="editingId" class="data-management-editing">正在编辑：{{ editingId }}</span>
          </div>
        </form>

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
                      v-if="activeResource.editable !== false"
                      type="button"
                      class="secondary-button"
                      @click="editResource(item)"
                    >
                      编辑
                    </button>
                    <button
                      v-if="activeResource.deletable !== false"
                      type="button"
                      class="danger-button"
                      @click="deleteResource(item)"
                    >
                      删除
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
const activeKey = ref(resources[0].key);
const items = ref([]);
const total = ref(0);
const loading = ref(false);
const saving = ref(false);
const errorText = ref('');
const editingId = ref('');
const accountId = ref(getCurrentAccountId());
const form = reactive({});
const lookups = reactive({});
const query = reactive({ keyword: '', limit: 20, offset: 0, filters: {} });

const activeResource = computed(() => resources.find((resource) => resource.key === activeKey.value) || resources[0]);
const activeFilterFields = computed(() => activeResource.value.filterFields || []);
const visibleEnd = computed(() => Math.min(total.value, query.offset + items.value.length));

function defaultValueFor(field) {
  if (field.type === 'json') return '';
  return '';
}

function clearForm() {
  editingId.value = '';
  for (const key of Object.keys(form)) delete form[key];
  for (const field of activeResource.value.fields) {
    form[field.key] = defaultValueFor(field);
  }
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
  clearForm();
  loadResources();
}

function editResource(item) {
  editingId.value = item.id || item.jobId || '';
  for (const field of activeResource.value.fields) {
    const value = item[field.key];
    form[field.key] = field.type === 'json' && value ? JSON.stringify(value, null, 2) : value ?? '';
  }
}

async function saveResource() {
  saving.value = true;
  errorText.value = '';
  try {
    const payload = buildPayload();
    if (editingId.value) {
      await updateAdminRecord(activeResource.value, editingId.value, payload);
    } else {
      await createAdminRecord(activeResource.value, payload);
    }
    clearForm();
    await loadLookups();
    await loadResources();
  } catch (error) {
    errorText.value = error.message || '保存失败';
  } finally {
    saving.value = false;
  }
}

async function deleteResource(item) {
  const itemId = item.id || item.jobId;
  if (!itemId) return;
  if (!window.confirm(`确认删除 ${itemId}？`)) return;
  errorText.value = '';
  try {
    await deleteAdminRecord(activeResource.value, itemId);
    await loadLookups();
    await loadResources();
  } catch (error) {
    errorText.value = error.message || '删除失败';
  }
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
