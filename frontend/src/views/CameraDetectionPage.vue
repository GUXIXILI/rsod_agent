<template>
  <div class="detection-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>摄像头实时检测</h2>
      <el-tag :type="statusTagType" size="large">
        {{ statusText }}
      </el-tag>
    </div>

    <!-- 主体区域 -->
    <div class="main-content">
      <!-- 左侧：视频预览 -->
      <div class="preview-panel">
        <div class="video-wrapper">
          <!-- 原始视频（隐藏，用于获取帧） -->
          <video
            ref="videoRef"
            autoplay
            playsinline
            muted
            style="display: none"
          ></video>

          <!-- 标注画面 Canvas（显示标注后的帧） -->
          <canvas
            ref="canvasRef"
            class="preview-canvas"
          ></canvas>

          <!-- 编码用 Canvas（隐藏，复用不销毁） -->
          <canvas
            ref="encodeCanvasRef"
            style="display: none"
          ></canvas>

          <!-- 未开启时的占位 -->
          <div v-if="!isRunning" class="placeholder">
            <p>点击下方按钮开启摄像头</p>
          </div>
        </div>

        <!-- 视频状态标签行 -->
        <div v-if="isRunning" class="video-stats">
          <el-tag type="success">FPS: {{ currentFps }}</el-tag>
          <el-tag type="info">帧: {{ frameCount }}</el-tag>
          <el-tag type="warning">推理: {{ inferenceTime }}ms</el-tag>
        </div>
      </div>

      <!-- 右侧：检测结果 -->
      <div class="result-panel">
        <!-- 实时检测统计 -->
        <el-card class="stats-card" shadow="never">
          <template #header>
            <span>实时检测统计</span>
          </template>
          <div class="stats-grid">
            <div class="stat-item">
              <div class="stat-value">{{ objectCount }}</div>
              <div class="stat-label">当前目标数</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ currentFps }}</div>
              <div class="stat-label">实时 FPS</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ inferenceTime }}</div>
              <div class="stat-label">推理耗时(ms)</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ frameCount }}</div>
              <div class="stat-label">已处理帧</div>
            </div>
          </div>
        </el-card>

        <!-- 火情预警信息 -->
        <el-card class="alert-card" shadow="never" :class="'alert-' + fireLevel">
          <template #header>
            <div class="card-header">
              <span>火情预警信息</span>
              <el-tag :type="alertTagType" size="small">{{ alertText }}</el-tag>
            </div>
          </template>
          <div class="alert-info">
            <div class="alert-row">
              <span class="alert-label">火情等级：</span>
              <span class="alert-value">{{ alertLevelText }}</span>
            </div>
            <div class="alert-row">
              <span class="alert-label">火情目标：</span>
              <span class="alert-value">{{ fireCount }} 个</span>
            </div>
            <div class="alert-row">
              <span class="alert-label">烟雾目标：</span>
              <span class="alert-value">{{ smokeCount }} 个</span>
            </div>
            <div class="alert-row">
              <span class="alert-label">更新时间：</span>
              <span class="alert-value">{{ lastAlertTime || '--' }}</span>
            </div>
          </div>
        </el-card>

        <!-- 当前帧目标列表 -->
        <el-card class="detections-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>当前帧目标列表</span>
              <el-tag size="small">{{ currentDetections.length }} 个目标</el-tag>
            </div>
          </template>
          <div v-if="currentDetections.length === 0" class="empty-state">
            暂无检测目标
          </div>
          <div v-else class="detection-list">
            <div
              v-for="det in currentDetections"
              :key="det._uid"
              class="detection-item"
            >
              <div class="det-info">
                <span class="det-class">{{ det.class_name || det.class || det.name || det.label || 'unknown' }}</span>
                <el-progress
                  :percentage="Math.round(det.confidence * 100)"
                  :stroke-width="6"
                  :show-text="true"
                  style="width: 120px"
                />
              </div>
              <div class="det-bbox">
                [{{ det.bbox.map((v) => Math.round(v)).join(', ') }}]
              </div>
            </div>
          </div>
        </el-card>

        <!-- 类别分布统计 -->
        <el-card
          v-if="Object.keys(classDistribution).length > 0"
          class="distribution-card"
          shadow="never"
        >
          <template #header>
            <span>类别分布</span>
          </template>
          <div class="distribution-list">
            <div
              v-for="(count, className) in classDistribution"
              :key="className"
              class="distribution-item"
            >
              <span class="class-name">{{ className }}</span>
              <el-tag size="small" type="primary">{{ count }}</el-tag>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 控制栏 -->
    <div class="control-bar">
      <el-button
        v-if="!isRunning"
        type="primary"
        size="large"
        @click="startCamera"
        :loading="isConnecting"
      >
        开启摄像头
      </el-button>
      <el-button v-else type="danger" size="large" @click="stopCamera">
        停止检测
      </el-button>
      <el-button v-if="isRunning" type="success" size="large" @click="generateReport">
        生成报告
      </el-button>

      <el-divider direction="vertical" />

      <!-- GPU/CPU 模式选择 -->
      <span class="control-label">推理模式：</span>
      <el-radio-group v-model="detectMode" :disabled="isRunning">
        <el-radio-button label="cpu">CPU 节能</el-radio-button>
        <el-radio-button label="gpu">GPU 加速</el-radio-button>
      </el-radio-group>

      <el-divider direction="vertical" />

      <!-- 置信度阈值 -->
      <span class="control-label">置信度：</span>
      <el-slider
        v-model="confThreshold"
        :min="0.1"
        :max="0.9"
        :step="0.05"
        :disabled="isRunning"
        style="width: 150px"
        show-input
      />
    </div>
  </div>
</template>

<script setup>
/**
 * CameraDetectionPage.vue — 摄像头实时检测独立页面
 *
 * 功能：
 *   - 浏览器 getUserMedia() 获取摄像头画面（320x240 低分辨率优化）
 *   - WebSocket 实时发送帧数据到后端（JPEG 0.45 压缩）
 *   - 接收后端返回的标注帧并渲染到 Canvas
 *   - 响应驱动帧发送：收到 config_ok → 发第一帧，收到 result 渲染后 → 发下一帧
 *   - GPU/CPU 双模式切换（CPU image_size=320, GPU image_size=640）
 *   - 实时统计：FPS、目标数、推理耗时、帧数、类别分布
 *   - 火情预警通知
 *   - 编码 Canvas 复用（不每次创建新 Canvas）
 *
 * 按照讲义 Day09 Section 8 的三区布局设计：
 *   左侧 — 视频预览区（隐藏 video + 可见 canvas）
 *   右侧 — 检测结果区（统计卡片 + 目标列表 + 类别分布）
 *   底部 — 控制栏（开启/停止 + 模式切换 + 置信度滑块）
 */
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { computed, onBeforeUnmount, ref } from 'vue'

// ── DOM 引用 ──
const videoRef = ref(null)
const canvasRef = ref(null)
const encodeCanvasRef = ref(null)

// ── 摄像头状态 ──
const isRunning = ref(false)
const isConnecting = ref(false)

// ── 检测配置 ──
const detectMode = ref('cpu')
const confThreshold = ref(0.25)

// ── 实时统计 ──
const currentFps = ref(0)
const frameCount = ref(0)
const inferenceTime = ref(0)
const objectCount = ref(0)
const currentDetections = ref([])
let _uidCounter = 0

// ── 火情预警 ──
const fireLevel = ref('safe')
const fireCount = ref(0)
const smokeCount = ref(0)
const lastAlertTime = ref('')

// ── 非响应式变量 ──
let ws = null
let mediaStream = null
let lastFireLevel = 'safe'

// WebSocket 重连相关
let _reconnectTimer = null
let _reconnectAttempts = 0
const _MAX_RECONNECT_ATTEMPTS = 5
const _RECONNECT_BASE_DELAY = 1000  // 初始延迟 1 秒

// ── 计算属性 ──
const statusText = computed(() => {
  if (isConnecting.value) return '连接中...'
  if (isRunning.value) return '运行中'
  return '未启动'
})

const statusTagType = computed(() => {
  if (isConnecting.value) return 'warning'
  if (isRunning.value) return 'success'
  return 'info'
})

const classDistribution = computed(() => {
  const dist = {}
  for (const det of currentDetections.value) {
    // 兼容多种字段名
    const name = det.class_name || det.class || det.name || det.label || 'unknown'
    dist[name] = (dist[name] || 0) + 1
  }
  return dist
})

const alertTagType = computed(() => {
  const map = { safe: 'success', notice: 'warning', warning: 'warning', danger: 'danger' }
  return map[fireLevel.value] || 'info'
})
const alertText = computed(() => {
  const map = { safe: '安全', notice: '注意', warning: '警告', danger: '危险' }
  return map[fireLevel.value] || '未知'
})
const alertLevelText = computed(() => {
  const map = { safe: '无火情', notice: '轻微火情', warning: '中度火情', danger: '严重火情' }
  return map[fireLevel.value] || fireLevel.value
})

// ── 开启摄像头 ──

/**
 * 开启摄像头并建立 WebSocket 检测连接
 * 1. 获取浏览器摄像头权限（320x240 低分辨率）
 * 2. 将媒体流绑定到 video 元素
 * 3. 建立 WebSocket 连接
 */
async function startCamera() {
  try {
    isConnecting.value = true

    // 1. 获取摄像头权限（320x240 低分辨率优化）
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: { width: 320, height: 240, facingMode: 'environment' },
      audio: false,
    })

    // 2. 将媒体流绑定到隐藏的 video 元素
    videoRef.value.srcObject = mediaStream
    await videoRef.value.play()

    // 3. 建立 WebSocket 连接
    connectWebSocket()

    isRunning.value = true
    ElMessage.success('摄像头已开启')
  } catch (err) {
    console.error('[摄像头开启失败]', err)
    ElMessage.error(`摄像头开启失败: ${err.message}`)
    isConnecting.value = false
  }
}

// ── 建立 WebSocket 连接 ──

/**
 * 建立 WebSocket 连接，发送配置消息并接收检测结果
 * 使用 ws:// 或 wss:// 协议，从 localStorage 获取 token 进行认证
 */
function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const token = localStorage.getItem('rsod_token') || localStorage.getItem('token')
  const wsUrl = `${protocol}//${host}/api/detection/camera?token=${token}`

  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    console.log('[WebSocket] 连接已建立')
    _reconnectAttempts = 0  // 重置重连计数

    // 发送 config 配置消息
    // CPU 模式 image_size=320（优化），GPU 模式 image_size=640
    const imageSize = detectMode.value === 'cpu' ? 320 : 640
    ws.send(JSON.stringify({
      type: 'config',
      mode: detectMode.value,
      conf: confThreshold.value,
      iou: 0.45,
      image_size: imageSize,
      scene_id: 1,
    }))
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)

      if (data.type === 'result') {
        // 更新统计信息
        currentFps.value = data.fps || 0
        frameCount.value = data.frame_count || 0
        inferenceTime.value = data.inference_time || 0
        objectCount.value = data.object_count || 0
        currentDetections.value = (data.detections || []).map(d => ({ ...d, _uid: ++_uidCounter }))

        // 渲染标注帧到 Canvas
        if (data.annotated_frame) {
          renderAnnotatedFrame(data.annotated_frame)
        }

        // 火情预警数据
        fireLevel.value = data.fire_level || 'safe'
        fireCount.value = data.fire_count || 0
        smokeCount.value = data.smoke_count || 0
        lastAlertTime.value = new Date().toLocaleTimeString()

        // 火情预警通知
        const fireLevel = data.fire_level || ''
        if (fireLevel !== lastFireLevel && ['notice', 'warning', 'danger'].includes(fireLevel)) {
          lastFireLevel = fireLevel
          const levelMap = { notice: '注意', warning: '警告', danger: '危险' }
          ElNotification({
            title: '火情预警',
            message: `检测到 ${data.object_count || 0} 个目标，火情等级：${levelMap[fireLevel] || fireLevel}`,
            type: 'warning',
            duration: 5000,
          })
        }
      } else if (data.type === 'config_ok') {
        console.log('[WebSocket] 配置确认:', data.message)
        // 响应驱动：收到 config_ok 后发送第一帧
        requestAnimationFrame(sendSingleFrame)
      } else if (data.type === 'error') {
        console.error('[WebSocket] 服务端错误:', data.message)
        ElMessage.error(data.message)
      }
    } catch (err) {
      console.error('[WebSocket] 消息解析失败:', err)
    }
  }

  ws.onclose = () => {
    console.log('[WebSocket] 连接已关闭')
    isConnecting.value = false
    // 非主动关闭时尝试重连
    if (isRunning.value && _reconnectAttempts < _MAX_RECONNECT_ATTEMPTS) {
      const delay = _RECONNECT_BASE_DELAY * Math.pow(2, _reconnectAttempts)
      _reconnectAttempts++
      console.log(`[WebSocket] 将在 ${delay}ms 后尝试第 ${_reconnectAttempts} 次重连...`)
      _reconnectTimer = setTimeout(() => {
        if (isRunning.value) {
          connectWebSocket()
        }
      }, delay)
    }
  }

  ws.onerror = (err) => {
    console.error('[WebSocket] 连接错误:', err)
    isConnecting.value = false
  }
}

// ── 发送单帧（响应驱动，收到 result 渲染后调用） ──

/**
 * 发送单帧到后端进行检测
 * 从 video 元素捕获当前帧，使用编码 Canvas 压缩为 JPEG（0.45 质量），
 * 通过 WebSocket 发送 base64 编码的帧数据
 * 采用响应驱动模式：收到 result 渲染完成后才发送下一帧
 */
function sendSingleFrame() {
  if (!ws || ws.readyState !== WebSocket.OPEN) return
  if (!videoRef.value || videoRef.value.readyState < 2) return

  const encodeCanvas = encodeCanvasRef.value
  const targetSize = detectMode.value === 'cpu' ? 320 : 640

  // 复用编码 Canvas，调整尺寸
  encodeCanvas.width = targetSize
  encodeCanvas.height = targetSize
  const ctx = encodeCanvas.getContext('2d')

  // 居中裁剪绘制
  const vw = videoRef.value.videoWidth
  const vh = videoRef.value.videoHeight
  const scale = Math.min(targetSize / vw, targetSize / vh)
  const x = (targetSize - vw * scale) / 2
  const y = (targetSize - vh * scale) / 2
  ctx.drawImage(videoRef.value, x, y, vw * scale, vh * scale)

  // JPEG 0.45 压缩
  const dataUrl = encodeCanvas.toDataURL('image/jpeg', 0.45)
  const base64Data = dataUrl.split(',')[1]

  ws.send(JSON.stringify({
    type: 'frame',
    data: base64Data,
    timestamp: Date.now(),
  }))
}

// ── 渲染标注帧到 Canvas ──

/**
 * 渲染后端返回的标注帧到 Canvas
 * 将 base64 编码的 JPEG 图片绘制到可见的 Canvas 上，
 * 渲染完成后触发下一帧发送（响应驱动模式）
 * @param {string} annotatedBase64 - 后端返回的标注帧 base64 数据
 */
function renderAnnotatedFrame(annotatedBase64) {
  if (!canvasRef.value) return

  const img = new Image()
  img.onload = () => {
    const canvas = canvasRef.value
    const ctx = canvas.getContext('2d')
    canvas.width = img.width
    canvas.height = img.height
    ctx.drawImage(img, 0, 0)

    // 响应驱动：渲染完成后发送下一帧
    requestAnimationFrame(sendSingleFrame)
  }
  img.src = `data:image/jpeg;base64,${annotatedBase64}`
}

// ── 停止摄像头 ──

/**
 * 停止摄像头检测
 * 关闭 WebSocket 连接、释放摄像头媒体流、重置所有状态变量
 */
function stopCamera() {
  // 清除重连定时器
  if (_reconnectTimer) {
    clearTimeout(_reconnectTimer)
    _reconnectTimer = null
  }
  _reconnectAttempts = 0

  // 关闭 WebSocket
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'close' }))
    ws.close()
    ws = null
  }

  // 停止摄像头
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop())
    mediaStream = null
  }

  if (videoRef.value) {
    videoRef.value.srcObject = null
  }

  // 重置状态
  isRunning.value = false
  isConnecting.value = false
  currentFps.value = 0
  frameCount.value = 0
  inferenceTime.value = 0
  objectCount.value = 0
  currentDetections.value = []
  lastFireLevel = 'safe'

  // 清空 Canvas
  if (canvasRef.value) {
    const ctx = canvasRef.value.getContext('2d')
    ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
  }

  ElMessage.info('摄像头已停止')
}

// ── 生成报告 ──

/**
 * 生成当前检测报告
 * 汇总实时检测数据（目标数、FPS、推理耗时、火情等级等），
 * 以对话框形式展示，支持一键复制到剪贴板
 */
function generateReport() {
  const lines = [
    '===== 摄像头检测报告 =====',
    `生成时间：${new Date().toLocaleString()}`,
    `检测模式：${detectMode.value === 'cpu' ? 'CPU 节能' : 'GPU 加速'}`,
    `置信度阈值：${confThreshold.value}`,
    '',
    '--- 实时统计 ---',
    `当前目标数：${objectCount.value}`,
    `实时 FPS：${currentFps.value}`,
    `推理耗时：${inferenceTime.value}ms`,
    `已处理帧：${frameCount.value}`,
    '',
    '--- 火情预警 ---',
    `火情等级：${alertLevelText.value}`,
    `火情目标：${fireCount.value} 个`,
    `烟雾目标：${smokeCount.value} 个`,
    '',
    '--- 当前帧目标列表 ---',
  ]
  if (currentDetections.value.length > 0) {
    for (const det of currentDetections.value) {
      const name = det.class_name || det.class || det.name || 'unknown'
      lines.push(`  ${name}: 置信度 ${Math.round((det.confidence || 0) * 100)}%, bbox [${(det.bbox || []).map(v => Math.round(v)).join(', ')}]`)
    }
  } else {
    lines.push('  暂无检测目标')
  }
  lines.push('')
  lines.push('--- 类别分布 ---')
  const dist = classDistribution.value
  if (Object.keys(dist).length > 0) {
    for (const [name, count] of Object.entries(dist)) {
      lines.push(`  ${name}: ${count}`)
    }
  } else {
    lines.push('  暂无数据')
  }
  const reportText = lines.join('\n')

  ElMessageBox.alert(reportText, '检测报告', {
    confirmButtonText: '复制报告',
    dangerouslyUseHTMLString: false,
    customClass: 'report-dialog',
    callback: (action) => {
      if (action === 'confirm') {
        navigator.clipboard.writeText(reportText).then(() => {
          ElMessage.success('报告已复制到剪贴板')
        }).catch(() => {
          ElMessage.info('请手动复制报告内容')
        })
      }
    }
  })
}

// ── 组件销毁时清理 ──
onBeforeUnmount(() => {
  stopCamera()
})
</script>

<style lang="scss" scoped>
.detection-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
  background: #f5f5f5;
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

/* 左侧预览区 */
.preview-panel {
  flex: 3;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.video-wrapper {
  position: relative;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-canvas {
  width: 100%;
  height: auto;
  display: block;
}

.placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 16px;
}

.video-stats {
  display: flex;
  gap: 8px;
}

/* 右侧结果区 */
.result-panel {
  flex: 2;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.stat-item {
  text-align: center;
  padding: 12px;
  background: #f9f9f9;
  border-radius: 8px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #409eff;
}

.stat-label {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.empty-state {
  text-align: center;
  color: #999;
  padding: 20px;
}

.detection-list {
  max-height: 300px;
  overflow-y: auto;
}

.detection-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;

  &:last-child {
    border-bottom: none;
  }
}

.det-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.det-class {
  font-weight: 600;
  min-width: 80px;
}

.det-bbox {
  font-size: 12px;
  color: #999;
  font-family: monospace;
}

.distribution-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.distribution-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: #f5f5f5;
  border-radius: 4px;
}

.class-name {
  font-weight: 500;
}

/* 火情预警卡片 */
.alert-card {
  margin-bottom: 12px;
  &.alert-safe { border-left: 3px solid #67c23a; }
  &.alert-notice { border-left: 3px solid #e6a23c; }
  &.alert-warning { border-left: 3px solid #e6a23c; }
  &.alert-danger { border-left: 3px solid #f56c6c; }
}
.alert-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.alert-row {
  display: flex;
  align-items: center;
}
.alert-label {
  color: #999;
  font-size: 13px;
  min-width: 80px;
}
.alert-value {
  font-weight: 600;
  font-size: 14px;
}

/* 控制栏 */
.control-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 0;
  border-top: 1px solid #e0e0e0;
  margin-top: 16px;
}

.control-label {
  font-size: 14px;
  color: #666;
  white-space: nowrap;
}
</style>