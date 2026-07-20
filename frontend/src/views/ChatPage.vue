<template>
  <div class="chat-page">
    <!-- ── 左侧会话列表 ── -->
    <ChatSidebar
      :sessions="agentStore.sessions"
      :current-session-id="agentStore.currentSessionId"
      @new-chat="handleNewSession"
      @switch-session="handleSwitchSession"
      @delete-session="handleDeleteSession"
      @rename-session="handleRenameSession"
    />

    <!-- ── 主对话区域 ── -->
    <div class="chat-main">
      <!-- 顶部栏：当前会话标题 + 操作 -->
      <div class="chat-header">
        <div class="header-left">
          <span class="header-title">{{ currentSessionTitle }}</span>
        </div>
        <div class="header-actions">
          <el-button
            size="small"
            :disabled="agentStore.isLoading"
            @click="handleQuickDetect('single')"
          >
            <el-icon><Picture /></el-icon>
            图片检测
          </el-button>
          <el-button
            size="small"
            :disabled="agentStore.isLoading"
            @click="handleQuickDetect('batch')"
          >
            <el-icon><Folder /></el-icon>
            批量检测
          </el-button>
          <el-button
            size="small"
            :disabled="agentStore.isLoading"
            @click="handleVideoDetect"
          >
            <el-icon><VideoCamera /></el-icon>
            视频检测
          </el-button>
        </div>
      </div>

      <!-- 消息列表 -->
      <div class="message-list" ref="messageListRef">
        <!-- 欢迎消息（无会话时） -->
        <div v-if="agentStore.messages.length === 0" class="welcome-area">
          <div class="welcome-icon">
            <el-icon :size="56"><ChatDotRound /></el-icon>
          </div>
          <h2>你好！我是火灾烟雾智能检测智能体</h2>
          <p class="welcome-desc">上传图片或视频，我可以帮你检测火情和烟雾目标</p>
          <div class="welcome-tips">
            <div class="tip-item" @click="inputTextPlaceholder = '检测一下这张图片中的火情'">
              <el-icon><Picture /></el-icon>
              <span>图片检测</span>
            </div>
            <div class="tip-item" @click="inputTextPlaceholder = '帮我分析这段视频中的烟雾'">
              <el-icon><VideoCamera /></el-icon>
              <span>视频检测</span>
            </div>
            <div class="tip-item" @click="inputTextPlaceholder = '批量检测这个 ZIP 中的图片'">
              <el-icon><Folder /></el-icon>
              <span>批量检测</span>
            </div>
          </div>
        </div>

        <!-- 消息项 -->
        <div
          v-for="(msg, index) in agentStore.messages"
          :key="index"
          :class="['message-item', `message-${msg.role}`]"
        >
          <!-- 用户消息 -->
          <div v-if="msg.role === 'user'" class="message-wrapper message-user-wrapper">
            <div class="message-bubble user-bubble">
              <div v-if="msg.content" class="message-content">{{ msg.content }}</div>
              <!-- 单张图片附件 -->
              <div v-if="msg.imagePreview" class="message-attachment">
                <img :src="msg.imagePreview" alt="附件图片" />
              </div>
              <!-- 多图附件 -->
              <div v-if="msg.images && msg.images.length" class="message-attachments-grid">
                <img v-for="(src, i) in msg.images" :key="i" :src="src" alt="附件图片" />
              </div>
            </div>
          </div>

          <!-- AI 消息 -->
          <div v-else-if="msg.role === 'assistant'" class="message-wrapper message-assistant-wrapper">
            <div class="message-bubble assistant-bubble">
              <!-- 思考中动画 -->
              <div v-if="msg.thinking" class="thinking-indicator">
                <div class="thinking-dots">
                  <span></span><span></span><span></span>
                </div>
                <span class="thinking-text">{{ msg.thinkingContent || '正在思考中...' }}</span>
              </div>

              <!-- 打字中动画 -->
              <div v-else-if="msg.loading && !msg.thinking" class="typing-indicator">
                <span></span><span></span><span></span>
              </div>

              <!-- Markdown 渲染 -->
              <div
                v-if="!msg.loading && msg.content && !msg.thinking"
                class="message-content markdown-body"
                v-html="renderMarkdown(msg.content)"
              ></div>

              <!-- 流式文本 -->
              <div
                v-if="msg.loading && msg.content && !msg.thinking"
                class="message-content streaming-text"
              >{{ msg.content }}</div>

              <!-- 工具调用时间线 -->
              <div v-if="msg.toolCalls && msg.toolCalls.length > 0" class="tool-timeline">
                <div
                  v-for="(tc, tIdx) in msg.toolCalls"
                  :key="tIdx"
                  :class="['tool-timeline-item', `tool-status-${tc.status}`]"
                >
                  <div v-if="tc.status === 'running'" class="tool-loading">
                    <el-icon class="is-loading"><Loading /></el-icon>
                    <span>正在调用工具：{{ tc.tool }}</span>
                  </div>
                  <div v-else-if="tc.status === 'completed'" class="tool-completed">
                    <el-icon color="#67c23a"><CircleCheck /></el-icon>
                    <span>工具 {{ tc.tool }} 执行完成</span>
                    <el-popover
                      v-if="tc.resultSummary"
                      placement="right"
                      :width="300"
                      trigger="click"
                    >
                      <template #reference>
                        <el-button text size="small" type="primary">查看详情</el-button>
                      </template>
                      <div class="tool-result-detail">{{ tc.resultSummary }}</div>
                    </el-popover>
                  </div>
                  <div v-else-if="tc.status === 'failed'" class="tool-failed">
                    <el-icon color="#f56c6c"><CircleClose /></el-icon>
                    <span>工具 {{ tc.tool }} 调用失败</span>
                  </div>
                </div>
              </div>

              <!-- 多Agent调用链 -->
              <div v-if="msg.agentChain && msg.agentChain.length > 0" class="agent-chain">
                <div class="agent-chain-title">智能体调用链</div>
                <div class="agent-chain-steps">
                  <span
                    v-for="(step, sIdx) in msg.agentChain"
                    :key="sIdx"
                    :class="['agent-chain-step', `agent-chain-step-${step.status}`]"
                  >
                    {{ step.current }}
                    <span v-if="sIdx < msg.agentChain.length - 1" class="agent-chain-arrow">→</span>
                  </span>
                </div>
              </div>

              <!-- 知识来源 -->
              <div v-if="msg.knowledgeSources && msg.knowledgeSources.length > 0" class="knowledge-sources">
                <div class="knowledge-sources-title">知识来源</div>
                <div
                  v-for="(source, kIdx) in msg.knowledgeSources"
                  :key="kIdx"
                  class="knowledge-source-item"
                >
                  <span class="knowledge-source-name">{{ source.title || source.source }}</span>
                  <span class="knowledge-source-similarity">
                    相似度: {{ (source.similarity * 100).toFixed(0) }}%
                  </span>
                </div>
              </div>

              <!-- 错误 + 重试 -->
              <div v-if="msg.error" class="error-actions">
                <el-button type="warning" size="small" @click="retryLastMessage">
                  <el-icon><Refresh /></el-icon> 重试
                </el-button>
              </div>

              <!-- 检测结果卡片 -->
              <DetectionResultCard
                v-if="msg.detectionResult"
                :result="msg.detectionResult"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- 底部输入区 -->
      <ChatInput
        :disabled="agentStore.isLoading"
        @send="handleSend"
        @stop="handleStop"
      />
    </div>
  </div>
</template>

<script setup>
/**
 * ChatPage.vue — 豆包风格全屏聊天界面
 *
 * 功能：
 *   - 左侧会话列表（可折叠）
 *   - 消息气泡（用户/AI 区分，Markdown 渲染）
 *   - 完整 SSE 事件协议（thinking/tool_start/tool_end/text_chunk/done/error）
 *   - 检测结果卡片 + 工具调用时间线
 *   - 快捷操作（单图/批量/视频检测）
 *   - 拖拽文件 + 文字输入 + 发送
 *   - 重试、停止生成
 */
import ChatInput from '@/components/chat/ChatInput.vue'
import ChatSidebar from '@/components/chat/ChatSidebar.vue'
import DetectionResultCard from '@/components/DetectionResultCard.vue'
import { useAgentStore } from '@/stores/agent'
import request from '@/utils/request'
import { renderMarkdown } from '@/utils/markdown'
import { streamChat } from '@/utils/stream'
import { detectBatch, detectSingle, detectVideo, detectZip, getVideoStatus } from '@/api/detection'
import { ChatDotRound, CircleCheck, CircleClose, Folder, Loading, Picture, Refresh, VideoCamera } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, nextTick, onMounted, ref } from 'vue'

// ── Store ──
const agentStore = useAgentStore()

// ── 响应式状态 ──
const messageListRef = ref(null)
const inputTextPlaceholder = ref('')

// 重试用
const lastSentMessage = ref('')
const lastSentImage = ref(null)
const lastSentFiles = ref([])

// ── 计算属性 ──
const currentSessionTitle = computed(() => {
  if (!agentStore.currentSessionId) return '新对话'
  const session = agentStore.sessions.find((s) => s.id === agentStore.currentSessionId)
  return session?.title || '新对话'
})

// ── 会话管理 ──
function handleNewSession() {
  agentStore.newChat()
}

async function handleSwitchSession(sessionId) {
  await agentStore.switchSession(sessionId)
  scrollToBottom()
}

async function handleDeleteSession(sessionId) {
  await agentStore.deleteSession(sessionId)
}

async function handleRenameSession(sessionId, title) {
  try {
    await agentStore.renameSession(sessionId, title)
    ElMessage.success('重命名成功')
  } catch (err) {
    ElMessage.error('重命名失败: ' + (err.response?.data?.detail || err.message || '未知错误'))
  }
}

// ── 发送消息 ──
async function handleSend({ text, files }) {
  if (!text && (!files || files.length === 0)) return

  const message = text || ''

  // 参数校验：content 长度不能超过 5000 字符
  if (message.length > 5000) {
    ElMessage.warning(`消息内容过长（${message.length}/5000），请精简后重试`)
    return
  }
  let uploadedFiles = []

  // Step 1: 如果有文件，先上传到后端
  if (files && files.length > 0) {
    ElMessage.info(`正在上传 ${files.length} 个文件...`)
    try {
      for (const file of files) {
        const formData = new FormData()
        formData.append('file', file)
        const res = await request.post('/chat/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
        uploadedFiles.push(res.data) // {url, type, name}
      }
      ElMessage.success(`文件上传完成 (${uploadedFiles.length} 个)`)
    } catch (err) {
      ElMessage.error('文件上传失败: ' + (err.response?.data?.detail || err.message || '未知错误'))
      return
    }
  }

  // Step 2: 添加用户消息（含文件预览）
  lastSentMessage.value = message
  lastSentImage.value = (files && files.length > 0) ? files[0] : null
  lastSentFiles.value = uploadedFiles

  const userMsg = {
    role: 'user',
    content: message,
  }

  if (files && files.length > 0) {
    const imageFiles = files.filter(f => f.type?.startsWith('image/'))
    // 单张图片预览
    if (imageFiles.length === 1) {
      userMsg.image = imageFiles[0].name
      userMsg.imagePreview = URL.createObjectURL(imageFiles[0])
    }
    // 多图预览
    else if (imageFiles.length > 1) {
      userMsg.images = imageFiles.map(f => URL.createObjectURL(f))
    }
    // 如果只有非图片文件且没有文字，用文件名填充消息内容
    if (imageFiles.length < files.length && !message) {
      const fileNames = files.map(f => f.name).join(', ')
      userMsg.content = `[文件] ${fileNames}`
    }
  }

  agentStore.addMessage(userMsg)

  // Step 3: 添加 AI 加载占位
  agentStore.addMessage({
    role: 'assistant',
    content: '',
    loading: true,
    toolCalls: [],
  })

  agentStore.setLoading(true)
  scrollToBottom()

  // Step 4: 构造请求体并发起 SSE
  const requestBody = { content: message }
  if (uploadedFiles.length > 0) {
    requestBody.files = uploadedFiles
  }
  if (agentStore.currentSessionId) {
    requestBody.session_id = agentStore.currentSessionId
  }

  let fullContent = ''

  const stop = streamChat('/api/chat/messages/stream', requestBody, {
    onMessage: (data) => {
      const lastMsg = agentStore.getLastAssistantMessage()
      if (!lastMsg) return

      switch (data.type) {
        case 'thinking':
          if (data.session_id && !agentStore.currentSessionId) {
            agentStore.currentSessionId = data.session_id
          }
          lastMsg.thinking = true
          lastMsg.thinkingContent = data.content || '正在分析问题...'
          lastMsg.loading = true
          break

        case 'tool_start': {
          lastMsg.thinking = false
          lastMsg.loading = true
          if (!lastMsg.toolCalls) lastMsg.toolCalls = []
          lastMsg.toolCalls.push({
            tool: data.tool || '未知工具',
            input: data.input || data.args,
            status: 'running',
            startTime: Date.now(),
          })
          break
        }

        case 'tool_end': {
          if (lastMsg.toolCalls && lastMsg.toolCalls.length > 0) {
            const runningTc = [...lastMsg.toolCalls].reverse().find((tc) => tc.status === 'running')
            if (runningTc) {
              runningTc.status = 'completed'
              runningTc.result = data.result
              try {
                const result = data.result ? JSON.parse(data.result) : {}
                if (result.error) {
                  runningTc.status = 'failed'
                  runningTc.resultSummary = result.error
                  const errorText = `检测失败：${result.error}`
                  lastMsg.content = lastMsg.content ? `${lastMsg.content}\n${errorText}` : errorText
                  lastMsg.loading = false
                } else if (Array.isArray(result.detections)) {
                  runningTc.resultSummary = `检测到 ${(result.fire_object_count || 0) + (result.smoke_object_count || 0)} 个目标`
                  lastMsg.detectionResult = result
                  lastMsg.loading = false
                } else {
                  runningTc.resultSummary = JSON.stringify(result).substring(0, 200)
                }
              } catch (parseErr) {
                // 工具返回非 JSON 格式（如纯文本），直接展示原文
                runningTc.status = 'completed'
                runningTc.resultSummary = (data.result || '').substring(0, 200)
                console.warn('[tool_end] JSON解析失败，以纯文本展示:', (data.result || '').substring(0, 100))
              }
            }
          }
          lastMsg.toolCall = { tool: data.tool, result: data.result }
          break
        }

        case 'text_chunk':
          lastMsg.thinking = false
          lastMsg.loading = true
          fullContent += data.content || ''
          lastMsg.content = fullContent
          break

        case 'done':
          if (data.session_id && !agentStore.currentSessionId) {
            agentStore.currentSessionId = data.session_id
          }
          if (data.response && !fullContent) {
            lastMsg.content = data.response
          }
          lastMsg.loading = false
          lastMsg.thinking = false
          agentStore.setLoading(false)
          agentStore.fetchSessions()
          break

        case 'error':
          lastMsg.content = data.content || '处理请求时发生错误'
          lastMsg.loading = false
          lastMsg.thinking = false
          lastMsg.error = true
          agentStore.setLoading(false)
          break

        case 'tool_call':
          lastMsg.thinking = false
          lastMsg.loading = true
          lastMsg.toolCall = { tool: data.tool, input: data.input || data.args }
          if (!lastMsg.toolCalls) lastMsg.toolCalls = []
          lastMsg.toolCalls.push({
            tool: data.tool,
            input: data.input || data.args,
            status: 'running',
            startTime: Date.now(),
          })
          break

        case 'tool_result': {
          let toolResult = null
          if (lastMsg.toolCalls && lastMsg.toolCalls.length > 0) {
            const runningTc = [...lastMsg.toolCalls].reverse().find((tc) => tc.status === 'running')
            if (runningTc) {
              runningTc.status = 'completed'
              runningTc.result = data.result
              toolResult = runningTc
            }
          }
          try {
            const result = data.result ? JSON.parse(data.result) : {}
            if (result.error) {
              if (toolResult) toolResult.status = 'failed'
              const errorText = `检测失败：${result.error}`
              lastMsg.content = lastMsg.content ? `${lastMsg.content}\n${errorText}` : errorText
              lastMsg.loading = false
            } else if (Array.isArray(result.detections)) {
              if (toolResult) {
                toolResult.resultSummary = `检测到 ${(result.fire_object_count || 0) + (result.smoke_object_count || 0)} 个目标`
              }
              lastMsg.detectionResult = result
              lastMsg.loading = false
            } else if (toolResult) {
              toolResult.resultSummary = JSON.stringify(result).substring(0, 200)
            }
          } catch (parseErr) {
            if (toolResult) {
              toolResult.status = 'completed'
              toolResult.resultSummary = (data.result || '').substring(0, 200)
            }
            console.warn('[tool_result] JSON解析失败，以纯文本展示:', (data.result || '').substring(0, 100))
          }
          break
        }

        case 'agent_chain':
          // 多Agent调用链事件
          if (!lastMsg.agentChain) lastMsg.agentChain = []
          lastMsg.agentChain.push({
            current: data.current,
            status: data.status,
            timestamp: Date.now(),
          })
          break

        case 'knowledge_sources':
          // 知识来源事件
          if (data.sources && Array.isArray(data.sources)) {
            lastMsg.knowledgeSources = data.sources
          }
          break

        default:
          if (data.content) {
            lastMsg.thinking = false
            lastMsg.loading = true
            fullContent += data.content
            lastMsg.content = fullContent
          }
          break
      }

      scrollToBottom()
    },

    onDone: () => {
      const lastMsg = agentStore.getLastAssistantMessage()
      if (lastMsg) {
        if (lastMsg.loading && !lastMsg.content && !lastMsg.detectionResult) {
          lastMsg.content = '处理完成。'
        }
        lastMsg.loading = false
        lastMsg.thinking = false
      }
      agentStore.setLoading(false)
      agentStore.abortController = null
      scrollToBottom()
    },

    onError: (err) => {
      const lastMsg = agentStore.getLastAssistantMessage()
      if (lastMsg) {
        lastMsg.content = `抱歉，处理出错了：${err.message}`
        lastMsg.loading = false
        lastMsg.thinking = false
        lastMsg.error = true
      }
      agentStore.setLoading(false)
      agentStore.abortController = null
      ElMessage.error('对话请求失败，请重试')
    },
  })

  agentStore.abortController = stop
}

// ── 重试 ──
async function retryLastMessage() {
  if (!lastSentMessage.value && !lastSentImage.value) {
    ElMessage.warning('没有可重试的消息')
    return
  }
  // 移除 AI 错误消息
  const lastMsg = agentStore.getLastAssistantMessage()
  if (lastMsg && lastMsg.error) {
    const idx = agentStore.messages.lastIndexOf(lastMsg)
    if (idx >= 0) agentStore.messages.splice(idx, 1)
  }
  // 移除最后一条用户消息（避免重复）
  const lastUserMsg = [...agentStore.messages].reverse().find(m => m.role === 'user')
  if (lastUserMsg) {
    const idx = agentStore.messages.lastIndexOf(lastUserMsg)
    if (idx >= 0) agentStore.messages.splice(idx, 1)
  }
  handleSend({ text: lastSentMessage.value, files: lastSentImage.value ? [lastSentImage.value] : [] })
}

// ── 停止 ──
function handleStop() {
  agentStore.abort()
  const lastMsg = agentStore.getLastAssistantMessage()
  if (lastMsg) {
    lastMsg.loading = false
    lastMsg.thinking = false
    if (lastMsg.toolCalls) {
      lastMsg.toolCalls.forEach((tc) => {
        if (tc.status === 'running') tc.status = 'failed'
      })
    }
    lastMsg.content += '\n[已停止生成]'
  }
}

// ── 滚动 ──
function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  })
}

// ── 快捷检测 ──
async function handleQuickDetect(type) {
  if (type === 'single') {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'image/*'
    input.onchange = async (e) => {
      const file = e.target.files[0]
      if (!file) return
      agentStore.addMessage({
        role: 'user',
        content: `[快捷检测] ${file.name}`,
        image: file.name,
        imagePreview: URL.createObjectURL(file),
      })
      agentStore.addMessage({
        role: 'assistant',
        content: '正在检测中...',
        loading: true,
        toolCalls: [],
      })
      agentStore.setLoading(true)
      const formData = new FormData()
      formData.append('file', file)
      try {
        const result = await detectSingle(formData)
        const lastMsg = agentStore.getLastAssistantMessage()
        if (lastMsg) {
          lastMsg.content = `检测完成！发现 ${(result.fire_object_count || 0) + (result.smoke_object_count || 0)} 个目标。`
          lastMsg.loading = false
          lastMsg.detectionResult = result
        }
      } catch (err) {
        const lastMsg = agentStore.getLastAssistantMessage()
        if (lastMsg) {
          lastMsg.content = '检测失败，请重试'
          lastMsg.loading = false
          lastMsg.error = true
        }
      } finally {
        agentStore.setLoading(false)
      }
    }
    input.click()
  } else if (type === 'batch') {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'image/*,.zip'
    input.multiple = true
    input.onchange = async (e) => {
      const files = Array.from(e.target.files)
      if (!files.length) return
      const isZip = files.some((f) => f.name.endsWith('.zip'))
      const formData = new FormData()
      if (isZip && files.length === 1) {
        formData.append('file', files[0])
        agentStore.addMessage({ role: 'user', content: `[快捷检测] ZIP: ${files[0].name}` })
      } else {
        files.forEach((f) => formData.append('files', f))
        agentStore.addMessage({
          role: 'user',
          content: `[快捷检测] ${files.length} 张图片`,
          images: files.map((f) => URL.createObjectURL(f)),
        })
      }
      agentStore.addMessage({
        role: 'assistant',
        content: '正在批量检测中...',
        loading: true,
        toolCalls: [],
      })
      agentStore.setLoading(true)
      try {
        const apiCall = isZip ? detectZip(formData) : detectBatch(formData)
        const result = await apiCall
        const lastMsg = agentStore.getLastAssistantMessage()
        if (!lastMsg) return
        if (result.error) {
          lastMsg.content = `批量检测失败：${result.error}`
          lastMsg.loading = false
          lastMsg.error = true
          return
        }
        lastMsg.content = `批量检测完成！共 ${(result.fire_object_count || 0) + (result.smoke_object_count || 0)} 个目标。`
        lastMsg.loading = false
        lastMsg.detectionResult = result
      } catch (err) {
        const lastMsg = agentStore.getLastAssistantMessage()
        if (lastMsg) {
          lastMsg.content = `批量检测失败：${err.message || err}`
          lastMsg.loading = false
          lastMsg.error = true
        }
      } finally {
        agentStore.setLoading(false)
      }
    }
    input.click()
  }
}

async function handleVideoDetect() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'video/mp4,video/avi,video/quicktime,video/x-msvideo'
  input.onchange = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    const maxSize = 50 * 1024 * 1024
    if (file.size > maxSize) {
      ElMessage.warning('视频文件不能超过 50MB')
      return
    }
    const videoUrl = URL.createObjectURL(file)
    agentStore.addMessage({
      role: 'user',
      content: `[视频检测] ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)}MB)`,
      videoUrl,
    })
    agentStore.addMessage({
      role: 'assistant',
      content: '正在上传视频...',
      loading: true,
      toolCalls: [],
    })
    agentStore.setLoading(true)
    const formData = new FormData()
    formData.append('file', file)
    try {
      const uploadResult = await detectVideo(formData)
      const taskId = uploadResult.task_id
      const lastMsg = agentStore.getLastAssistantMessage()
      if (lastMsg) lastMsg.content = '视频已上传，正在处理中...'
      await pollVideoProgress(taskId)
    } catch (err) {
      const lastMsg = agentStore.getLastAssistantMessage()
      if (lastMsg) {
        lastMsg.content = `视频检测失败：${err.message || err}`
        lastMsg.loading = false
        lastMsg.error = true
      }
    } finally {
      agentStore.setLoading(false)
    }
  }
  input.click()
}

async function pollVideoProgress(taskId) {
  const pollInterval = 3000
  return new Promise((resolve) => {
    const poll = async () => {
      try {
        const result = await getVideoStatus(taskId)
        if (result.status === 'completed') {
          const lastMsg = agentStore.getLastAssistantMessage()
          if (lastMsg) {
            lastMsg.content = `视频检测完成！发现 ${result.total_objects || 0} 个目标。`
            lastMsg.loading = false
            lastMsg.detectionResult = result
          }
          resolve(result)
        } else if (result.status === 'failed') {
          const lastMsg = agentStore.getLastAssistantMessage()
          if (lastMsg) {
            lastMsg.content = `视频检测失败：${result.error_message || '未知错误'}`
            lastMsg.loading = false
            lastMsg.error = true
          }
          resolve(null)
        } else {
          const lastMsg = agentStore.getLastAssistantMessage()
          if (lastMsg) lastMsg.content = `视频检测中... ${result.progress || 0}%`
          setTimeout(poll, pollInterval)
        }
      } catch (err) {
        const lastMsg = agentStore.getLastAssistantMessage()
        if (lastMsg) {
          lastMsg.content = `视频检测失败：${err.message || err}`
          lastMsg.loading = false
          lastMsg.error = true
        }
        resolve(null)
      }
    }
    setTimeout(poll, pollInterval)
  })
}

onMounted(async () => {
  // 等待 token 就绪后再请求会话列表，避免 401 竞态（BUG-007）
  const token = localStorage.getItem('rsod_token')
  if (token) {
    await agentStore.fetchSessions()
  }
  if (agentStore.messages.length === 0) {
    // 欢迎消息在模板中通过 v-if 处理
  }
})
</script>

<style lang="scss" scoped>
$chat-sidebar-top-height: 57px;
$chat-header-height: 52px;
$chat-input-area-height: 80px;
$color-main-dark: #a9a6a2;
$color-main-light: #dcc9b7;

.chat-page {
  display: flex;
  width: calc(100% + 40px);
  height: calc(100vh - $header-height);
  margin: -20px;
  background: #f5f6f7;
  overflow: hidden;

  /* 左侧会话列表：宽度固定 260px，独立滚动 */
  :deep(.chat-sidebar) {
    width: 260px;
    flex-shrink: 0;
    height: 100%;
    background: #fff;
    border-right: 1px solid #e4e7ed;
    display: flex;
    flex-direction: column;
  }

  :deep(.session-list) {
    height: calc(100vh - $header-height - $chat-sidebar-top-height);
    flex: 1 1 auto;
    min-height: 0;
    overflow-y: auto;
  }
}

/* ── 主对话区域 ── */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100%;
  background: #f5f6f7;
  overflow: hidden;
}

/* ── 顶部栏 ── */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: $chat-header-height;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-title {
  font-size: 17px;
  font-weight: 600;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 8px;

  :deep(.el-button) {
    font-size: 14px;
    color: $color-main-dark;
    border-color: $color-main-dark;

    &:hover {
      background-color: rgba(169, 166, 162, 0.1);
      border-color: $color-main-dark;
      color: $color-main-dark;
    }
  }
}

/* ── 消息列表 ── */
.message-list {
  height: calc(100vh - $header-height - $chat-header-height - $chat-input-area-height);
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding: 20px 16px;
}

/* ── 欢迎区域 ── */
.welcome-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
}

.welcome-icon {
  color: $color-main-dark;
  margin-bottom: 16px;
}

.welcome-area h2 {
  font-size: 22px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 8px;
}

.welcome-desc {
  font-size: 15px;
  color: #909399;
  margin: 0 0 32px;
}

.welcome-tips {
  display: flex;
  gap: 12px;
}

.tip-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  font-size: 14px;
  color: #606266;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: $color-main-dark;
    color: $color-main-dark;
    background: rgba(169, 166, 162, 0.08);
  }
}

/* ── 消息项 ── */
.message-item {
  margin-bottom: 20px;
}

.message-wrapper {
  display: flex;
  max-width: 75%;
}

.message-user-wrapper {
  margin-left: auto;
  justify-content: flex-end;
}

.message-assistant-wrapper {
  margin-right: auto;
  justify-content: flex-start;
}

.message-bubble {
  padding: 14px 18px;
  border-radius: 12px;
  line-height: 1.6;
  word-break: break-word;
  font-size: 15px;
}

.user-bubble {
  background: linear-gradient(135deg, $color-main-dark, $color-main-light);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.assistant-bubble {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.message-content {
  white-space: pre-wrap;
}

.streaming-text {
  &::after {
    content: '|';
    animation: blink 1s infinite;
  }
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.markdown-body {
  :deep(h1), :deep(h2), :deep(h3) {
    margin-top: 8px;
    margin-bottom: 4px;
  }
  :deep(table) {
    border-collapse: collapse;
    width: 100%;
    margin: 8px 0;
  }
  :deep(th), :deep(td) {
    border: 1px solid #e0e0e0;
    padding: 4px 8px;
  }
  :deep(code) {
    background: #f0f0f0;
    padding: 2px 4px;
    border-radius: 3px;
  }
}

/* ── 附件 ── */
.message-attachment {
  margin-top: 8px;
  img {
    max-width: 200px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.3);
  }
}

.message-attachments-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
  gap: 8px;
  margin-top: 8px;
  img {
    width: 100%;
    height: 80px;
    object-fit: cover;
    border-radius: 6px;
    border: 1px solid rgba(255, 255, 255, 0.3);
  }
}

/* ── 思考中 ── */
.thinking-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
}

.thinking-dots {
  display: flex;
  gap: 4px;
  span {
    width: 8px;
    height: 8px;
    background: $color-main-dark;
    border-radius: 50%;
    animation: thinkingPulse 1.2s infinite;
  }
  span:nth-child(2) { animation-delay: 0.2s; }
  span:nth-child(3) { animation-delay: 0.4s; }
}

@keyframes thinkingPulse {
  0%, 60%, 100% { opacity: 0.3; transform: scale(0.8); }
  30% { opacity: 1; transform: scale(1.2); }
}

.thinking-text {
  font-size: 14px;
  color: #909399;
  font-style: italic;
}

/* ── 打字中 ── */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 4px 0;
  span {
    width: 6px;
    height: 6px;
    background: #999;
    border-radius: 50%;
    animation: typing 1.2s infinite;
  }
  span:nth-child(2) { animation-delay: 0.2s; }
  span:nth-child(3) { animation-delay: 0.4s; }
}

@keyframes typing {
  0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
  30% { opacity: 1; transform: translateY(-4px); }
}

/* ── 工具调用时间线 ── */
.tool-timeline {
  margin-top: 12px;
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
}

.tool-timeline-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  font-size: 14px;
  &:not(:last-child) {
    border-bottom: 1px dashed #e8e8e8;
  }
}

.tool-loading {
  display: flex;
  align-items: center;
  gap: 6px;
  color: $color-main-dark;
  font-size: 14px;
}

.tool-completed {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #67c23a;
  font-size: 14px;
}

.tool-failed {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #f56c6c;
  font-size: 14px;
}

.tool-result-detail {
  font-size: 13px;
  color: #606266;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow-y: auto;
}

/* ── 错误重试 ── */
.error-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

/* ── 多Agent调用链 ── */
.agent-chain {
  margin-top: 12px;
  padding: 8px 12px;
  background: rgba(169, 166, 162, 0.08);
  border-radius: 8px;
  border: 1px solid rgba(169, 166, 162, 0.15);
}

.agent-chain-title {
  font-size: 13px;
  color: #909399;
  margin-bottom: 6px;
}

.agent-chain-steps {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}

.agent-chain-step {
  font-size: 13px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(169, 166, 162, 0.1);
  color: $color-main-dark;
  font-weight: 500;

  &.agent-chain-step-running {
    background: $color-main-dark;
    color: #fff;
    animation: agentPulse 1.2s infinite;
  }

  &.agent-chain-step-completed {
    background: #e8f5e9;
    color: #67c23a;
  }
}

.agent-chain-arrow {
  color: #c0c4cc;
  margin: 0 2px;
}

@keyframes agentPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

/* ── 知识来源 ── */
.knowledge-sources {
  margin-top: 12px;
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
}

.knowledge-sources-title {
  font-size: 13px;
  color: #909399;
  margin-bottom: 6px;
}

.knowledge-source-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  font-size: 13px;

  &:not(:last-child) {
    border-bottom: 1px dashed #e8e8e8;
  }
}

.knowledge-source-name {
  color: $color-main-dark;
  max-width: 70%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.knowledge-source-similarity {
  color: #909399;
  flex-shrink: 0;
}
:deep(.el-button--primary) {
  background-color: #dcc9b7;    
  border-color: #dcc9b7;
  color: #303133;
  &:hover {
    background-color: #c9b59f; 
    border-color: #c9b59f;
  }
  &:active {
    background-color: #b8a38c;
    border-color: #b8a38c;
  }
}

:deep(.el-button--primary.is-text) {
  color: #dcc9b7;
  background: transparent;
  border: none;
  &:hover {
    color: #c9b59f;
  }
  &:active {
    color: #b8a38c;
  }
}

:deep(.el-button--default) {
  &:hover {
    color: #dcc9b7;
    border-color: #dcc9b7;
  }
  &:active {
    color: #b8a38c;
    border-color: #b8a38c;
  }
}

:deep(.el-button.is-active) {
  background-color: #dcc9b7;
  border-color: #dcc9b7;
  color: #303133;
}

:deep(.session-item.active) {
  background-color: #dcc9b7 !important;
  color: #303133 !important;
  border-left: 3px solid #a9a6a2 !important;
}

:deep(.el-menu-item.is-active) {
  background-color: #dcc9b7 !important;
  color: #303133 !important;
  border-left: 3px solid #a9a6a2 !important;
}
.user-bubble .message-content {
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.25);
}
</style>