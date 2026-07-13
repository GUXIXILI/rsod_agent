<template>
  <div class="dashboard-page">
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <el-statistic title="总检测次数" :value="overview.total_detections || 0" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-fire">
          <el-statistic title="火焰检出次数" :value="overview.fire_detected || 0" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-smoke">
          <el-statistic title="烟雾检出次数" :value="overview.smoke_detected || 0" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-warning">
          <el-statistic title="预警次数" :value="overview.warning_count || 0" />
        </el-card>
      </el-col>
    </el-row>
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card>
          <template #header><span>火情等级分布</span></template>
          <div ref="pieChartRef" style="height: 350px" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><span>检测趋势（近7天）</span></template>
          <div ref="lineChartRef" style="height: 350px" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { getOverview, getFireLevelDistribution, getTrend } from '@/api/stats'
import * as echarts from 'echarts'

const overview = ref({})
const pieChartRef = ref(null)
const lineChartRef = ref(null)

onMounted(async () => {
  try {
    const ovRes = await getOverview()
    overview.value = ovRes.data || {}
  } catch (e) {
    ElMessage.error('获取总览数据失败')
  }

  await nextTick()
  let pieChart, lineChart
  if (pieChartRef.value) pieChart = echarts.init(pieChartRef.value)
  if (lineChartRef.value) lineChart = echarts.init(lineChartRef.value)

  try {
    const distRes = await getFireLevelDistribution()
    const distData = (distRes.data || []).map(d => ({ name: fireLevelLabel(d.fire_level), value: d.count }))
    if (pieChart) {
      pieChart.setOption({
        tooltip: { trigger: 'item' },
        legend: { bottom: '5%' },
        series: [{
          type: 'pie',
          radius: ['40%', '70%'],
          itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
          label: { show: true },
          data: distData
        }]
      })
    }
  } catch (e) {
    console.error('获取火情分布失败', e)
  }

  try {
    const trendRes = await getTrend({ days: 7 })
    const trendData = trendRes.data || []
    if (lineChart) {
      lineChart.setOption({
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: trendData.map(d => d.date) },
        yAxis: { type: 'value', name: '检测次数' },
        series: [{
          type: 'line',
          data: trendData.map(d => d.count),
          smooth: true,
          areaStyle: { opacity: 0.3 },
          itemStyle: { color: '#e74c3c' }
        }]
      })
    }
  } catch (e) {
    console.error('获取趋势数据失败', e)
  }
})

function fireLevelLabel(level) {
  const map = { safe: '安全', notice: '关注', warning: '警告', danger: '危险' }
  return map[level] || '未知'
}
</script>

<style scoped>
.dashboard-page { padding: 20px; }
.stat-card .el-statistic { text-align: center; }
.stat-fire :deep(.el-statistic__number) { color: #e67e22; }
.stat-smoke :deep(.el-statistic__number) { color: #7f8c8d; }
.stat-warning :deep(.el-statistic__number) { color: #e74c3c; }
</style>