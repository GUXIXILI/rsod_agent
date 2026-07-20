<template>
  <div class="dashboard-page">
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
              <div class="stat-card__growth" v-if="overview.total_detections_growth !== undefined">
                <span :class="overview.total_detections_growth >= 0 ? 'growth-up' : 'growth-down'">
                  <el-icon><CaretTop v-if="overview.total_detections_growth >= 0" /><CaretBottom v-else /></el-icon>
                  {{ Math.abs(overview.total_detections_growth).toFixed(1) }}%
                </span>
                <span class="growth-label">环比上月</span>
              </div>
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
              <div class="stat-card__growth" v-if="overview.fire_detected_growth !== undefined">
                <span :class="overview.fire_detected_growth >= 0 ? 'growth-up' : 'growth-down'">
                  <el-icon><CaretTop v-if="overview.fire_detected_growth >= 0" /><CaretBottom v-else /></el-icon>
                  {{ Math.abs(overview.fire_detected_growth).toFixed(1) }}%
                </span>
                <span class="growth-label">环比上月</span>
              </div>
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
              <div class="stat-card__growth" v-if="overview.smoke_detected_growth !== undefined">
                <span :class="overview.smoke_detected_growth >= 0 ? 'growth-up' : 'growth-down'">
                  <el-icon><CaretTop v-if="overview.smoke_detected_growth >= 0" /><CaretBottom v-else /></el-icon>
                  {{ Math.abs(overview.smoke_detected_growth).toFixed(1) }}%
                </span>
                <span class="growth-label">环比上月</span>
              </div>
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
              <div class="stat-card__growth" v-if="overview.warning_count_growth !== undefined">
                <span :class="overview.warning_count_growth >= 0 ? 'growth-up' : 'growth-down'">
                  <el-icon><CaretTop v-if="overview.warning_count_growth >= 0" /><CaretBottom v-else /></el-icon>
                  {{ Math.abs(overview.warning_count_growth).toFixed(1) }}%
                </span>
                <span class="growth-label">环比上月</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ==================== 图表区域 ==================== -->
    <!-- 第一行：火情等级分布（饼图） + 任务类型分布（环形图） -->
    <el-row :gutter="20">
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
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="chart-card__header">
              <span><el-icon><PieChart /></el-icon> 任务类型分布</span>
              <el-tag size="small" type="info">检测任务分类</el-tag>
            </div>
          </template>
          <div ref="typePieChartRef" class="chart-container" v-loading="typePieLoading"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 第二行：近7天检测趋势折线图 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="24">
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

    <!-- 第三行：场景分布柱状图 -->
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
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import {
  VideoCamera,
  Sunny,
  Cloudy,
  WarningFilled,
  PieChart,
  TrendCharts,
  Histogram,
  CaretTop,
  CaretBottom
} from '@element-plus/icons-vue'
import { getOverview, getFireLevelDistribution, getTrend, getSceneDistribution, getTypeDistribution } from '@/api/stats'
import * as echarts from 'echarts'

// ---- 响应式数据 ----
const overview = ref({})

// 饼图 (火情等级)
const pieLoading = ref(false)
const pieChartRef = ref(null)
let pieChartInstance = null

// 环形图 (任务类型)
const typePieLoading = ref(false)
const typePieChartRef = ref(null)
let typePieChartInstance = null

// 折线图
const lineLoading = ref(false)
const lineChartRef = ref(null)
let lineChartInstance = null

// 柱状图
const barLoading = ref(false)
const barChartRef = ref(null)
let barChartInstance = null

// ---- 等级映射 ----
const FIRE_LEVEL_LABEL_MAP = {
  safe: '安全',
  notice: '关注',
  warning: '警告',
  danger: '危险'
}
const FIRE_LEVEL_COLOR_MAP = {
  safe: '#67c23a',
  notice: '#409eff',
  warning: '#e6a23c',
  danger: '#f56c6c'
}

function fireLevelLabel(level) {
  return FIRE_LEVEL_LABEL_MAP[level] || '未知'
}
function fireLevelColor(level) {
  return FIRE_LEVEL_COLOR_MAP[level] || '#909399'
}

// ---- 数据获取 ----
async function fetchOverview() {
  try {
    const res = await getOverview()
    overview.value = res.data || {}
  } catch (e) {
    ElMessage.error('获取总览数据失败')
  }
}

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

async function fetchTypePieData() {
  typePieLoading.value = true
  try {
    const res = await getTypeDistribution({ days: 30 })
    const distData = (res.data || []).map(d => ({
      name: d.task_type || '未知',
      value: d.count
    }))
    renderTypePieChart(distData)
  } catch (e) {
    console.error('获取任务类型分布失败', e)
  } finally {
    typePieLoading.value = false
  }
}

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

// ---- ECharts 初始化 ----
async function initCharts() {
  await nextTick()
  if (pieChartRef.value) pieChartInstance = echarts.init(pieChartRef.value)
  if (typePieChartRef.value) typePieChartInstance = echarts.init(typePieChartRef.value)
  if (lineChartRef.value) lineChartInstance = echarts.init(lineChartRef.value)
  if (barChartRef.value) barChartInstance = echarts.init(barChartRef.value)
}

// ---- 渲染函数 ----
function renderPieChart(data) {
  if (!pieChartInstance) return
  const hasData = data.some(d => d.value > 0)
  pieChartInstance.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} 次 ({d}%)' },
    legend: { bottom: '5%', itemWidth: 12, itemHeight: 12 },
    series: [{
      type: 'pie',
      radius: hasData ? ['45%', '72%'] : ['0%', '0%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
      label: { show: hasData, formatter: '{b}\n{d}%' },
      emphasis: { label: { fontSize: 16, fontWeight: 'bold' }, scaleSize: 10 },
      data: hasData ? data : [{ name: '暂无数据', value: 1, itemStyle: { color: '#e0e0e0' } }]
    }]
  })
}

function renderTypePieChart(data) {
  if (!typePieChartInstance) return
  const hasData = data.some(d => d.value > 0)
  // 定义一组柔和颜色
  const colors = ['#5470c6', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc']
  const coloredData = data.map((d, idx) => ({
    ...d,
    itemStyle: { color: colors[idx % colors.length] }
  }))
  typePieChartInstance.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} 次 ({d}%)' },
    legend: { bottom: '5%', itemWidth: 12, itemHeight: 12 },
    series: [{
      type: 'pie',
      radius: hasData ? ['40%', '70%'] : ['0%', '0%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
      label: { show: hasData, formatter: '{b}\n{d}%' },
      emphasis: { label: { fontSize: 16, fontWeight: 'bold' }, scaleSize: 10 },
      data: hasData ? coloredData : [{ name: '暂无数据', value: 1, itemStyle: { color: '#e0e0e0' } }]
    }]
  })
}

function renderLineChart(data) {
  if (!lineChartInstance) return
  const dates = data.map(d => d.date)
  const counts = data.map(d => d.count)
  lineChartInstance.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' }, formatter: '{b}<br/>检测次数：<b>{c}</b> 次' },
    grid: { top: 20, left: 10, right: 20, bottom: 10, containLabel: true },
    xAxis: { type: 'category', data: dates, boundaryGap: false, axisLine: { lineStyle: { color: '#ccc' } }, axisLabel: { color: '#666', formatter: v => v.substring(5) } },
    yAxis: { type: 'value', name: '检测次数', nameTextStyle: { color: '#666' }, minInterval: 1, splitLine: { lineStyle: { type: 'dashed', color: '#e8e8e8' } } },
    series: [{
      type: 'line',
      data: counts,
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      lineStyle: { color: '#e74c3c', width: 2.5 },
      itemStyle: { color: '#e74c3c' },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(231, 76, 60, 0.3)' }, { offset: 1, color: 'rgba(231, 76, 60, 0.02)' }]) },
      markLine: { silent: true, data: [{ type: 'average', name: '平均值' }], lineStyle: { color: '#e6a23c', type: 'dashed' } }
    }]
  })
}

function renderBarChart(data) {
  if (!barChartInstance) return
  const names = data.map(d => d.name)
  const values = data.map(d => d.value)
  barChartInstance.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: '{b}<br/>检测次数：<b>{c}</b> 次' },
    grid: { top: 20, left: 10, right: 20, bottom: 30, containLabel: true },
    xAxis: { type: 'category', data: names, axisLabel: { color: '#666', rotate: names.length > 6 ? 30 : 0 }, axisLine: { lineStyle: { color: '#ccc' } } },
    yAxis: { type: 'value', name: '检测次数', nameTextStyle: { color: '#666' }, minInterval: 1, splitLine: { lineStyle: { type: 'dashed', color: '#e8e8e8' } } },
    series: [{
      type: 'bar',
      data: values,
      barWidth: '40%',
      itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#FF6B35' }, { offset: 1, color: '#FF8F5E' }]), borderRadius: [4, 4, 0, 0] },
      label: { show: true, position: 'top', color: '#333', fontSize: 12 }
    }]
  })
}

// ---- 生命周期 ----
onMounted(async () => {
  await Promise.all([fetchOverview(), initCharts()])
  await Promise.all([fetchPieData(), fetchTypePieData(), fetchLineData(), fetchBarData()])
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  ;[pieChartInstance, typePieChartInstance, lineChartInstance, barChartInstance].forEach(inst => {
    if (inst) { inst.dispose(); inst = null }
  })
})

function handleResize() {
  ;[pieChartInstance, typePieChartInstance, lineChartInstance, barChartInstance].forEach(inst => {
    if (inst) inst.resize()
  })
}
</script>

<style scoped>
.dashboard-page { padding: 20px; min-height: 100%; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 22px; }

.stat-card { cursor: pointer; transition: transform 0.2s ease; }
.stat-card:hover { transform: translateY(-3px); }
.stat-card__inner { display: flex; align-items: center; gap: 16px; }
.stat-card__icon { width: 56px; height: 56px; border-radius: 12px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.stat-total .stat-card__icon { background: rgba(64, 158, 255, 0.12); color: #409eff; }
.stat-fire .stat-card__icon { background: rgba(230, 126, 34, 0.12); color: #e67e22; }
.stat-smoke .stat-card__icon { background: rgba(127, 140, 141, 0.12); color: #7f8c8d; }
.stat-warning .stat-card__icon { background: rgba(231, 76, 60, 0.12); color: #e74c3c; }
.stat-card__content { flex: 1; min-width: 0; }
.stat-card__value { font-size: 28px; font-weight: 700; line-height: 1.2; color: #303133; }
.stat-card__title { font-size: 13px; color: #909399; margin-top: 4px; }
.stat-total .stat-card__value { color: #409eff; }
.stat-fire .stat-card__value { color: #e67e22; }
.stat-smoke .stat-card__value { color: #7f8c8d; }
.stat-warning .stat-card__value { color: #e74c3c; }

.stat-card__growth { margin-top: 6px; font-size: 13px; display: flex; align-items: center; gap: 6px; }
.growth-up { color: #67c23a; }
.growth-down { color: #f56c6c; }
.growth-label { color: #909399; font-size: 12px; }

.chart-card { height: 100%; }
.chart-card__header { display: flex; align-items: center; justify-content: space-between; }
.chart-card__header span { display: flex; align-items: center; gap: 6px; font-weight: 600; font-size: 15px; }
.chart-container { width: 100%; height: 350px; }
</style>