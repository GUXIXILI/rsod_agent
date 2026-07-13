<template>
  <div class="detection-page">
    <el-card class="upload-card">
      <template #header>
        <div class="card-header">
          <span>火灾烟雾检测工作台</span>
          <el-tag v-if="selectedScene" type="success" size="small">{{ selectedScene.display_name }}</el-tag>
        </div>
      </template>
      <el-row :gutter="20">
        <el-col :span="8">
          <el-form label-width="100px" size="small">
            <el-form-item label="检测场景">
              <el-select v-model="sceneId" placeholder="选择场景" @change="onSceneChange">
                <el-option v-for="s in scenes" :key="s.id" :label="s.display_name" :value="s.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="置信度阈值">
              <el-slider v-model="confThreshold" :min="0.05" :max="0.95" :step="0.05" show-input />
            </el-form-item>
            <el-form-item label="IoU 阈值">
              <el-slider v-model="iouThreshold" :min="0.1" :max="0.9" :step="0.05" show-input />
            </el-form-item>
            <el-form-item label="检测模式">
              <el-radio-group v-model="detectMode">
                <el-radio-button label="single">单图检测</el-radio-button>
                <el-radio-button label="batch">批量检测</el-radio-button>
                <el-radio-button label="video">视频检测</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item>
              <el-upload
                ref="uploadRef"
                :action="''"
                :auto-upload="false"
                :multiple="detectMode === 'batch'"
                :accept="detectMode === 'video' ? 'video/*' : 'image/*'"
                :on-change="handleFileChange"
                :file-list="fileList"
                :limit="detectMode === 'batch' ? 20 : 1"
                list-type="picture"
                drag
              >
                <el-icon><UploadFilled /></el-icon>
                <div class="el-upload__text">
                  拖拽{{ detectMode === 'video' ? '视频' : '图片' }}到此处或<em>点击上传</em>
                </div>
              </el-upload>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" size="large" :loading="detecting" :disabled="!sceneId || fileList.length === 0" @click="startDetect" style="width: 100%">
                {{ detecting ? '检测中...' : '开始检测' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-col>
        <el-col :span="16">
          <div v-if="detectResult" class="result-area">
            <el-alert
              :title="'火情等级：' + fireLevelLabel"
              :type="fireLevelType"
              :description="fireLevelDesc"
              show-icon
              :closable="false"
              style="margin-bottom: 16px"
            />
            <el-image
              v-if="detectResult.annotated_url"
              :src="detectResult.annotated_url"
              fit="contain"
              style="max-height: 500px; width: 100%"
            />
            <el-descriptions v-if="detectResult" :column="2" border size="small" style="margin-top: 16px">
              <el-descriptions-item label="火焰目标数">{{ detectResult.fire_object_count || 0 }}</el-descriptions-item>
              <el-descriptions-item label="烟雾目标数">{{ detectResult.smoke_object_count || 0 }}</el-descriptions-item>
              <el-descriptions-item label="火情等级">
                <el-tag :type="fireLevelType">{{ fireLevelLabel }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="检测时间">{{ detectTime }}</el-descriptions-item>
            </el-descriptions>
          </div>
          <el-empty v-else description="请上传图片或视频开始检测" />
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { detectSingle, detectBatch, detectVideo } from '@/api/detection'
import { getActiveScenes } from '@/api/training'

const scenes = ref([])
const sceneId = ref(null)
const selectedScene = computed(() => scenes.value.find(s => s.id === sceneId.value))
const confThreshold = ref(0.25)
const iouThreshold = ref(0.45)
const detectMode = ref('single')
const fileList = ref([])
const detecting = ref(false)
const detectResult = ref(null)
const uploadRef = ref(null)

const fireLevelLabel = computed(() => {
  const map = { safe: '安全', notice: '关注', warning: '警告', danger: '危险' }
  return map[detectResult.value?.fire_level] || '未知'
})
const fireLevelType = computed(() => {
  const map = { safe: 'success', notice: 'info', warning: 'warning', danger: 'danger' }
  return map[detectResult.value?.fire_level] || 'info'
})
const fireLevelDesc = computed(() => {
  const map = {
    safe: '当前无火情，持续监控中',
    notice: '检测到烟雾，请持续观察',
    warning: '检测到火焰，请立即核实',
    danger: '火势较大，请立即处置'
  }
  return map[detectResult.value?.fire_level] || ''
})
const detectTime = computed(() => new Date().toLocaleString())

onMounted(async () => {
  try {
    const res = await getActiveScenes()
    scenes.value = res.data || []
  } catch (e) {
    ElMessage.error('获取场景列表失败')
  }
})

function onSceneChange() {}

function handleFileChange(file, fileListNew) {
  fileList.value = fileListNew
}

async function startDetect() {
  if (!sceneId.value || fileList.value.length === 0) {
    ElMessage.warning('请选择场景并上传文件')
    return
  }
  detecting.value = true
  detectResult.value = null
  try {
    const formData = new FormData()
    formData.append('scene_id', sceneId.value)
    formData.append('conf_threshold', confThreshold.value)
    formData.append('iou_threshold', iouThreshold.value)
    formData.append('image_size', 640)

    let res
    if (detectMode.value === 'single') {
      formData.append('file', fileList.value[0].raw)
      res = await detectSingle(formData)
    } else if (detectMode.value === 'batch') {
      fileList.value.forEach(f => formData.append('files', f.raw))
      res = await detectBatch(formData)
    } else {
      formData.append('file', fileList.value[0].raw)
      formData.append('frame_skip', 5)
      res = await detectVideo(formData)
    }

    if (res.data) {
      detectResult.value = res.data
      ElMessage.success('检测完成')
    }
  } catch (e) {
    ElMessage.error('检测失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    detecting.value = false
  }
}
</script>

<style scoped>
.detection-page {
  padding: 20px;
}
.upload-card {
  max-width: 1400px;
  margin: 0 auto;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}
.result-area {
  min-height: 400px;
}
</style>