<template>
  <div class="membership-plans">
    <!-- ========== 1. 版本切换标签 ========== -->
    <nav class="version-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="version-tab"
        :class="{ active: activeTab === tab.key }"
        @click="switchTab(tab.key)"
      >
        {{ tab.label }}
      </button>
    </nav>

    <!-- ========== 2. 订阅套餐卡片 ========== -->
    <section class="plan-cards">
      <div
        v-for="plan in currentPlans"
        :key="plan.id"
        class="plan-card"
        :class="{ selected: selectedPlan === plan.id }"
        @click="selectedPlan = plan.id"
      >
        <span v-if="plan.badge" class="plan-badge">{{ plan.badge }}</span>
        <h3 class="plan-name">{{ plan.name }}</h3>
        <p class="plan-original">{{ plan.originalLabel }}</p>
        <p class="plan-price">
          <span class="price-currency">{{ plan.currency }}</span>
          <span class="price-value">{{ plan.price }}</span>
          <span class="price-unit"> /{{ plan.unit }}</span>
        </p>
      </div>
    </section>

    <p class="plan-hint">所有版本均支持双机位视频分析，套餐到期后未使用时长不结转</p>

    <!-- ========== 3. 支付交互区 ========== -->
    <section class="payment-area">
      <button class="pay-button" :disabled="!agreed" @click="handlePay">
        确认协议并以 {{ currentPriceText }} 支付
      </button>

      <label class="agreement-row">
        <span class="checkbox-circle" :class="{ checked: agreed }" @click="toggleAgree">
          <svg v-if="agreed" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </span>
        <span class="agreement-text">
          开通会员代表接受<span class="agreement-link" @click.stop="openAgreement">《会员服务协议》</span>（含自动续费条款）
        </span>
      </label>
    </section>

    <!-- ========== 4. 会员特权对比表格 ========== -->
    <section class="privilege-section">
      <h2 class="privilege-title">会员特权对比</h2>
      <div class="privilege-table-wrap">
        <table class="privilege-table">
          <thead>
            <tr>
              <th class="col-feature"></th>
              <th
                v-for="tab in tabs"
                :key="tab.key"
                class="col-plan"
                :class="{ 'col-current': activeTab === tab.key }"
              >
                {{ tab.label }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in tableRows" :key="row.label">
              <td class="col-feature">{{ row.label }}</td>
              <td
                v-for="tab in tabs"
                :key="tab.key"
                class="col-plan"
                :class="{ 'col-current': activeTab === tab.key }"
              >
                <span v-if="row[tab.key] === '✓'" class="check-mark">✓</span>
                <span v-else>{{ row[tab.key] }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

// --- 版本切换标签 ---
const tabs = [
  { key: 'basic', label: '基础版' },
  { key: 'pro', label: '专业版' },
  { key: 'topup', label: '充值包' },
]
const activeTab = ref('basic')

// --- 各版本的套餐方案 ---
const plansMap = {
  basic: [
    { id: 'monthly', name: '连续包月', badge: '最推荐', original: '¥49.9', originalLabel: '¥49.9/月', currency: '¥', price: '49.9', unit: '月' },
    { id: 'quarterly', name: '连续包季', badge: '', original: '¥39.9', originalLabel: '¥39.9/月', currency: '¥', price: '120', unit: '季' },
    { id: 'yearly', name: '连续包年', badge: '', original: '¥29.9', originalLabel: '¥29.9/月', currency: '¥', price: '480', unit: '年' },
  ],
  pro: [
    { id: 'monthly', name: '连续包月', badge: '最推荐', original: '¥79.9', originalLabel: '¥79.9/月', currency: '¥', price: '79.9', unit: '月' },
    { id: 'quarterly', name: '连续包季', badge: '', original: '¥69.9', originalLabel: '¥69.9/月', currency: '¥', price: '210', unit: '季' },
    { id: 'yearly', name: '连续包年', badge: '', original: '¥59.9', originalLabel: '¥59.9/月', currency: '¥', price: '720', unit: '年' },
  ],
  topup: [
    { id: 'monthly', name: '充值包小', badge: '', original: '¥9.9', originalLabel: '¥9.9', currency: '¥', price: '9.9', unit: '次' },
    { id: 'quarterly', name: '充值包中', badge: '最推荐', original: '¥19.9', originalLabel: '¥19.9', currency: '¥', price: '19.9', unit: '次' },
    { id: 'yearly', name: '充值包大', badge: '', original: '¥29.9', originalLabel: '¥29.9', currency: '¥', price: '29.9', unit: '次' },
  ],
}

// --- 当前选中 ---
const selectedPlan = ref('monthly')
const agreed = ref(false)

// --- 当前版本的套餐列表 ---
const currentPlans = computed(() => plansMap[activeTab.value] || plansMap.basic)

// --- 当前选中的价格文本 ---
const currentPriceText = computed(() => {
  const plan = currentPlans.value.find(p => p.id === selectedPlan.value)
  if (!plan) return '¥ 49.9'
  return `¥ ${plan.price}`
})

// --- 特权对比表数据 ---
const tableRows = [
  { label: '双机位视频同步', basic: '音频互相关自动对齐', pro: '音频互相关 + 蜂鸣器精对齐', topup: '音频互相关自动对齐' },
  { label: '3D 姿态重建', basic: 'MediaPipe + 双目三角测量', pro: 'MediaPipe + 双目三角测量', topup: 'MediaPipe + 双目三角测量' },
  { label: '分析档位', basic: '快速', pro: '快速 / 均衡 / 质量', topup: '快速 / 均衡' },
  { label: '单次视频时长', basic: '最长 3 分钟', pro: '最长 15 分钟', topup: '最长 5 分钟' },
  { label: '运动学指标', basic: 'COM 速度、位移、步法分段', pro: '全部指标（力矩、做功、KLI、DSO 等）', topup: '全部指标（单次有效）' },
  { label: '报告图表', basic: '5 项基础图表', pro: '全部 12 项图表', topup: '全部 12 项图表（单次）' },
  { label: '关节生物力学', basic: '/', pro: '髋/膝/踝角度、力矩、功率', topup: '✓' },
  { label: '数据导出', basic: 'CSV', pro: 'CSV + XLSX + 图表 PNG', topup: 'CSV' },
  { label: '历史记录', basic: '保留 7 天', pro: '永久保留', topup: '保留 30 天' },
  { label: '自定义参数', basic: '/', pro: '帧采样、滤波档位可调', topup: '/' },
  { label: '智能缓存加速', basic: '/', pro: 'ArtifactCache 阶段复用', topup: '/' },
]

// --- 版本切换时重置选中卡片 ---
const switchTab = (key) => {
  activeTab.value = key
  selectedPlan.value = plansMap[key][0].id
}

// --- 协议勾选 ---
const toggleAgree = () => {
  agreed.value = !agreed.value
}

// --- 支付 ---
const handlePay = () => {
  if (!agreed.value) return
  alert(`确认支付 ${currentPriceText.value}`)
}

// --- 打开协议 ---
const openAgreement = () => {
  alert('《会员服务协议》内容')
}
</script>

<style scoped>
/* ==================== 版本标签 ==================== */
.version-tabs {
  display: flex;
  gap: 0;
  margin: 0 0 20px;
  background: #fff;
  border-radius: 12px;
  padding: 4px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}

.version-tab {
  flex: 1;
  padding: 10px 0;
  border: none;
  background: transparent;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s;
}

.version-tab.active {
  background: #fff;
  color: #2563eb;
  font-weight: 700;
  box-shadow: 0 0 0 2px #2563eb, 0 2px 8px rgba(37, 99, 235, 0.15);
}

/* ==================== 套餐卡片 ==================== */
.plan-cards {
  display: flex;
  gap: 10px;
  margin-bottom: 8px;
}

.plan-card {
  flex: 1;
  position: relative;
  background: #fff;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px 10px 14px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

.plan-card:hover {
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.1);
}

.plan-card.selected {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2), 0 4px 16px rgba(37, 99, 235, 0.12);
}

.plan-badge {
  position: absolute;
  top: -1px;
  left: 50%;
  transform: translateX(-50%);
  background: #f97316;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 12px;
  border-radius: 0 0 8px 8px;
  white-space: nowrap;
}

.plan-name {
  margin: 4px 0 4px;
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

.plan-original {
  margin: 0 0 6px;
  font-size: 12px;
  color: #94a3b8;
  text-decoration: line-through;
}

.plan-price {
  margin: 0;
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 1px;
}

.price-currency {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.price-value {
  font-size: 28px;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.1;
}

.price-unit {
  font-size: 13px;
  font-weight: 500;
  color: #64748b;
}

.plan-hint {
  text-align: center;
  font-size: 12px;
  color: #94a3b8;
  margin: 8px 0 20px;
}

/* ==================== 支付区域 ==================== */
.payment-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  margin-bottom: 28px;
}

.pay-button {
  width: 100%;
  padding: 14px 0;
  border: none;
  background: #2563eb;
  color: #fff;
  font-size: 17px;
  font-weight: 700;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.35);
}

.pay-button:hover:not(:disabled) {
  background: #1d4ed8;
  box-shadow: 0 6px 20px rgba(37, 99, 235, 0.45);
}

.pay-button:disabled {
  background: #bfdbfe;
  cursor: not-allowed;
  box-shadow: none;
}

.agreement-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}

.checkbox-circle {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  border: 2px solid #2563eb;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 1px;
  transition: all 0.2s;
  color: #2563eb;
}

.checkbox-circle.checked {
  background: #2563eb;
  color: #fff;
}

.agreement-text {
  font-size: 12px;
  color: #64748b;
  line-height: 1.6;
}

.agreement-link {
  color: #2563eb;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
}

.agreement-link:hover {
  text-decoration: underline;
}

/* ==================== 特权对比表格 ==================== */
.privilege-section {
  background: #fff;
  border-radius: 12px;
  padding: 20px 16px;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.06);
}

.privilege-title {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 16px;
  text-align: center;
}

.privilege-table-wrap {
  overflow-x: auto;
}

.privilege-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.privilege-table th,
.privilege-table td {
  padding: 11px 8px;
  text-align: center;
  border-bottom: 1px solid #f1f5f9;
}

.privilege-table thead th {
  font-weight: 600;
  color: #64748b;
  font-size: 14px;
  border-bottom: 2px solid #e2e8f0;
}

.col-feature {
  text-align: left;
  color: #475569;
  font-weight: 500;
  white-space: nowrap;
  min-width: 80px;
}

.col-plan.col-current {
  color: #2563eb;
  font-weight: 700;
}

.col-plan .check-mark {
  color: #2563eb;
  font-weight: 700;
  font-size: 16px;
}

/* ==================== 响应式 ==================== */
@media (min-width: 640px) {
  .plan-card {
    padding: 20px 14px 18px;
  }

  .price-value {
    font-size: 32px;
  }
}
</style>
