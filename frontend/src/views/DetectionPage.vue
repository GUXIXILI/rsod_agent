<template>
  <div class="detection-page">
    <!-- ── 页面标题 ── -->
    <div class="page-header">
      <h2>检测工作台</h2>
      <el-tag :type="statusTagType" size="large">
        {{ statusText }}
      </el-tag>
    </div>

    <!-- ── 主体区域 ── -->
    <div class="main-content">
      <!-- 左侧：图片上传 + 参数配置 -->
      <div class="upload-panel">
        <!-- 模式切换 -->
        <div class="mode-switch">
          <span class="control-label">检测模式：</span>
          <el-radio-group v-model="detectMode" :disabled="isDetecting">
            <el-radio-button label="single">单图检测</el-radio-button>
            <el-radio-button label="batch">批量检测</el-radio-button>
          </el-radio-group>
        </div>

        <!-- 图片上传区域 -->
        <div class="upload-area">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :multiple="detectMode === 'batch'"
            :limit="detectMode === 'batch' ? 20 : 1"
            :accept="'.jpg,.jpeg,.png,.bmp,.webp'"
            :file-list="fileList"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :on-exceed="handleExceed"
            list-type="picture-card"
            drag
            action="#"
          >
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div class="upload-text">
              <span>将图片拖拽到此处，或</span>
              <em>点击上传</em>
            </div>
            <template #tip>
              <div class="upload-tip">
                支持 jpg / jpeg / png / bmp / webp 格式，
                {{ detectMode === 'batch' ? '最多 20 张' : '单张图片' }}
              </div>
            </template>
          </el-upload>
        </div>

        <!-- 参数配置 -->
        <el-card class="params-card" shadow="never">
          <template #header>
            <span>检测参数配置</span>
          </template>

          <div class="params-form">
            <div class="param-item">
              <span class="param-label">置信度阈值</span>
              <el-slider
                v-model="confThreshold"
                :min="0.05"
                :max="0.95"
                :step="0.05"
                :disabled="isDetecting"
                show-input
                style="flex: 1"
              />
            </div>

            <div class="param-item">
              <span class="param-label">IOU 阈值</span>
              <el-slider
                v-model="iouThreshold"
                :min="0.1"
                :max="0.9"
                :step="0.05"
                :disabled="isDetecting"
                show-input
                style="flex: 1"
              />
            </div>

            <div class="param-item">
              <span class="param-label">场景 ID</span>
              <el-input-number
                v-model="sceneId"
                :min="1"
                :disabled="isDetecting"
                style="width: 120px"
              />
            </div>
          </div>
        </el-card>

        <!-- 检测按钮 -->
        <el-button
          type="primary"
          size="large"
          :loading="isDetecting"
          :disabled="fileList.length === 0"
          @click="startDetection"
          style="width: 100%; margin-top: 16px"
        >
          <el-icon><Search /></el-icon>
          {{ isDetecting ? '检测中...' : '开始检测' }}
        </el-button>
      </div>

      <!-- 右侧：检测结果 -->
      <div class="result-panel">
        <!-- 无结果占位 -->
        <div v-if="results.length === 0 && !isDetecting" class="empty-state">
          <el-icon :size="64" color="#ccc"><PictureFilled /></el-icon>
          <p>上传图片并点击"开始检测"查看结果</p>
        </div>

        <!-- 检测中 -->
        <div v-if="isDetecting" class="detecting-state">
          <el-icon :size="32" class="is-loading"><Loading /></el-icon>
          <p>正在检测中，请稍候...</p>
        </div>

        <!-- 结果列表 -->
        <div v-if="results.length > 0" class="results-container">
          <!-- 总览统计 -->
          <el-card class="summary-card" shadow="never">
            <template #header>
              <span>检测概览</span>
            </template>
            <div class="summary-stats">
              <div class="summary-item">
                <div class="summary-value">{{ results.length }}</div>
                <div class="summary-label">检测图片数</div>
              </div>
              <div class="summary-item">
                <div class="summary-value danger">{{ totalFireCount }}</div>
                <div class="summary-label">火焰目标数</div>
              </div>
              <div class="summary-item">
                <div class="summary-value warning">{{ totalSmokeCount }}</div>
                <div class="summary-label">烟雾目标数</div>
              </div>
              <div class="summary-item">
                <div class="summary-value">{{ totalInferenceTime }}ms</div>
                <div class="summary-label">总推理耗时</div>
              </div>
            </div>
          </el-card>

          <!-- 各图片结果 -->
          <el-card
            v-for="(result, index) in results"
            :key="index"
            class="result-card"
            shadow="never"
          >
            <template #header>
              <div class="result-card-header">
                <span>图片 {{ index + 1 }}</span>
                <el-tag size="small" type="success">
                  火 {{ result.fire_object_count || 0 }} / 烟 {{ result.smoke_object_count || 0 }}
                </el-tag>
                <el-tag
                  v-if="result.fire_level"
                  size="small"
                  :type="fireLevelType(result.fire_level)"
                >
                  {{ result.fire_level }}
                </el-tag>
              </div>
            </template>
            <div class="result-card-body">
              <div class="result-info">
                <div class="info-row">
                  <span class="info-label">推理耗时</span>
                  <span class="info-value">{{ result.inference_time || 0 }}ms</span>
                </div>
                <div class="info-row">
                  <span class="info-label">火焰目标</span>
                  <span class="info-value danger">{{ result.fire_object_count || 0 }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">烟雾目标</span>
                  <span class="info-value warning">{{ result.smoke_object_count || 0 }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">火灾等级</span>
                  <span class="info-value">{{ result.fire_level || '无' }}</span>
                </div>
              </div>
              <!-- 标注图（如果有） -->
              <div v-if="result.annotated_url" class="result-annotated">
                <img
                  :src="result.annotated_url"
                  alt="检测标注图"
                  @click="previewAnnotated(result.annotated_url)"
                />
              </div>
            </div>
          </el-card>
        </div>
      </div>
    </div>

    <!-- 全屏图片预览 -->
    <el-dialog v-model="showPreview" title="检测标注图" width="80%">
      <img v-if="previewSrc" :src="previewSrc" style="width: 100%" alt="标注图" />
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * DetectionPage.vue — 图片检测工作台
 *
 * 功能：
 *   - 单图/批量图片上传检测
 *   - 可调节置信度阈值、IOU 阈值
 *   - 展示检测结果：火焰/烟雾目标数、火灾等级、推理耗时
 *   - 标注图预览
 */
import { UploadFilled, Search, PictureFilled, Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, ref } from 'vue'
import { detectSingle } from '@/api/detection'

// ── 响应式状态 ──
const uploadRef = ref(null)
const fileList = ref([])
const detectMode = ref('single')
const isDetecting = ref(false)
const results = ref([])

// 检测配置
const confThreshold = ref(0.25)
const iouThreshold = ref(0.45)
const sceneId = ref(1)

// 图片预览
const showPreview = ref(false)
const previewSrc = ref('')

// ── 计算属性 ──
const statusText = computed(() => {
  if (isDetecting.value) return '检测中...'
  if (results.value.length > 0) return '检测完成'
  return '待检测'
})

const statusTagType = computed(() => {
  if (isDetecting.value) return 'warning'
  if (results.value.length > 0) return 'success'
  return 'info'
})

const totalFireCount = computed(() => {
  return results.value.reduce((sum, r) => sum + (r.fire_object_count || 0), 0)
})

const totalSmokeCount = computed(() => {
  return results.value.reduce((sum, r) => sum + (r.smoke_object_count || 0), 0)
})

const totalInferenceTime = computed(() => {
  return results.value.reduce((sum, r) => sum + (r.inference_time || 0), 0)
})

function fireLevelType(level) {
  const map = { '低': 'info', '中': 'warning', '高': 'danger', '严重': 'danger' }
  return map[level] || 'info'
}

// ── 文件处理 ──
function handleFileChange(file) {
  // el-upload 自动管理 fileList
}

function handleFileRemove(file) {
  // el-upload 自动管理 fileList
}

function handleExceed() {
  ElMessage.warning(`最多上传 ${detectMode.value === 'batch' ? 20 : 1} 张图片`)
}

// ── 开始检测 ──
async function startDetection() {
  if (fileList.value.length === 0) {
    ElMessage.warning('请先上传图片')
    return
  }

  isDetecting.value = true
  results.value = []

  try {
    if (detectMode.value === 'single') {
      // 单图检测
      const file = fileList.value[0].raw
      const formData = new FormData()
      formData.append('file', file)
      formData.append('scene_id', sceneId.value)
      formData.append('conf_threshold', confThreshold.value)
      formData.append('iou_threshold', iouThreshold.value)

      const res = await detectSingle(formData, sceneId.value)
      if (res.code === 200) {
        results.value = [res.data]
        ElMessage.success('检测完成')
      } else {
        ElMessage.error(res.message || '检测失败')
      }
    } else {
      // 批量检测：逐个调用单图接口
      const allResults = []
      for (let i = 0; i < fileList.value.length; i++) {
        const file = fileList.value[i].raw
        const formData = new FormData()
        formData.append('file', file)
        formData.append('scene_id', sceneId.value)
        formData.append('conf_threshold', confThreshold.value)
        formData.append('iou_threshold', iouThreshold.value)

        try {
          const res = await detectSingle(formData, sceneId.value)
          if (res.code === 200) {
            allResults.push(res.data)
          }
        } catch (e) {
          console.error(`图片 ${i + 1} 检测失败:`, e)
        }
      }
      results.value = allResults
      ElMessage.success(`批量检测完成，成功 ${allResults.length} / ${fileList.value.length} 张`)
    }
  } catch (err) {
    console.error('[检测失败]', err)
    ElMessage.error('检测失败，请稍后重试')
  } finally {
    isDetecting.value = false
  }
}

function previewAnnotated(url) {
  previewSrc.value = url
  showPreview.value = true
}
</script>

<style lang="scss" scoped>
.detection-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
  background: #f5f5f5;
  overflow: hidden;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;

  h2 {
    margin: 0;
  }
}

.main-content {
  display: flex;
  gap: 20px;
  flex: 1;
  overflow: hidden;
}

/* 左侧上传区 */
.upload-panel {
  flex: 2;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}

.mode-switch {
  display: flex;
  align-items: center;
  gap: 12px;
}

.control-label {
  font-size: 14px;
  color: #666;
  white-space: nowrap;
}

.upload-area {
  :deep(.el-upload) {
    width: 100%;
  }

  :deep(.el-upload-dragger) {
    width: 100%;
    padding: 40px 20px;
  }
}

.upload-icon {
  font-size: 48px;
  color: #c0c4cc;
  margin-bottom: 10px;
}

.upload-text {
  font-size: 14px;
  color: #606266;

  em {
    color: #409eff;
    font-style: normal;
  }
}

.upload-tip {
  font-size: 12px;
  color: #999;
  margin-top: 8px;
}

.params-card {
  :deep(.el-card__body) {
    padding: 16px;
  }
}

.params-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.param-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.param-label {
  font-size: 14px;
  color: #666;
  white-space: nowrap;
  min-width: 90px;
}

/* 右侧结果区 */
.result-panel {
  flex: 3;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
  font-size: 16px;
  gap: 12px;
}

.detecting-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #409eff;
  font-size: 16px;
  gap: 12px;
}

.results-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.summary-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.summary-item {
  text-align: center;
  padding: 12px;
  background: #f9f9f9;
  border-radius: 8px;
}

.summary-value {
  font-size: 24px;
  font-weight: 700;
  color: #409eff;

  &.danger {
    color: #f56c6c;
  }

  &.warning {
    color: #e6a23c;
  }
}

.summary-label {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.result-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.result-card-body {
  display: flex;
  gap: 16px;
}

.result-info {
  flex: 0 0 160px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.info-label {
  color: #909399;
}

.info-value {
  font-weight: 600;
  color: #303133;

  &.danger {
    color: #f56c6c;
  }

  &.warning {
    color: #e6a23c;
  }
}

.result-annotated {
  flex: 1;
  min-width: 0;

  img {
    width: 100%;
    max-height: 300px;
    object-fit: contain;
    border-radius: 4px;
    cursor: pointer;
    border: 1px solid #e0e0e0;
    transition: opacity 0.2s;

    &:hover {
      opacity: 0.8;
    }
  }
}
</style>