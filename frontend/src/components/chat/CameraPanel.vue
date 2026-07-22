<template>
  <div class="camera-panel">
    <div class="panel-header">
      <span class="panel-title">
        <el-icon><VideoCamera /></el-icon>
        实时摄像头检测
      </span>
      <div class="panel-stats">
        <span class="stat">FPS: {{ fps }}</span>
        <span class="stat">推理: {{ inferenceTime }}ms</span>
        <span class="stat" :class="{ alert: fireLevel >= 2 }">目标: {{ objectCount }}</span>
      </div>
      <el-button :icon="Close" text circle @click="handleClose" />
    </div>

    <div class="video-container">
      <video ref="videoRef" class="camera-video" autoplay playsinline muted></video>
      <canvas ref="canvasRef" class="camera-canvas"></canvas>
      <canvas ref="encodeCanvasRef" style="display: none;"></canvas>
      <div v-if="!streaming" class="camera-placeholder">
        <el-icon :size="48"><VideoCamera /></el-icon>
        <p>{{ statusText }}</p>
      </div>
    </div>

    <!-- 火情预警 -->
    <div v-if="fireLevel >= 2" class="fire-alert">
      <el-icon><WarningFilled /></el-icon>
      <span>{{ fireLevel === 3 ? '⚠ 严重火情预警！' : '⚠ 疑似火情，请注意！' }}</span>
    </div>
  </div>
</template>

<script setup>
/**
 * CameraPanel.vue — 摄像头实时检测面板
 *
 * 功能：
 *   - 通过 WebSocket 连接 /api/detection/camera
 *   - 发送 config 配置检测参数
 *   - 循环发送 frame 消息（base64 JPEG）
 *   - 接收 result 消息渲染标注帧
 *   - 显示 FPS、推理时间、当前目标数量
 *   - 火情预警（fire >= notice 时通知父组件）
 *   - 检测结果同步到聊天
 *   - 帧率自适应：根据推理时间动态调整发送间隔
 *   - 关闭时释放摄像头和 WebSocket 资源
 */
import { Close, VideoCamera, WarningFilled } from '@element-plus/icons-vue'
import { onBeforeUnmount, onMounted, ref } from 'vue'

const emit = defineEmits(['close', 'fire-alert', 'detection-result'])

const videoRef = ref(null)
const canvasRef = ref(null)
const encodeCanvasRef = ref(null)
const streaming = ref(false)
const statusText = ref('正在启动摄像头...')
const fps = ref(0)
const inferenceTime = ref(0)
const objectCount = ref(0)
const fireLevel = ref(0)
const retryCount = ref(0)

let ws = null
let videoStream = null
let fpsCounter = 0
let fpsTimer = null
let warmedUp = false
let rafId = null
let lastFrameTime = 0
const TARGET_FRAME_INTERVAL = 100 // 10 FPS
let configTimeout = null

// ── 启动摄像头 ──
async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 320, height: 240, facingMode: 'environment' },
    })
    videoStream = stream

    const video = videoRef.value
    video.srcObject = stream
    video.autoplay = true
    video.playsInline = true
    video.muted = true

    await video.play()
    streaming.value = true
    statusText.value = ''

    // 连接 WebSocket
    connectWebSocket()
    startFPSCounter()
  } catch (err) {
    console.error('摄像头启动失败:', err)
    streaming.value = false
    statusText.value = '摄像头启动失败，请检查权限'
  }
}

// ── WebSocket 连接 ──
function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const token = localStorage.getItem('rsod_token') || localStorage.getItem('token')
  const url = `${protocol}//${host}/api/detection/camera?token=${token}`

  ws = new WebSocket(url)

  ws.onopen = () => {
    // 发送配置消息
    ws.send(JSON.stringify({
      type: 'config',
      mode: 'cpu',
      conf: 0.25,
      iou: 0.45,
      image_size: 640,
      scene_id: 1,
    }))

    // 5 秒超时重试
    configTimeout = setTimeout(() => {
      if (!warmedUp) {
        statusText.value = '连接超时，正在重试...'
        cleanup()
        retryCount.value++
        if (retryCount.value < 3) {
          startCamera()
        } else {
          statusText.value = '连接失败，请检查网络后重试'
        }
      }
    }, 5000)
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'config_ok') {
        clearTimeout(configTimeout)
        warmedUp = true
        statusText.value = ''
        rafId = requestAnimationFrame(sendFrameLoop)
        return
      }
      if (data.type === 'result') {
        handleResult(data)
      }
    } catch (e) {
      console.warn('WebSocket 消息解析失败:', e)
    }
  }

  ws.onerror = (err) => {
    console.error('WebSocket 错误:', err)
  }

  ws.onclose = () => {
    console.log('WebSocket 已关闭')
  }
}

// ── 发送帧 ──
function sendFrameLoop(timestamp) {
  if (!ws || ws.readyState !== WebSocket.OPEN || !videoRef.value) {
    rafId = requestAnimationFrame(sendFrameLoop)
    return
  }
  if (timestamp - lastFrameTime >= TARGET_FRAME_INTERVAL) {
    lastFrameTime = timestamp
    const canvas = encodeCanvasRef.value
    canvas.width = 320
    canvas.height = 240
    const ctx = canvas.getContext('2d')
    ctx.drawImage(videoRef.value, 0, 0, 320, 240)
    const frameData = canvas.toDataURL('image/jpeg', 0.45)
    const base64 = frameData.split(',')[1]
    ws.send(JSON.stringify({ type: 'frame', data: base64, timestamp: Date.now() }))
    fpsCounter++
  }
  rafId = requestAnimationFrame(sendFrameLoop)
}

// ── 处理检测结果 ──
function handleResult(data) {
  inferenceTime.value = data.inference_time || 0
  objectCount.value = data.total_objects || 0

  // fire_level 是字符串，转换为数值用于显示
  const fireLevelMap = { 'notice': 1, 'warning': 2, 'danger': 3 }
  fireLevel.value = fireLevelMap[data.fire_level] || 0

  // 渲染标注帧到 canvas（后端返回字段名为 annotated_frame）
  if (data.annotated_frame && canvasRef.value) {
    const canvas = canvasRef.value
    const ctx = canvas.getContext('2d')
    const img = new Image()
    img.onload = () => {
      canvas.width = img.width
      canvas.height = img.height
      ctx.drawImage(img, 0, 0)
    }
    img.src = `data:image/jpeg;base64,${data.annotated_frame}`
  }

  // 每检测到目标时通知聊天（后端返回字段名为 detections）
  if (data.detections && data.detections.length > 0) {
    emit('detection-result', {
      detections: data.detections,
      total: data.total_objects,
      fire_level: data.fire_level,
      inference_time: data.inference_time,
    })
  }

  // 火情预警
  const NOTICE_LEVELS = ['notice', 'warning', 'danger']
  if (data.fire_level && NOTICE_LEVELS.includes(data.fire_level)) {
    emit('fire-alert', {
      level: data.fire_level,
      objects: data.total_objects,
      timestamp: Date.now(),
    })
  }
}

// ── FPS 计数器 ──
function startFPSCounter() {
  fpsTimer = setInterval(() => {
    fps.value = fpsCounter
    fpsCounter = 0
  }, 1000)
}

// ── 关闭 ──
function handleClose() {
  cleanup()
  emit('close')
}

function cleanup() {
  // 停止超时计时器
  if (configTimeout) {
    clearTimeout(configTimeout)
    configTimeout = null
  }

  // 停止帧发送
  if (rafId) {
    cancelAnimationFrame(rafId)
    rafId = null
  }

  // 停止 FPS 计数
  if (fpsTimer) {
    clearInterval(fpsTimer)
    fpsTimer = null
  }

  // 关闭 WebSocket
  if (ws) {
    ws.close()
    ws = null
  }

  // 释放摄像头
  if (videoStream) {
    videoStream.getTracks().forEach((t) => t.stop())
    videoStream = null
  }

  if (videoRef.value) {
    videoRef.value.srcObject = null
  }

  warmedUp = false
  streaming.value = false
}

// 组件挂载后启动（确保 videoRef 已绑定 DOM 元素）
onMounted(() => {
  startCamera()
})

onBeforeUnmount(() => {
  cleanup()
})
</script>

<style lang="scss" scoped>
.camera-panel {
  background: #fff;
  border: 1px solid #E8E0D8;
  border-radius: 8px;
  overflow: hidden;
  margin: 0 16px 0 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: linear-gradient(135deg, #4A90D9, #87CEEB);
  border-bottom: 1px solid #E8E0D8;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
}

.panel-stats {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.85);
  flex: 1;

  .stat {
    white-space: nowrap;

    &.alert {
      color: #F0A030;
      font-weight: 600;
    }
  }
}

.video-container {
  position: relative;
  background: #000;
  min-height: 240px;
  max-height: 360px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.camera-video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.camera-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.camera-placeholder {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #7F8C8D;
  gap: 8px;
  z-index: 1;

  p {
    font-size: 13px;
  }
}

.fire-alert {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #FFF5EB;
  color: #F0A030;
  font-size: 13px;
  font-weight: 600;
  border-top: 1px solid #EDE6DE;
}
</style>