<!-- 通用资源表格：关键字搜索 + 筛选面板(左覆盖) + 双层表头 + 数据行 + 分页。 -->
<template>
  <section class="data-management-panel">
    <div class="data-management-panel__head">
      <div>
        <h2>{{ resource.title }}</h2>
        <p>{{ resource.description }}</p>
      </div>
    </div>

    <!-- 关键字搜索条（仅输入框） -->
    <div class="dm-search-bar">
      <input
        v-model.trim="localKeyword"
        type="search"
        placeholder="搜索关键字..."
        @keyup.enter="emitSearch"
        @input="onKeywordInput"
      />
    </div>

    <!-- 筛选折叠条 -->
    <button
      type="button"
      class="dm-filter-toggle"
      :class="{ 'is-open': filterOpen }"
      @click="filterOpen = !filterOpen"
    >
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
        <path d="M2 3h10L8.5 7.2v4.3L5.5 9.8V7.2L2 3Z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/>
      </svg>
      筛选（默认）
      <span v-if="activeFilterSummary" class="dm-filter-toggle__summary">— {{ activeFilterSummary }}</span>
      <span class="dm-filter-toggle__arrow">&#9650;</span>
    </button>

    <!-- 筛选面板区：relative 锚点 + absolute 左覆盖面板 -->
    <div class="dm-table-zone">
      <!-- 筛选覆盖面板 -->
      <div v-if="hasFilterFields" class="dm-filter-overlay" :class="{ 'is-open': filterOpen }">
        <div class="dm-filter-inner">
          <div v-for="group in resolvedFilterGroups" :key="group.key" class="dm-filter-group">
            <div class="dm-filter-group__label">{{ group.label }}</div>
            <div class="dm-filter-group__chips">
              <span
                v-for="opt in visibleOptions(group)"
                :key="opt.value"
                class="dm-filter-chip"
                :class="{ 'is-active': (activeFilters[group.key] || '') === opt.value }"
                @click="toggleFilter(group.key, opt.value)"
              >
                {{ opt.label }}<span class="dm-filter-chip__count">（{{ opt.count }}）</span>
              </span>
              <button
                v-if="group.truncated"
                type="button"
                class="dm-filter-chip dm-filter-chip--more"
                @click="group.expanded = !group.expanded"
              >
                {{ group.expanded ? '收起' : `+ ${group.truncated} 更多` }}
              </button>
            </div>
          </div>

          <div v-if="!hasFilterFields" style="color:#94a3b8;font-size:0.8125rem;padding:8px 0;">
            此资源无筛选项
          </div>

          <div class="dm-filter-actions">
            <button type="button" class="dm-btn-reset" @click="resetFilters">恢复默认</button>
            <button type="button" class="dm-btn-apply" @click="applyFilters">确认</button>
          </div>
        </div>
      </div>

      <!-- 新增按钮 -->
      <button
        v-if="resource.fields.length && resource.creatable !== false"
        type="button"
        class="data-management-add-btn"
        @click="$emit('create')"
      >
        + 新增记录
      </button>

      <p v-if="errorText" class="data-management-error">{{ errorText }}</p>

      <!-- 表格卡片 -->
      <div class="dm-table-card">
        <!-- 双层表头 -->
        <div class="dm-table-header">
          <!-- 第一层：排序按钮 -->
          <div class="dm-header-sort-row" :style="{ gridTemplateColumns: gridColumns }">
            <button
              v-for="col in resource.columns"
              :key="col.key"
              type="button"
              class="dm-sort-btn"
              :class="{
                'is-active': localSortBy === col.key,
                'is-desc': localSortBy === col.key && localSortOrder === 'desc'
              }"
              :disabled="!col.sortable"
              @click="toggleSort(col)"
            >
              {{ col.label || COLUMN_LABELS[col.key] || col.key }}
              <span v-if="col.sortable" class="dm-sort-arrows">&#9650;<br>&#9660;</span>
            </button>
          </div>
          <!-- 第二层：列名 -->
          <div class="dm-header-label-row" :style="{ gridTemplateColumns: gridColumns }">
            <div v-for="col in resource.columns" :key="col.key" class="dm-header-label-cell">
              {{ col.label || COLUMN_LABELS[col.key] || col.key }}
            </div>
          </div>
        </div>

        <!-- 骨架屏 -->
        <template v-if="loadingState === 'initial'">
          <div
            v-for="i in 5" :key="'skel-' + i"
            class="dm-data-row" :style="{ gridTemplateColumns: gridColumns }"
          >
            <div v-for="col in resource.columns" :key="col.key" class="dm-data-cell">
              <div class="dm-skeleton" />
            </div>
          </div>
        </template>

        <!-- 加载中（无旧数据） -->
        <template v-else-if="!items.length && (loadingState === 'refreshing' || loadingState === 'paginating')">
          <div class="dm-data-row" :style="{ gridTemplateColumns: gridColumns }">
            <div class="dm-data-cell" style="grid-column:1/-1;justify-content:center;padding:32px;color:#94a3b8;">
              加载中...
            </div>
          </div>
        </template>

        <!-- 空 -->
        <template v-else-if="!items.length && loadingState === 'idle'">
          <div class="dm-data-row" :style="{ gridTemplateColumns: gridColumns }">
            <div class="dm-data-cell" style="grid-column:1/-1;justify-content:center;padding:40px;color:#94a3b8;">
              暂无数据
            </div>
          </div>
        </template>

        <!-- 数据行 -->
        <div
          v-for="item in items"
          v-else
          :key="item.id || item.jobId"
          class="dm-data-row"
          :class="{ 'is-dimmed': loadingState === 'paginating' }"
          :style="{ gridTemplateColumns: gridColumns }"
        >
          <div v-for="col in resource.columns" :key="col.key" class="dm-data-cell">
            {{ displayValue(item[col.key]) }}
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div class="dm-pagination">
        <span class="dm-pagination__info">共 {{ total }} 条，当前 {{ visibleStart }} - {{ visibleEnd }}</span>
        <div class="dm-pagination__controls">
          <select v-model.number="localLimit" class="dm-pagination__size" @change="onLimitChange">
            <option :value="10">10 条/页</option>
            <option :value="20">20 条/页</option>
            <option :value="50">50 条/页</option>
          </select>
          <button type="button" class="dm-page-btn" :disabled="localOffset <= 0" @click="goPrev">上一页</button>
          <template v-for="p in pageNumbers" :key="p">
            <button
              v-if="p !== '...'"
              type="button"
              class="dm-page-btn"
              :class="{ 'is-active': p === currentPage }"
              @click="goPage(p)"
            >{{ p }}</button>
            <span v-else class="dm-pagination__ellipsis">…</span>
          </template>
          <button type="button" class="dm-page-btn" :disabled="visibleEnd >= total" @click="goNext">下一页</button>
          <label class="dm-pagination__jump">
            <span>跳转</span>
            <input
              v-model="jumpPage"
              type="number"
              :min="1"
              :max="totalPages"
              @keyup.enter="goPage(jumpPage)"
            />
            <span>页</span>
          </label>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { COLUMN_LABELS } from '../../services/adminData.js';

const props = defineProps({
  resource: { type: Object, required: true },
  items: { type: Array, default: () => [] },
  total: { type: Number, default: 0 },
  loadingState: { type: String, default: 'idle' },
  errorText: { type: String, default: '' },
  deleting: { type: Boolean, default: false },
  // 后端返回的 filter 聚合数据
  filters: { type: Array, default: () => [] },
  // 外部初始查询参数
  initialKeyword: { type: String, default: '' },
  initialLimit: { type: Number, default: 20 },
  initialOffset: { type: Number, default: 0 },
  initialFilters: { type: Object, default: () => ({}) },
  initialSortBy: { type: String, default: '' },
  initialSortOrder: { type: String, default: 'asc' },
});

const emit = defineEmits(['search', 'create', 'edit', 'delete', 'view-video', 'view-footwork']);

// ── Local state ──
const localKeyword = ref(props.initialKeyword);
const localLimit = ref(props.initialLimit);
const localOffset = ref(props.initialOffset);
const activeFilters = ref({ ...props.initialFilters });
const localSortBy = ref(props.initialSortBy);
const localSortOrder = ref(props.initialSortOrder);
const filterOpen = ref(false);
const jumpPage = ref(1);

// Debounce timer for keyword input
let keywordTimer = null;

// ── Computed ──
const gridColumns = computed(() => {
  return props.resource.columns.map(() => '1fr').join(' ');
});

const visibleStart = computed(() => Math.min(props.total, props.items.length ? localOffset.value + 1 : 0));
const visibleEnd = computed(() => Math.min(props.total, localOffset.value + props.items.length));

const activeFilterSummary = computed(() => {
  if (!props.filters.length) return '';
  const parts = [];
  for (const [key, val] of Object.entries(activeFilters.value)) {
    if (!val) continue;
    const group = props.filters.find(f => f.key === key);
    if (!group) continue;
    const opt = group.options.find(o => o.value === val);
    parts.push(opt ? opt.label : val);
  }
  return parts.join('、');
});

const hasFilterFields = computed(() => props.resource.filterFields && props.resource.filterFields.length > 0);

// Merge backend filter aggregations with local expanded state and truncation
const _expandedState = ref({});

const resolvedFilterGroups = computed(() => {
  if (!props.filters.length) {
    // Fallback: build from resource.filterFields without counts
    return (props.resource.filterFields || []).map(ff => ({
      key: ff.key,
      label: ff.label,
      options: [{ value: '', label: '全部', count: 0 }],
      truncated: 0,
      expanded: _expandedState.value[ff.key] || false,
    }));
  }
  return props.filters.map(group => {
    const totalOpts = group.options.length;
    const truncated = totalOpts > 9 ? totalOpts - 8 : 0;
    return {
      ...group,
      truncated,
      expanded: _expandedState.value[group.key] || false,
    };
  });
});

function visibleOptions(group) {
  if (!group.truncated || group.expanded) return group.options;
  return group.options.slice(0, 8);
}

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / localLimit.value)));
const currentPage = computed(() => Math.floor(localOffset.value / localLimit.value) + 1);

const pageNumbers = computed(() => {
  const total = totalPages.value;
  const current = currentPage.value;
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const pages = [1];
  if (current > 3) pages.push('...');
  const start = Math.max(2, current - 1);
  const end = Math.min(total - 1, current + 1);
  for (let i = start; i <= end; i++) pages.push(i);
  if (current < total - 2) pages.push('...');
  pages.push(total);
  return pages;
});

// ── Methods ──
function displayValue(value) {
  if (value === null || value === undefined || value === '') return '-';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function toggleFilter(key, value) {
  activeFilters.value = { ...activeFilters.value, [key]: value };
  // 即时生效 — 筛选变化直接触发搜索
  localOffset.value = 0;
  emitSearch();
}

function resetFilters() {
  const next = {};
  for (const key of Object.keys(activeFilters.value)) {
    next[key] = '';
  }
  activeFilters.value = next;
  localOffset.value = 0;
  emitSearch();
}

function applyFilters() {
  filterOpen.value = false;
  // 筛选已经是即时生效的，这里只关闭面板
}

function toggleSort(col) {
  if (!col.sortable) return;
  if (localSortBy.value === col.key) {
    localSortOrder.value = localSortOrder.value === 'asc' ? 'desc' : 'asc';
  } else {
    localSortBy.value = col.key;
    localSortOrder.value = 'asc';
  }
  localOffset.value = 0;
  emitSearch();
}

function onKeywordInput() {
  clearTimeout(keywordTimer);
  keywordTimer = setTimeout(() => {
    localOffset.value = 0;
    emitSearch();
  }, 350);
}

function emitSearch() {
  emit('search', {
    keyword: localKeyword.value,
    limit: localLimit.value,
    offset: localOffset.value,
    filters: { ...activeFilters.value },
    sortBy: localSortBy.value,
    sortOrder: localSortOrder.value,
  });
}

function onLimitChange() {
  localOffset.value = 0;
  emitSearch();
}

function goPrev() {
  localOffset.value = Math.max(0, localOffset.value - localLimit.value);
  emitPageChange();
}
function goNext() {
  localOffset.value += localLimit.value;
  emitPageChange();
}
function goPage(p) {
  const page = Number(p);
  if (isNaN(page) || page < 1 || page > totalPages.value) return;
  localOffset.value = (page - 1) * localLimit.value;
  emitPageChange();
}
function emitPageChange() {
  emit('search', {
    keyword: localKeyword.value,
    limit: localLimit.value,
    offset: localOffset.value,
    filters: { ...activeFilters.value },
    sortBy: localSortBy.value,
    sortOrder: localSortOrder.value,
  });
}

// ── Watch resource key change → reset all local state ──
watch(() => props.resource.key, () => {
  localKeyword.value = '';
  localOffset.value = 0;
  activeFilters.value = {};
  localSortBy.value = '';
  localSortOrder.value = 'asc';
  filterOpen.value = false;
  _expandedState.value = {};
});

// Sync external initial props inward (for parent-driven resets)
watch(() => props.initialFilters, (val) => {
  activeFilters.value = { ...val };
}, { deep: true });
watch(() => props.initialSortBy, (val) => { localSortBy.value = val; });
watch(() => props.initialSortOrder, (val) => { localSortOrder.value = val; });
watch(() => props.initialKeyword, (val) => { localKeyword.value = val; });
watch(() => props.initialLimit, (val) => { localLimit.value = val; });
watch(() => props.initialOffset, (val) => { localOffset.value = val; });
</script>
