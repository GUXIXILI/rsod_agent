<!--
  模型训练页面
  提供训练任务管理、实时监控、训练曲线展示等功能
-->
<template>
  <div class="page-container">
    <!-- 区域1：页面标题 + 操作按钮 -->
    <div class="card-container flex-between training-header">
      <h2>模型训练</h2>
      <el-button type="primary" @click="openTrainDialog">
        <el-icon><Plus /></el-icon>
        开始训练
      </el-button>
    </div>

    <!-- 区域2：训练任务列表 -->
    <div class="card-container" style="margin-top: 16px">
      <el-table :data="taskList" stripe style="width: 100%" v-loading="tableLoading">
        <el-table-column prop="task_uuid" label="任务ID" min-width="140" :formatter="(row, column, cellValue) => cellValue?.substring(0, 8)" />
        <el-table-column prop="model_name" label="模型名称" width="120" />
        <el-table-column prop="scene_name" label="场景" width="120" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="180">
          <template #default="{ row }">
            <el-progress
              :percentage="row.progress || 0"
              :status="row.status === 'failed' ? 'exception' : undefined"
              :stroke-width="14"
            />
          </template>
        </el-table-column>
        <el-table-column prop="current_epoch" label="当前Epoch" width="100" />
        <el-table-column prop="epochs" label="总计Epochs" width="100" />
        <el-table-column prop="device" label="设备" width="80" />
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'running'"
              type="danger"
              size="small"
              @click="handleStop(row)"
            >
              停止
            </el-button>
            <el-button
              v-if="row.status === 'completed'"
              type="primary"
              size="small"
              @click="handleViewMetrics(row)"
            >
              查看曲线
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 区域3：实时监控面板（仅运行中任务显示） -->
    <div v-if="runningTask" class="card-container" style="margin-top: 16px">
      <h3 style="margin-bottom: 16px">实时监控 — {{ runningTask.task_name }}</h3>
      <el-row :gutter="20">
        <el-col :span="12">
          <div class="monitor-item">
            <span class="monitor-label">训练进度</span>
            <el-progress
              :percentage="runningTask.progress || 0"
              :stroke-width="20"
              :text-inside="true"
            />
          </div>
        </el-col>
        <el-col :span="12">
          <div class="monitor-item">
            <span class="monitor-label">当前 Epoch</span>
            <span class="monitor-value">
              {{ runningTask.current_epoch || 0 }} / {{ runningTask.total_epochs || 0 }}
            </span>
          </div>
        </el-col>
      </el-row>
      <el-row :gutter="20" style="margin-top: 16px">
        <el-col :span="6">
          <div class="monitor-item">
            <span class="monitor-label">box_loss</span>
            <span class="monitor-value">{{ runningMetrics.box_loss ?? '-' }}</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="monitor-item">
            <span class="monitor-label">cls_loss</span>
            <span class="monitor-value">{{ runningMetrics.cls_loss ?? '-' }}</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="monitor-item">
            <span class="monitor-label">dfl_loss</span>
            <span class="monitor-value">{{ runningMetrics.dfl_loss ?? '-' }}</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="monitor-item">
            <span class="monitor-label">mAP50</span>
            <span class="monitor-value">{{ runningMetrics.mAP50 ?? '-' }}</span>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 区域4：ECharts 训练曲线图表 -->
    <div v-if="showMetrics" class="card-container" style="margin-top: 16px">
      <h3 style="margin-bottom: 16px">训练曲线 — {{ metricsTaskName }}</h3>
      <el-row :gutter="20">
        <el-col :span="12">
          <div ref="lossChartRef" style="width: 100%; height: 350px"></div>
        </el-col>
        <el-col :span="12">
          <div ref="mapChartRef" style="width: 100%; height: 350px"></div>
        </el-col>
      </el-row>
    </div>

    <!-- 区域5：训练配置对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="训练配置"
      width="560px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form
        ref="formRef"
        :model="trainForm"
        :rules="formRules"
        label-width="130px"
        label-position="right"
      >
        <el-form-item label="场景选择" prop="scene">
          <el-select
            v-model="trainForm.scene"
            placeholder="请选择场景"
            style="width: 100%"
          >
            <el-option
              v-for="scene in sceneList"
              :key="scene.id || scene.name"
              :label="scene.name"
              :value="scene.name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="模型名称" prop="model_name">
          <el-input v-model="trainForm.model_name" placeholder="请输入模型名称" />
        </el-form-item>
        <el-form-item label="Epochs" prop="epochs">
          <el-input-number
            v-model="trainForm.epochs"
            :min="1"
            :max="1000"
            :step="1"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="Batch Size" prop="batch_size">
          <el-input-number
            v-model="trainForm.batch_size"
            :min="1"
            :max="128"
            :step="1"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="图像尺寸" prop="img_size">
          <el-select
            v-model="trainForm.img_size"
            placeholder="请选择图像尺寸"
            style="width: 100%"
          >
            <el-option
              v-for="size in imgSizeOptions"
              :key="size"
              :label="size"
              :value="size"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="设备" prop="device">
          <el-select
            v-model="trainForm.device"
            placeholder="请选择设备"
            style="width: 100%"
          >
            <el-option
              v-for="dev in deviceOptions"
              :key="dev"
              :label="dev === 'cpu' ? 'CPU' : `GPU ${dev}`"
              :value="dev"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitTrain">
          开始训练
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import request from '@/utils/request'
import {
  startTraining,
  getTrainingTasks,
  getTrainingStatus,
  getTrainingMetrics,
  stopTraining,
} from '@/api/training'

// ==================== 响应式数据 ====================

// 任务列表
const taskList = ref([])
const tableLoading = ref(false)

// 轮询定时器
let pollTimer = null

// 场景列表
const sceneList = ref([])

// 对话框
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref(null)

// 训练表单
const trainForm = reactive({
  scene: '',
  model_name: 'yolo11n',
  epochs: 100,
  batch_size: 16,
  img_size: 640,
  device: 'cpu',
})

// 表单验证规则
const formRules = {
  scene: [{ required: true, message: '请选择场景', trigger: 'change' }],
  model_name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
}

// 图像尺寸选项
const imgSizeOptions = [320, 416, 512, 640]

// 设备选项
const deviceOptions = ['cpu', '0', '1']

// 运行中的任务
const runningTask = computed(() => {
  return taskList.value.find((t) => t.status === 'running') || null
})

// 运行中任务的最新指标
const runningMetrics = reactive({
  box_loss: null,
  cls_loss: null,
  dfl_loss: null,
  mAP50: null,
  mAP50_95: null,
})

// ==================== 图表相关 ====================

const showMetrics = ref(false)
const metricsTaskName = ref('')
const lossChartRef = ref(null)
const mapChartRef = ref(null)
let lossChartInstance = null
let mapChartInstance = null

// ==================== 状态映射工具 ====================

/**
 * 状态标签文本映射
 */
const statusLabel = (status) => {
  const map = {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
  }
  return map[status] || status
}

/**
 * 状态标签颜色映射
 */
const statusTagType = (status) => {
  const map = {
    pending: 'info',
    running: '',
    completed: 'success',
    failed: 'danger',
    cancelled: 'warning',
  }
  return map[status] || 'info'
}

// ==================== 数据加载 ====================

/**
 * 获取场景列表
 */
const fetchScenes = async () => {
  try {
    const data = await request.get('/scenes')
    sceneList.value = Array.isArray(data) ? data : data.scenes || []
  } catch {
    // 场景列表加载失败不影响主流程
  }
}

/**
 * 刷新任务列表
 */
const fetchTasks = async () => {
  try {
    const data = await getTrainingTasks()
    taskList.value = Array.isArray(data) ? data : data.tasks || []
  } catch {
    // 静默处理，避免轮询时频繁弹窗
  }
}

/**
 * 轮询刷新运行中任务的状态
 */
const pollRunningTask = async () => {
  const task = runningTask.value
  if (!task) return

  try {
    const status = await getTrainingStatus(task.task_uuid)
    if (status) {
      // 更新任务列表中的进度
      const idx = taskList.value.findIndex((t) => t.id === task.id)
      if (idx !== -1) {
        taskList.value[idx] = { ...taskList.value[idx], ...status }
      }

      // 更新实时指标
      if (status.latest_metric) {
        runningMetrics.box_loss = status.latest_metric.box_loss ?? null
        runningMetrics.cls_loss = status.latest_metric.cls_loss ?? null
        runningMetrics.dfl_loss = status.latest_metric.dfl_loss ?? null
        runningMetrics.mAP50 = status.latest_metric.mAP50 ?? null
        runningMetrics.mAP50_95 = status.latest_metric.mAP50_95 ?? null
      }
    }
  } catch {
    // 静默处理
  }
}

/**
 * 开始轮询
 */
const startPolling = () => {
  stopPolling()
  pollTimer = setInterval(async () => {
    await pollRunningTask()
    // 如果任务不在运行中，刷新一次完整列表
    if (!runningTask.value) {
      await fetchTasks()
    }
  }, 5000)
}

/**
 * 停止轮询
 */
const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// ==================== 操作处理 ====================

/**
 * 打开训练配置对话框
 */
const openTrainDialog = () => {
  dialogVisible.value = true
}

/**
 * 重置表单
 */
const resetForm = () => {
  trainForm.scene = ''
  trainForm.model_name = 'yolo11n'
  trainForm.epochs = 100
  trainForm.batch_size = 16
  trainForm.img_size = 640
  trainForm.device = 'cpu'
  formRef.value?.resetFields()
}

/**
 * 提交训练
 */
const submitTrain = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    // 将前端字段映射为后端 schema
    const scene = sceneList.value.find((s) => s.name === trainForm.scene)
    const payload = {
      scene_id: scene?.id,
      model_name: trainForm.model_name,
      epochs: trainForm.epochs,
      img_size: trainForm.img_size,
      batch_size: trainForm.batch_size,
      device: trainForm.device,
    }
    await startTraining(payload)
    ElMessage.success('训练任务已启动')
    dialogVisible.value = false
    await fetchTasks()
  } catch {
    // 错误已在 request 拦截器中处理
  } finally {
    submitting.value = false
  }
}

/**
 * 停止训练
 */
const handleStop = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要停止任务「${row.task_name}」吗？`,
      '停止训练',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    await stopTraining(row.task_uuid)
    ElMessage.success('训练已停止')
    await fetchTasks()
  } catch {
    // 取消操作或错误
  }
}

/**
 * 查看训练曲线
 */
const handleViewMetrics = async (row) => {
  metricsTaskName.value = row.model_name || row.task_name
  showMetrics.value = true

  try {
    const data = await getTrainingMetrics(row.task_uuid)
    const metrics = Array.isArray(data) ? data : data.metrics || []

    await nextTick()
    renderCharts(metrics)
  } catch {
    ElMessage.error('获取训练指标失败')
  }
}

// ==================== 图表渲染 ====================

/**
 * 初始化 ECharts 实例
 */
const initCharts = () => {
  if (lossChartRef.value) {
    lossChartInstance = echarts.init(lossChartRef.value)
  }
  if (mapChartRef.value) {
    mapChartInstance = echarts.init(mapChartRef.value)
  }
}

/**
 * 渲染图表
 */
const renderCharts = (metrics) => {
  if (!metrics || metrics.length === 0) return

  const epochs = metrics.map((m) => m.epoch)

  // Loss 曲线配置
  const lossOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['box_loss', 'cls_loss', 'dfl_loss'], bottom: 0 },
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'category',
      name: 'Epoch',
      data: epochs,
    },
    yAxis: {
      type: 'value',
      name: 'Loss',
    },
    series: [
      {
        name: 'box_loss',
        type: 'line',
        data: metrics.map((m) => m.box_loss),
        smooth: true,
        lineStyle: { color: '#409EFF' },
        itemStyle: { color: '#409EFF' },
      },
      {
        name: 'cls_loss',
        type: 'line',
        data: metrics.map((m) => m.cls_loss),
        smooth: true,
        lineStyle: { color: '#F56C6C' },
        itemStyle: { color: '#F56C6C' },
      },
      {
        name: 'dfl_loss',
        type: 'line',
        data: metrics.map((m) => m.dfl_loss),
        smooth: true,
        lineStyle: { color: '#67C23A' },
        itemStyle: { color: '#67C23A' },
      },
    ],
  }

  // mAP 曲线配置
  const mapOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['mAP50', 'mAP50-95'], bottom: 0 },
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'category',
      name: 'Epoch',
      data: epochs,
    },
    yAxis: {
      type: 'value',
      name: 'mAP',
    },
    series: [
      {
        name: 'mAP50',
        type: 'line',
        data: metrics.map((m) => m.mAP50),
        smooth: true,
        lineStyle: { color: '#409EFF' },
        itemStyle: { color: '#409EFF' },
      },
      {
        name: 'mAP50-95',
        type: 'line',
        data: metrics.map((m) => m.mAP50_95),
        smooth: true,
        lineStyle: { color: '#F56C6C' },
        itemStyle: { color: '#F56C6C' },
      },
    ],
  }

  if (lossChartInstance) {
    lossChartInstance.setOption(lossOption, true)
  } else {
    initCharts()
    lossChartInstance?.setOption(lossOption, true)
  }

  if (mapChartInstance) {
    mapChartInstance.setOption(mapOption, true)
  } else {
    initCharts()
    mapChartInstance?.setOption(mapOption, true)
  }
}

/**
 * 销毁图表实例
 */
const disposeCharts = () => {
  if (lossChartInstance) {
    lossChartInstance.dispose()
    lossChartInstance = null
  }
  if (mapChartInstance) {
    mapChartInstance.dispose()
    mapChartInstance = null
  }
}

// ==================== 生命周期 ====================

onMounted(async () => {
  await fetchScenes()
  await fetchTasks()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
  disposeCharts()
})
</script>

<style scoped lang="scss">
.training-header {
  h2 {
    margin: 0;
    font-size: 20px;
    color: $text-primary;
  }
}

.monitor-item {
  padding: $spacing-md;
  background-color: $bg-light;
  border-radius: $border-radius-sm;

  .monitor-label {
    display: block;
    font-size: 13px;
    color: $text-secondary;
    margin-bottom: $spacing-sm;
  }

  .monitor-value {
    font-size: 20px;
    font-weight: 600;
    color: $text-primary;
  }
}
</style>