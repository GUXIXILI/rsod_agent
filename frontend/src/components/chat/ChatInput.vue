<template>
  <div class="chat-input-wrapper">
    <!-- 拖拽区域 -->
    <div
      class="drop-zone"
      :class="{ dragging: isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
    >
      <div v-if="isDragging" class="drop-overlay">
        <el-icon :size="40"><UploadFilled /></el-icon>
        <p>释放文件以添加</p>
      </div>

      <!-- 文件预览区 -->
      <div v-if="files.length > 0" class="file-preview">
        <div
          v-for="(file, idx) in files"
          :key="idx"
          :class="['file-chip', { 'is-image': file.type?.startsWith('image/') }]"
        >
          <img v-if="file.type?.startsWith('image/')" :src="file._preview" alt="" />
          <el-icon v-else class="file-icon"><Document /></el-icon>
          <span class="file-name">{{ file.name }}</span>
          <el-button
            class="file-remove"
            :icon="CircleClose"
            circle
            size="small"
            text
            title="移除文件"
            @click="removeFile(idx)"
          />
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="input-row">
        <el-button
          class="attach-btn"
          :icon="Link"
          circle
          :disabled="disabled"
          title="上传文件"
          @click="triggerFileInput"
        />
        <input
          ref="fileInputRef"
          type="file"
          accept="image/*,.zip,video/mp4,video/avi,video/quicktime"
          multiple
          style="display: none"
          @change="handleFileSelect"
        />

        <textarea
          ref="textareaRef"
          v-model="text"
          class="text-input"
          :placeholder="disabled ? 'AI 正在回复中...' : '输入消息，支持拖拽图片/ZIP/视频...'"
          :disabled="disabled"
          :rows="1"
          @keydown.enter.exact="handleEnter"
          @input="autoResize"
          @paste="handlePaste"
        ></textarea>

        <el-button
          class="camera-btn"
          :icon="Camera"
          circle
          :disabled="disabled"
          title="开启摄像头"
          @click="$emit('camera-toggle')"
        />

        <el-button
          v-if="!disabled"
          class="send-btn"
          type="primary"
          :icon="Promotion"
          circle
          :disabled="!canSend"
          title="发送消息"
          @click="handleSend"
        />
        <el-button
          v-else
          class="stop-btn"
          type="danger"
          :icon="VideoPause"
          circle
          title="停止生成"
          @click="$emit('stop')"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * ChatInput.vue — 聊天输入组件
 *
 * 功能：
 *   - 拖拽文件上传（图片/ZIP/视频）
 *   - 文件预览区（图片缩略图，其他文件显示类型图标）
 *   - 可移除已选文件
 *   - 多行 textarea，自动调整高度
 *   - 摄像头按钮
 *   - 发送/停止按钮
 *   - 支持 Ctrl+V 粘贴图片
 */
import { Camera, CircleClose, Document, Link, Promotion, UploadFilled, VideoPause } from '@element-plus/icons-vue'
import { computed, nextTick, ref } from 'vue'

const props = defineProps({
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['send', 'stop', 'camera-toggle'])

const text = ref('')
const files = ref([])
const fileInputRef = ref(null)
const textareaRef = ref(null)
const isDragging = ref(false)

const canSend = computed(() => {
  return text.value.trim() || files.value.length > 0
})

function triggerFileInput() {
  fileInputRef.value?.click()
}

function handleFileSelect(event) {
  addFiles(Array.from(event.target.files))
  event.target.value = ''
}

function handleDrop(event) {
  isDragging.value = false
  const droppedFiles = Array.from(event.dataTransfer.files)
  if (droppedFiles.length > 0) {
    addFiles(droppedFiles)
  }
}

function addFiles(newFiles) {
  newFiles.forEach((f) => {
    if (f.type?.startsWith('image/')) {
      f._preview = URL.createObjectURL(f)
    }
    files.value.push(f)
  })
}

function removeFile(idx) {
  const file = files.value[idx]
  if (file._preview) {
    URL.revokeObjectURL(file._preview)
  }
  files.value.splice(idx, 1)
}

function autoResize() {
  nextTick(() => {
    const el = textareaRef.value
    if (el) {
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 150) + 'px'
    }
  })
}

function handleEnter(event) {
  // Shift+Enter 换行，Enter 发送
  if (!event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}

function handlePaste(event) {
  const items = event.clipboardData?.items
  if (!items) return
  const imageFiles = []
  for (const item of items) {
    if (item.type?.startsWith('image/')) {
      const blob = item.getAsFile()
      if (blob) {
        const ext = item.type.split('/')[1] || 'png'
        const file = new File([blob], `paste-${Date.now()}.${ext}`, { type: item.type })
        imageFiles.push(file)
      }
    }
  }
  if (imageFiles.length > 0) {
    addFiles(imageFiles)
  }
}

function handleSend() {
  if (!canSend.value) return
  emit('send', {
    text: text.value.trim(),
    files: [...files.value],
  })
  // 清理
  files.value.forEach((f) => {
    if (f._preview) URL.revokeObjectURL(f._preview)
  })
  files.value = []
  text.value = ''
  nextTick(() => {
    const el = textareaRef.value
    if (el) {
      el.style.height = 'auto'
    }
  })
}

defineExpose({ clear: handleSend })
</script>

<style lang="scss" scoped>
.chat-input-wrapper {
  flex-shrink: 0;
}

.drop-zone {
  position: relative;
  background: #fff;
  border-top: 1px solid #e4e7ed;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.04);
  padding: 12px 16px;
  transition: border-color 0.2s;

  &.dragging {
    border-color: #409eff;
  }
}

.drop-overlay {
  position: absolute;
  inset: 0;
  background: rgba(64, 158, 255, 0.08);
  border: 2px dashed #409eff;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 10;
  color: #409eff;
  pointer-events: none;

  p {
    margin-top: 8px;
    font-size: 14px;
  }
}

.file-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.file-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  font-size: 12px;
  max-width: 200px;

  &.is-image {
    padding: 2px;
    background: transparent;
    border: 1px solid #e4e7ed;

    img {
      width: 48px;
      height: 48px;
      object-fit: cover;
      border-radius: 4px;
    }
  }
}

.file-icon {
  color: #909399;
  flex-shrink: 0;
}

.file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #606266;
}

.file-remove {
  flex-shrink: 0;
  padding: 2px;
  width: 18px;
  height: 18px;
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.text-input {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  font-size: 14px;
  line-height: 1.6;
  padding: 6px 0;
  max-height: 150px;
  font-family: inherit;
  color: #303133;
  background: transparent;

  &::placeholder {
    color: #c0c4cc;
  }

  &:disabled {
    background: transparent;
    cursor: not-allowed;
  }
}

.attach-btn,
.camera-btn,
.send-btn,
.stop-btn {
  flex-shrink: 0;
}
</style>