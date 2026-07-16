<template>
  <div class="dashboard-page" v-loading="loading">
    <!-- ── 页面标题 ── -->
    <div class="page-header">
      <h2>数据看板</h2>
    </div>

    <!-- ==================== 总览统计卡片 ==================== -->
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-total">
          <div class="stat-card__inner">
            <div class="stat-card__icon">
              <el-icon :size="32"><VideoCamera /></el-icon>
            </div>
            <div class="stat-card__content">
              <div class="stat-card__value">{{ overview.total_detections || 0 }}</div>
              <div class="stat-card__title">总检测次数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-fire">
          <div class="stat-card__inner">
            <div class="stat-card__icon">
              <el-icon :size="32"><Sunny /></el-icon>
            </div>
            <div class="stat-card__content">
              <div class="stat-card__value">{{ overview.fire_detected || 0 }}</div>
              <div class="stat-card__title">火焰检出次数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-smoke">
          <div class="stat-card__inner">
            <div class="stat-card__icon">
              <el-icon :size="32"><Cloudy /></el-icon>
            </div>
            <div class="stat-card__content">
              <div class="stat-card__value">{{ overview.smoke_detected || 0 }}</div>
              <div class="stat-card__title">烟雾检出次数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-warning">
          <div class="stat-card__inner">
            <div class="stat-card__icon">
              <el-icon :size="32"><WarningFilled /></el-icon>
            </div>
            <div class="stat-card__content">
              <div class="stat-card__value">{{ overview.warning_count || 0 }}</div>
              <div class="stat-card__title">预警次数</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ==================== 图表区域 ==================== -->
    <el-row :gutter="20">
      <!-- 火情等级分布饼图 -->
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="chart-card__header">
              <span><el-icon><PieChart /></el-icon> 火情等级分布</span>
              <el-tag size="small" type="info">safe / notice / warning / danger</el-tag>
            </div>
          </template>
          <div ref="pieChartRef" class="chart-container" v-loading="pieLoading"></div>
        </el-card>
      </el-col>
      <!-- 近7天检测趋势折线图 -->
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="chart-card__header">
              <span><el-icon><TrendCharts /></el-icon> 检测趋势（近7天）</span>
              <el-tag size="small" type="info">检测次数</el-tag>
            </div>
          </template>
          <div ref="lineChartRef" class="chart-container" v-loading="lineLoading"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ==================== 场景分布柱状图 ==================== -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="24">
        <el-card class="chart-card">
          <template #header>
            <div class="chart-card__header">
              <span><el-icon><Histogram /></el-icon> 场景分布</span>
              <el-tag size="small" type="info">各监测点检测次数</el-tag>
            </div>
          </template>
          <div ref="barChartRef" class="chart-container" v-loading="barLoading"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
/**
 * DashboardPage.vue — 数据看板页面
 *
 * 功能说明：
 *   - 顶部 4 张总览统计卡片：总检测次数、火焰检出次数、烟雾检出次数、预警次数
 *   - 左侧火情等级分布饼图（ECharts 实现）：safe / notice / warning / danger 四级
 *   - 右侧近 7 天检测趋势折线图（ECharts 实现）
 *   - 火灾方向适配：所有统计和图表面向 fire/smoke 火灾场景
 *
 * 火情等级定义：
 *   safe     — 安全：无火情
 *   notice   — 关注：检测到烟雾，需持续观察
 *   warning  — 警告：检测到火焰，需立即核实
 *   danger   — 危险：火势较大，需立即处置
 */
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import {
  VideoCamera,
  Sunny,
  Cloudy,
  WarningFilled,
  PieChart,
  TrendCharts,
  Histogram
} from '@element-plus/icons-vue'
import { getOverview, getFireLevelDistribution, getTrend, getSceneDistribution } from '@/api/stats'
import * as echarts from 'echarts'

// ---- 响应式数据 ----

/** 页面整体加载状态 */
const loading = ref(false)

/** 总览统计数据 */
const overview = ref({})

/** 饼图加载状态 */
const pieLoading = ref(false)

/** 折线图加载状态 */
const lineLoading = ref(false)

/** 饼图 DOM 引用 */
const pieChartRef = ref(null)

/** 折线图 DOM 引用 */
const lineChartRef = ref(null)

/** 柱状图 DOM 引用 */
const barChartRef = ref(null)

/** 柱状图加载状态 */
const barLoading = ref(false)

/** ECharts 实例引用，用于组件销毁时释放 */
let pieChartInstance = null
let lineChartInstance = null
let barChartInstance = null

// ---- 火情等级映射表 ----

/** 火情等级 → 中文标签 */
const FIRE_LEVEL_LABEL_MAP = {
  safe: '安全',
  notice: '关注',
  warning: '警告',
  danger: '危险'
}

/** 火情等级 → 饼图颜色 */
const FIRE_LEVEL_COLOR_MAP = {
  safe: '#67c23a',    // 绿色 — 安全
  notice: '#409eff',   // 蓝色 — 关注
  warning: '#e6a23c',  // 橙色 — 警告
  danger: '#f56c6c'    // 红色 — 危险
}

// ---- 工具函数 ----

/**
 * 将火情等级转换为中文标签
 * @param {string} level - 火情等级（safe/notice/warning/danger）
 * @returns {string} 中文标签
 */
function fireLevelLabel(level) {
  return FIRE_LEVEL_LABEL_MAP[level] || '未知'
}

/**
 * 获取火情等级对应的颜色
 * @param {string} level - 火情等级（safe/notice/warning/danger）
 * @returns {string} 颜色值
 */
function fireLevelColor(level) {
  return FIRE_LEVEL_COLOR_MAP[level] || '#909399'
}

// ---- 生命周期 ----

onMounted(async () => {
  // 并行加载所有数据
  await Promise.all([
    fetchOverview(),
    initCharts()
  ])
  // 图表初始化后拉取图表数据
  await Promise.all([
    fetchPieData(),
    fetchLineData(),
    fetchBarData()
  ])
  // 监听窗口大小变化，自动调整图表尺寸
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  // 移除窗口大小监听
  window.removeEventListener('resize', handleResize)
  // 销毁 ECharts 实例，释放内存
  if (pieChartInstance) {
    pieChartInstance.dispose()
    pieChartInstance = null
  }
  if (lineChartInstance) {
    lineChartInstance.dispose()
    lineChartInstance = null
  }
  if (barChartInstance) {
    barChartInstance.dispose()
    barChartInstance = null
  }
})

// ---- 数据获取 ----

/** 获取总览统计数据 */
async function fetchOverview() {
  try {
    const res = await getOverview()
    overview.value = res.data || {}
  } catch (e) {
    ElMessage.error('获取总览数据失败')
  }
}

/** 获取火情等级分布数据并渲染饼图 */
async function fetchPieData() {
  pieLoading.value = true
  try {
    const res = await getFireLevelDistribution()
    const distData = (res.data || []).map(d => ({
      name: fireLevelLabel(d.fire_level),
      value: d.count,
      itemStyle: { color: fireLevelColor(d.fire_level) }
    }))
    renderPieChart(distData)
  } catch (e) {
    console.error('获取火情等级分布失败', e)
  } finally {
    pieLoading.value = false
  }
}

/** 获取近 7 天检测趋势数据并渲染折线图 */
async function fetchLineData() {
  lineLoading.value = true
  try {
    const res = await getTrend({ days: 7 })
    const trendData = res.data || []
    renderLineChart(trendData)
  } catch (e) {
    console.error('获取检测趋势失败', e)
  } finally {
    lineLoading.value = false
  }
}

// ---- ECharts 初始化 ----

/** 初始化 ECharts 实例 */
async function initCharts() {
  await nextTick()
  if (pieChartRef.value) {
    pieChartInstance = echarts.init(pieChartRef.value)
  }
  if (lineChartRef.value) {
    lineChartInstance = echarts.init(lineChartRef.value)
  }
  if (barChartRef.value) {
    barChartInstance = echarts.init(barChartRef.value)
  }
}

// ---- ECharts 渲染 ----

/**
 * 渲染火情等级分布饼图
 * 使用环形饼图，safe/notice/warning/danger 四级分别用绿/蓝/橙/红色表示
 * @param {Array} data - 饼图数据 [{name, value, itemStyle}]
 */
function renderPieChart(data) {
  if (!pieChartInstance) return

  // 如果所有数据都为 0，展示空状态提示
  const hasData = data.some(d => d.value > 0)

  pieChartInstance.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} 次 ({d}%)'
    },
    legend: {
      bottom: '5%',
      itemWidth: 12,
      itemHeight: 12
    },
    series: [{
      type: 'pie',
      radius: hasData ? ['45%', '72%'] : ['0%', '0%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 4,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: {
        show: hasData,
        formatter: '{b}\n{d}%'
      },
      emphasis: {
        label: {
          fontSize: 16,
          fontWeight: 'bold'
        },
        scaleSize: 10
      },
      data: hasData ? data : [{ name: '暂无数据', value: 1, itemStyle: { color: '#e0e0e0' } }]
    }]
  })
}

/**
 * 渲染近 7 天检测趋势折线图
 * 使用面积折线图，展示每日检测次数变化趋势
 * @param {Array} data - 趋势数据 [{date, count}]
 */
function renderLineChart(data) {
  if (!lineChartInstance) return

  const dates = data.map(d => d.date)
  const counts = data.map(d => d.count)

  lineChartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: '{b}<br/>检测次数：<b>{c}</b> 次'
    },
    grid: {
      top: 20,
      left: 10,
      right: 20,
      bottom: 10,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#ccc' } },
      axisLabel: {
        color: '#666',
        formatter: (value) => {
          // 日期格式化：只显示月-日
          return value.substring(5)
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '检测次数',
      nameTextStyle: { color: '#666' },
      minInterval: 1,
      splitLine: { lineStyle: { type: 'dashed', color: '#e8e8e8' } }
    },
    series: [{
      type: 'line',
      data: counts,
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      lineStyle: { color: '#e74c3c', width: 2.5 },
      itemStyle: { color: '#e74c3c' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(231, 76, 60, 0.3)' },
          { offset: 1, color: 'rgba(231, 76, 60, 0.02)' }
        ])
      },
      markLine: {
        silent: true,
        data: [{ type: 'average', name: '平均值' }],
        lineStyle: { color: '#e6a23c', type: 'dashed' }
      }
    }]
  })
}

// ---- 场景分布柱状图 ----

/** 获取场景分布数据并渲染柱状图 */
async function fetchBarData() {
  barLoading.value = true
  try {
    const res = await getSceneDistribution()
    const distData = (res.data || []).map(d => ({
      name: d.scene_name || d.name || '未知',
      value: d.count || d.detection_count || 0
    }))
    renderBarChart(distData)
  } catch (e) {
    console.error('获取场景分布失败', e)
  } finally {
    barLoading.value = false
  }
}

/**
 * 渲染场景分布柱状图
 * @param {Array} data - 场景分布数据 [{name, value}]
 */
function renderBarChart(data) {
  if (!barChartInstance) return

  const names = data.map(d => d.name)
  const values = data.map(d => d.value)

  barChartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: '{b}<br/>检测次数：<b>{c}</b> 次'
    },
    grid: {
      top: 20,
      left: 10,
      right: 20,
      bottom: 30,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: names,
      axisLabel: {
        color: '#666',
        rotate: names.length > 6 ? 30 : 0
      },
      axisLine: { lineStyle: { color: '#ccc' } }
    },
    yAxis: {
      type: 'value',
      name: '检测次数',
      nameTextStyle: { color: '#666' },
      minInterval: 1,
      splitLine: { lineStyle: { type: 'dashed', color: '#e8e8e8' } }
    },
    series: [{
      type: 'bar',
      data: values,
      barWidth: '40%',
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#FF6B35' },
          { offset: 1, color: '#FF8F5E' }
        ]),
        borderRadius: [4, 4, 0, 0]
      },
      label: {
        show: true,
        position: 'top',
        color: '#333',
        fontSize: 12
      }
    }]
  })
}

// ---- 窗口自适应 ----

/** 窗口大小变化时自动调整图表尺寸 */
function handleResize() {
  if (pieChartInstance) {
    pieChartInstance.resize()
  }
  if (lineChartInstance) {
    lineChartInstance.resize()
  }
  if (barChartInstance) {
    barChartInstance.resize()
  }
}
</script>

<style scoped>
/* 页面容器 */
.dashboard-page {
  padding: 20px;
  min-height: 100%;
}

/* 页面标题栏 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 22px;
}

/* ==================== 统计卡片 ==================== */

.stat-card {
  cursor: pointer;
  transition: transform 0.2s ease;
}

.stat-card:hover {
  transform: translateY(-3px);
}

.stat-card__inner {
  display: flex;
  align-items: center;
  gap: 16px;
}

/* 统计卡片图标容器 */
.stat-card__icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* 各卡片图标背景色 */
.stat-total .stat-card__icon {
  background: rgba(64, 158, 255, 0.12);
  color: #409eff;
}

.stat-fire .stat-card__icon {
  background: rgba(230, 126, 34, 0.12);
  color: #e67e22;
}

.stat-smoke .stat-card__icon {
  background: rgba(127, 140, 141, 0.12);
  color: #7f8c8d;
}

.stat-warning .stat-card__icon {
  background: rgba(231, 76, 60, 0.12);
  color: #e74c3c;
}

/* 统计卡片内容区 */
.stat-card__content {
  flex: 1;
  min-width: 0;
}

/* 统计数值 */
.stat-card__value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
  color: #303133;
}

/* 统计标题 */
.stat-card__title {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

/* 各卡片数值颜色 */
.stat-total .stat-card__value { color: #409eff; }
.stat-fire .stat-card__value { color: #e67e22; }
.stat-smoke .stat-card__value { color: #7f8c8d; }
.stat-warning .stat-card__value { color: #e74c3c; }

/* ==================== 图表卡片 ==================== */

.chart-card {
  height: 100%;
}

/* 图表卡片头部 */
.chart-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chart-card__header span {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 15px;
}

/* 图表容器 */
.chart-container {
  width: 100%;
  height: 350px;
}
</style>