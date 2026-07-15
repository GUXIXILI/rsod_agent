<template>
  <div class="chat-page">
    <!-- ── 会话列表侧边栏（左侧悬浮） ── -->
    <div class="session-sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <span v-if="!sidebarCollapsed" class="sidebar-title">会话列表</span>
        <el-button
          class="sidebar-toggle"
          :icon="sidebarCollapsed ? 'Expand' : 'Fold'"
          text
          @click="sidebarCollapsed = !sidebarCollapsed"
        />
      </div>
      <div v-if="!sidebarCollapsed" class="sidebar-body">
        <el-button
          type="primary"
          size="small"
          class="new-session-btn"
          @click="handleNewSession"
        >
          <el-icon><Plus /></el-icon> 新对话
        </el-button>
        <div class="session-list">
          <div
            v-for="session in agentStore.sessions"
            :key="session.id"
            :class="['session-item', { active: session.id === agentStore.currentSessionId }]"
            @click="handleSwitchSession(session.id)"
          >
            <div class="session-title">{{ session.title }}</div>
            <div class="session-time">{{ formatTime(session.created_at) }}</div>
          </div>
          <el-empty
            v-if="agentStore.sessions.length === 0"
            description="暂无历史会话"
            :image-size="60"
          />
        </div>
      </div>
    </div>

    <!-- ── 主对话区域 ── -->
    <div class="chat-main">
      <!-- ── 页面标题 ── -->
      <div class="page-header">
        <h2>智能对话</h2>
      </div>

      <!-- ── 消息列表区域 ── -->
      <div class="message-list" ref="messageListRef">
        <div
          v-for="(msg, index) in agentStore.messages"
          :key="index"
          :class="['message-item', `message-${msg.role}`]"
        >
          <!-- 用户消息 -->
          <div v-if="msg.role === 'user'" class="message-bubble user-bubble">
            <div class="message-content">{{ msg.content }}</div>
            <!-- 单张图片附件 -->
            <div v-if="msg.image" class="message-attachment">
              <img :src="msg.imagePreview" alt="附件图片" />
            </div>
            <!-- 多图附件（批量检测） -->
            <div v-if="msg.images && msg.images.length" class="message-attachments-grid">
              <img v-for="(src, i) in msg.images" :key="i" :src="src" alt="附件图片" />
            </div>
          </div>

          <!-- AI 消息 -->
          <div
            v-else-if="msg.role === 'assistant'"
            class="message-bubble assistant-bubble"
          >
            <!-- 思考中动画 -->
            <div v-if="msg.thinking" class="thinking-indicator">
              <div class="thinking-dots">
                <span></span><span></span><span></span>
              </div>
              <span class="thinking-text">{{ msg.thinkingContent || '正在思考中...' }}</span>
            </div>

            <!-- 打字中动画（loading 但没有 thinking） -->
            <div v-else-if="msg.loading && !msg.thinking" class="typing-indicator">
              <span></span><span></span><span></span>
            </div>

            <!-- 消息内容（Markdown 渲染） -->
            <div
              v-if="!msg.loading && msg.content"
              class="message-content markdown-body"
              v-html="renderMarkdown(msg.content)"
            ></div>

            <!-- 流式渲染中的文本（逐字显示） -->
            <div
              v-if="msg.loading && msg.content"
              class="message-content streaming-text"
            >{{ msg.content }}</div>

            <!-- 工具调用时间线 -->
            <div v-if="msg.toolCalls && msg.toolCalls.length > 0" class="tool-timeline">
              <div
                v-for="(tc, tIdx) in msg.toolCalls"
                :key="tIdx"
                :class="['tool-timeline-item', `tool-status-${tc.status}`]"
              >
                <!-- 工具调用中：加载动画 -->
                <div v-if="tc.status === 'running'" class="tool-loading">
                  <el-icon class="is-loading"><Loading /></el-icon>
                  <span>正在调用工具：{{ tc.tool }}</span>
                </div>
                <!-- 工具调用完成：显示结果摘要 -->
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
                <!-- 工具调用失败 -->
                <div v-else-if="tc.status === 'failed'" class="tool-failed">
                  <el-icon color="#f56c6c"><CircleClose /></el-icon>
                  <span>工具 {{ tc.tool }} 调用失败</span>
                </div>
              </div>
            </div>

            <!-- 错误状态：显示错误消息和重试按钮 -->
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

      <!-- ── 快捷操作栏 ── -->
      <div class="quick-actions">
        <el-button
          @click="handleQuickDetect('single')"
          :disabled="agentStore.isLoading"
        >
          📷 单图检测
        </el-button>
        <el-button
          @click="handleQuickDetect('batch')"
          :disabled="agentStore.isLoading"
        >
          📁 批量/ZIP
        </el-button>
        <el-button
          @click="handleVideoDetect"
          :disabled="agentStore.isLoading"
        >
          🎬 视频
        </el-button>
        <el-button disabled>📹 摄像头</el-button>
      </div>

      <!-- ── 输入区域 ── -->
      <div class="input-area">
        <!-- 附件按钮 -->
        <el-button
          class="attach-btn"
          @click="triggerFileInput"
          :disabled="agentStore.isLoading"
          circle
        >
          📎
        </el-button>
        <input
          ref="fileInputRef"
          type="file"
          accept="image/*,.zip"
          style="display: none"
          @change="handleFileSelect"
        />

        <!-- 文本输入框 -->
        <el-input
          v-model="inputText"
          placeholder="输入消息，或拖拽图片/ZIP 到这里..."
          @keyup.enter="sendMessage"
          :disabled="agentStore.isLoading"
        />

        <!-- 发送/停止按钮 -->
        <el-button
          v-if="!agentStore.isLoading"
          type="primary"
          @click="sendMessage"
          :disabled="!inputText.trim() && !selectedFile"
        >
          发送
        </el-button>
        <el-button v-else type="danger" @click="handleStop"> 停止 </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * ChatPage.vue — 智能对话界面（完整 SSE 事件协议版）
 *
 * 功能：
 *   - 会话列表侧边栏（左侧悬浮，支持创建/切换会话）
 *   - 消息气泡（用户/AI 区分）
 *   - 文件附件上传（图片/ZIP 拖拽或选择）
 *   - 完整 SSE 事件协议支持：
 *       thinking   — Agent 思考中（显示思考动画）
 *       tool_start — 开始调用工具（工具调用时间线 + 加载动画）
 *       tool_end   — 工具调用完成（显示结果摘要）
 *       text_chunk — 流式文本片段（逐字渲染）
 *       done       — 完成（带完整响应）
 *       error      — 错误（显示重试按钮）
 *   - 检测结果卡片展示
 *   - 快捷操作栏（单图/批量/视频/摄像头）
 *   - 中断当前对话
 */
import { detectBatch, detectSingle, detectVideo, detectZip, getVideoStatus } from "@/api/detection";
import DetectionResultCard from "@/components/DetectionResultCard.vue";
import { useAgentStore } from "@/stores/agent";
import { renderMarkdown } from "@/utils/markdown";
import request from "@/utils/request";
import { streamChat } from "@/utils/stream";
import { CircleCheck, CircleClose, Loading, Plus, Refresh } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, nextTick, onMounted, ref } from "vue";

// ── Store ──
const agentStore = useAgentStore();

// ── 响应式状态 ──
const inputText = ref("");
const selectedFile = ref(null);
const messageListRef = ref(null);
const fileInputRef = ref(null);
const sidebarCollapsed = ref(false);

// ── 上一次发送的消息内容（用于重试） ──
const lastSentMessage = ref("");
const lastSentImage = ref(null);

// ── 计算属性 ──
const canSend = computed(() => {
  return inputText.value.trim() || selectedFile.value;
});

// ── 方法 ──

/** 创建新会话 */
function handleNewSession() {
  agentStore.newChat();
  // 显示欢迎消息
  agentStore.addMessage({
    role: "assistant",
    content:
      "你好！我是火灾烟雾智能检测智能体助手。\n\n你可以：\n- 上传一张图片，让我帮你检测目标\n- 使用下方的快捷按钮直接触发检测\n- 用自然语言描述你的需求\n\n试试发一张图片给我吧！",
  });
}

/** 切换会话 */
function handleSwitchSession(sessionId) {
  agentStore.switchSession(sessionId);
  scrollToBottom();
}

/** 格式化时间 */
function formatTime(timestamp) {
  if (!timestamp) return "";
  const d = new Date(timestamp);
  const now = new Date();
  const diff = now - d;
  if (diff < 60000) return "刚刚";
  if (diff < 3600000) return Math.floor(diff / 60000) + "分钟前";
  if (diff < 86400000) return Math.floor(diff / 3600000) + "小时前";
  return d.toLocaleDateString();
}

/** 发送消息 */
async function sendMessage() {
  if (!canSend.value) return;

  const message = inputText.value.trim();
  // ── 关键：在清空之前保存文件引用 ──
  const fileToSend = selectedFile.value;
  const imagePreview = fileToSend ? URL.createObjectURL(fileToSend) : null;

  // 保存用于重试
  lastSentMessage.value = message;
  lastSentImage.value = fileToSend;

  // 添加用户消息到列表
  agentStore.addMessage({
    role: "user",
    content: message,
    image: fileToSend ? fileToSend.name : null,
    imagePreview,
  });

  // 清空输入
  inputText.value = "";
  selectedFile.value = null;

  // 添加 AI 加载占位
  agentStore.addMessage({
    role: "assistant",
    content: "",
    loading: true,
    toolCalls: [],
  });

  // 设置加载状态
  agentStore.setLoading(true);

  // 滚动到底部
  scrollToBottom();

  // ── 如果有附件图片，先上传到服务端获取真实路径 ──
  let serverImagePath = null;
  if (fileToSend) {
    try {
      const formData = new FormData();
      formData.append("file", fileToSend);
      // 不设置 Content-Type，让 axios 自动添加 boundary
      const uploadResult = await request.post("/chat/upload", formData);
      serverImagePath = uploadResult.image_path;
    } catch (err) {
      console.error("[图片上传失败]", err.response?.data || err.message || err);
      const lastMsg = agentStore.getLastAssistantMessage();
      if (lastMsg) {
        lastMsg.content = `图片上传失败：${err.response?.data?.detail || err.message || "未知错误"}，请重试`;
        lastMsg.loading = false;
        lastMsg.error = true;
      }
      agentStore.setLoading(false);
      return;
    }
  }

  // 发起 SSE 流式请求
  const requestBody = {
    message,
    ...(serverImagePath ? { image_path: serverImagePath } : {}),
  };

  let fullContent = "";

  const stop = streamChat("/api/chat/messages/stream", requestBody, {
    onMessage: (data) => {
      // 调试日志
      console.log("[SSE事件]", data.type, data);

      const lastMsg = agentStore.getLastAssistantMessage();
      if (!lastMsg) return;

      switch (data.type) {
        // ── thinking：Agent 正在思考 ──
        case "thinking":
          lastMsg.thinking = true;
          lastMsg.thinkingContent = data.content || "正在分析问题...";
          lastMsg.loading = true;
          break;

        // ── tool_start：开始调用工具 ──
        case "tool_start": {
          lastMsg.thinking = false;
          lastMsg.loading = true;
          // 初始化工具调用列表
          if (!lastMsg.toolCalls) lastMsg.toolCalls = [];
          // 添加工具调用记录
          lastMsg.toolCalls.push({
            tool: data.tool || "未知工具",
            input: data.input,
            status: "running",
            startTime: Date.now(),
          });
          break;
        }

        // ── tool_end：工具调用完成 ──
        case "tool_end": {
          // 更新最后一个 running 状态的工具为 completed
          if (lastMsg.toolCalls && lastMsg.toolCalls.length > 0) {
            const runningTc = [...lastMsg.toolCalls].reverse().find(tc => tc.status === "running");
            if (runningTc) {
              runningTc.status = "completed";
              runningTc.result = data.result;
              // 生成结果摘要
              try {
                const result = JSON.parse(data.result);
                if (result.detections) {
                  runningTc.resultSummary = `检测到 ${result.total_objects || 0} 个目标`;
                  // 设置检测结果卡片
                  lastMsg.detectionResult = result;
                  lastMsg.loading = false;
                } else {
                  runningTc.resultSummary = JSON.stringify(result).substring(0, 200);
                }
              } catch {
                runningTc.resultSummary = (data.result || "").substring(0, 200);
              }
            }
          }
          // 回退：兼容旧 tool_call/tool_result 协议
          lastMsg.toolCall = { tool: data.tool, result: data.result };
          break;
        }

        // ── text_chunk：流式文本片段 ──
        case "text_chunk":
          lastMsg.thinking = false;
          lastMsg.loading = true;
          fullContent += data.content || "";
          lastMsg.content = fullContent;
          break;

        // ── done：完成 ──
        case "done":
          if (data.response && !fullContent) {
            lastMsg.content = data.response;
          }
          lastMsg.loading = false;
          lastMsg.thinking = false;
          agentStore.setLoading(false);
          break;

        // ── error：错误 ──
        case "error":
          lastMsg.content = data.content || "处理请求时发生错误";
          lastMsg.loading = false;
          lastMsg.thinking = false;
          lastMsg.error = true;
          agentStore.setLoading(false);
          break;

        // ── 兼容旧版 tool_call / tool_result 协议 ──
        case "tool_call":
          lastMsg.thinking = false;
          lastMsg.loading = true;
          lastMsg.toolCall = { tool: data.tool, input: data.input };
          if (!lastMsg.toolCalls) lastMsg.toolCalls = [];
          lastMsg.toolCalls.push({
            tool: data.tool,
            input: data.input,
            status: "running",
            startTime: Date.now(),
          });
          break;

        case "tool_result":
          if (lastMsg.toolCalls && lastMsg.toolCalls.length > 0) {
            const runningTc = [...lastMsg.toolCalls].reverse().find(tc => tc.status === "running");
            if (runningTc) {
              runningTc.status = "completed";
              runningTc.result = data.result;
            }
          }
          console.log("[工具结果] tool:", data.tool, "result长度:", data.result?.length);
          try {
            const result = JSON.parse(data.result);
            console.log("[工具结果解析]", "total_objects:", result.total_objects, "detections:", result.detections?.length);
            if (result.detections) {
              lastMsg.detectionResult = result;
              lastMsg.loading = false;
              console.log("[检测结果卡片已设置]", lastMsg.detectionResult);
            }
          } catch (e) {
            console.warn("[工具结果解析失败]", e.message, "原始数据:", data.result?.substring(0, 200));
            lastMsg.content += `\n[工具结果: ${data.result?.substring(0, 100)}...]`;
          }
          break;

        default:
          // 未知类型，尝试作为 text_chunk 处理
          if (data.content) {
            lastMsg.thinking = false;
            lastMsg.loading = true;
            fullContent += data.content;
            lastMsg.content = fullContent;
          }
          break;
      }

      scrollToBottom();
    },

    onDone: () => {
      const lastMsg = agentStore.getLastAssistantMessage();
      if (lastMsg) {
        if (lastMsg.loading && !lastMsg.content && !lastMsg.detectionResult) {
          lastMsg.content = "处理完成。";
        }
        lastMsg.loading = false;
        lastMsg.thinking = false;
      }
      agentStore.setLoading(false);
      agentStore.abortController = null;
      scrollToBottom();
    },

    onError: (err) => {
      const lastMsg = agentStore.getLastAssistantMessage();
      if (lastMsg) {
        lastMsg.content = `抱歉，处理出错了：${err.message}`;
        lastMsg.loading = false;
        lastMsg.thinking = false;
        lastMsg.error = true;
      }
      agentStore.setLoading(false);
      agentStore.abortController = null;
      ElMessage.error("对话请求失败，请重试");
    },
  });

  // 保存中断函数到 store
  agentStore.abortController = stop;
}

/** 重试最后一条消息 */
function retryLastMessage() {
  if (!lastSentMessage.value && !lastSentImage.value) {
    ElMessage.warning("没有可重试的消息");
    return;
  }
  // 移除最后一条错误的 AI 消息
  const lastMsg = agentStore.getLastAssistantMessage();
  if (lastMsg && lastMsg.error) {
    const idx = agentStore.messages.lastIndexOf(lastMsg);
    if (idx >= 0) agentStore.messages.splice(idx, 1);
  }
  // 恢复输入并重新发送
  inputText.value = lastSentMessage.value;
  selectedFile.value = lastSentImage.value;
  sendMessage();
}

/** 停止生成 */
function handleStop() {
  agentStore.abort();
  const lastMsg = agentStore.getLastAssistantMessage();
  if (lastMsg) {
    lastMsg.loading = false;
    lastMsg.thinking = false;
    if (lastMsg.toolCalls) {
      lastMsg.toolCalls.forEach(tc => {
        if (tc.status === "running") tc.status = "failed";
      });
    }
    lastMsg.content += "\n[已停止生成]";
  }
}

/** 触发文件选择框 */
function triggerFileInput() {
  fileInputRef.value?.click();
}

/** 文件选择回调 */
function handleFileSelect(event) {
  const file = event.target.files[0];
  if (file) {
    selectedFile.value = file;
    file._tempPath = URL.createObjectURL(file);
    ElMessage.info(`${file.name} 已选择`);
  }
}

/** 滚动到底部 */
function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight;
    }
  });
}

/**
 * 快捷单图检测流程：
 * 1. 用户点击"📷 单图检测"按钮
 * 2. 弹出文件选择框
 * 3. 选择图片后，调用 detectSingle API
 * 4. 将结果以"用户消息 + AI 结果卡片"的形式插入对话
 */
async function handleQuickDetect(type) {
  if (type === "single") {
    // 创建隐藏的文件选择器
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      // 添加用户消息（显示文件名）
      agentStore.addMessage({
        role: "user",
        content: `[快捷检测] ${file.name}`,
        image: file.name,
        imagePreview: URL.createObjectURL(file),
      });

      // 添加加载占位
      agentStore.addMessage({
        role: "assistant",
        content: "正在检测中...",
        loading: true,
        toolCalls: [],
      });
      agentStore.setLoading(true);

      // 构造 FormData 并调用 API
      const formData = new FormData();
      formData.append("file", file);

      try {
        const result = await detectSingle(formData);
        const lastMsg = agentStore.getLastAssistantMessage();
        if (lastMsg) {
          lastMsg.content = `检测完成！发现 ${result.total_objects} 个目标。`;
          lastMsg.loading = false;
          lastMsg.detectionResult = result;
        }
      } catch (err) {
        const lastMsg = agentStore.getLastAssistantMessage();
        if (lastMsg) {
          lastMsg.content = "检测失败，请重试";
          lastMsg.loading = false;
          lastMsg.error = true;
        }
      } finally {
        agentStore.setLoading(false);
      }
    };
    input.click();
  } else if (type === "batch") {
    // 批量检测（支持多选 + ZIP）
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*,.zip";
    input.multiple = true;
    input.onchange = async (e) => {
      const files = Array.from(e.target.files);
      if (!files.length) return;

      const isZip = files.some((f) => f.name.endsWith(".zip"));
      const formData = new FormData();

      if (isZip && files.length === 1) {
        // 单个 ZIP 文件
        formData.append("file", files[0]);
        agentStore.addMessage({
          role: "user",
          content: `[快捷检测] ZIP: ${files[0].name}`,
        });
      } else {
        // 多张图片
        files.forEach((f) => formData.append("files", f));
        const imagePreviews = files.map((f) => URL.createObjectURL(f));
        agentStore.addMessage({
          role: "user",
          content: `[快捷检测] ${files.length} 张图片`,
          images: imagePreviews,
        });
      }

      agentStore.addMessage({
        role: "assistant",
        content: "正在批量检测中...",
        loading: true,
        toolCalls: [],
      });
      agentStore.setLoading(true);

      try {
        const apiCall = isZip ? detectZip(formData) : detectBatch(formData);
        const result = await apiCall;
        const lastMsg = agentStore.getLastAssistantMessage();
        if (!lastMsg) return;

        if (result.error) {
          lastMsg.content = `批量检测失败：${result.error}`;
          lastMsg.loading = false;
          lastMsg.error = true;
          return;
        }

        const totalObjects = result.total_objects ?? 0;
        lastMsg.content = `批量检测完成！共 ${totalObjects} 个目标。`;
        lastMsg.loading = false;
        lastMsg.detectionResult = result;
        console.log("[批量检测结果]", result);
      } catch (err) {
        console.error("[批量检测异常]", err);
        const lastMsg = agentStore.getLastAssistantMessage();
        if (lastMsg) {
          lastMsg.content = `批量检测失败：${err.message || err}`;
          lastMsg.loading = false;
          lastMsg.error = true;
        }
      } finally {
        agentStore.setLoading(false);
      }
    };
    input.click();
  }
}

/**
 * 视频检测流程：
 * 1. 用户点击 "🎬 视频" 按钮
 * 2. 弹出文件选择框（限制视频格式）
 * 3. 选择视频后，上传到后端
 * 4. 后端返回 task_id，前端开始轮询进度
 * 5. 处理完成后，展示关键帧结果卡片
 */
async function handleVideoDetect() {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "video/mp4,video/avi,video/quicktime,video/x-msvideo";
  input.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
      ElMessage.warning("视频文件不能超过 50MB");
      return;
    }

    const videoUrl = URL.createObjectURL(file);

    agentStore.addMessage({
      role: "user",
      content: `[视频检测] ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)}MB)`,
      videoUrl,
    });

    agentStore.addMessage({
      role: "assistant",
      content: "正在上传视频...",
      loading: true,
      toolCalls: [],
    });
    agentStore.setLoading(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const uploadResult = await detectVideo(formData);
      const taskId = uploadResult.task_id;

      const lastMsg = agentStore.getLastAssistantMessage();
      if (lastMsg) {
        lastMsg.content = "视频已上传，正在处理中...";
      }

      await pollVideoProgress(taskId);
    } catch (err) {
      console.error("[视频检测失败]", err);
      const lastMsg = agentStore.getLastAssistantMessage();
      if (lastMsg) {
        lastMsg.content = `视频检测失败：${err.message || err}`;
        lastMsg.loading = false;
        lastMsg.error = true;
      }
    } finally {
      agentStore.setLoading(false);
    }
  };
  input.click();
}

/**
 * 轮询视频检测进度
 * @param {number} taskId - 视频检测任务 ID
 */
async function pollVideoProgress(taskId) {
  const pollInterval = 3000;

  return new Promise((resolve) => {
    const poll = async () => {
      try {
        const result = await getVideoStatus(taskId);

        if (result.status === "completed") {
          const lastMsg = agentStore.getLastAssistantMessage();
          if (lastMsg) {
            lastMsg.content = `视频检测完成！发现 ${result.total_objects || 0} 个目标。`;
            lastMsg.loading = false;
            lastMsg.detectionResult = result;
          }
          resolve(result);
        } else if (result.status === "failed") {
          const lastMsg = agentStore.getLastAssistantMessage();
          if (lastMsg) {
            lastMsg.content = `视频检测失败：${result.error_message || "未知错误"}`;
            lastMsg.loading = false;
            lastMsg.error = true;
          }
          resolve(null);
        } else {
          const lastMsg = agentStore.getLastAssistantMessage();
          if (lastMsg) {
            lastMsg.content = `视频检测中... ${result.progress || 0}%`;
          }
          setTimeout(poll, pollInterval);
        }
      } catch (err) {
        console.error("[轮询视频进度失败]", err);
        const lastMsg = agentStore.getLastAssistantMessage();
        if (lastMsg) {
          lastMsg.content = `视频检测失败：${err.message || err}`;
          lastMsg.loading = false;
          lastMsg.error = true;
        }
        resolve(null);
      }
    };

    setTimeout(poll, pollInterval);
  });
}

onMounted(() => {
  // 页面加载时如果没有会话，创建新会话并显示欢迎消息
  if (!agentStore.currentSessionId) {
    agentStore.currentSessionId = Date.now().toString();
  }
  if (agentStore.messages.length === 0) {
    agentStore.addMessage({
      role: "assistant",
      content:
        "你好！我是火灾烟雾智能检测智能体助手。\n\n你可以：\n- 上传一张图片，让我帮你检测目标\n- 使用下方的快捷按钮直接触发检测\n- 用自然语言描述你的需求\n\n试试发一张图片给我吧！",
    });
  }
});
</script>

<style lang="scss" scoped>
.chat-page {
  display: flex;
  height: 100%;
  background: #f5f5f5;
  position: relative;
}

/* ── 会话列表侧边栏 ── */
.session-sidebar {
  width: 260px;
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  overflow: hidden;

  &.collapsed {
    width: 48px;
  }
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-bottom: 1px solid #e0e0e0;
  min-height: 48px;
}

.sidebar-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
}

.sidebar-toggle {
  flex-shrink: 0;
}

.sidebar-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 12px;
}

.new-session-btn {
  width: 100%;
  margin-bottom: 12px;
}

.session-list {
  flex: 1;
  overflow-y: auto;
}

.session-item {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: background 0.2s;

  &:hover {
    background: #f0f2f5;
  }

  &.active {
    background: #e6f4ff;
    border: 1px solid #91caff;
  }
}

.session-title {
  font-size: 13px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 4px;
}

.session-time {
  font-size: 11px;
  color: #909399;
}

/* ── 主对话区域 ── */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* ── 页面标题栏 ── */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: #fff;
  border-bottom: 1px solid #e0e0e0;
}

.page-header h2 {
  margin: 0;
  font-size: 22px;
  color: $text-primary;
}

/* ── 消息列表 ── */
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.message-item {
  display: flex;
  margin-bottom: 16px;

  &.message-user {
    justify-content: flex-end;
  }

  &.message-assistant {
    justify-content: flex-start;
  }
}

.message-bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.5;
  word-break: break-word;
}

.user-bubble {
  background: #409eff;
  color: white;
  border-bottom-right-radius: 4px;
}

.assistant-bubble {
  background: white;
  border: 1px solid #e0e0e0;
  border-bottom-left-radius: 4px;
}

.message-content {
  white-space: pre-wrap;
}

.streaming-text {
  /* 流式文本逐字渲染，末尾添加光标闪烁 */
  &::after {
    content: "|";
    animation: blink 1s infinite;
  }
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.markdown-body {
  h1, h2, h3 {
    margin-top: 8px;
    margin-bottom: 4px;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    margin: 8px 0;
  }
  th, td {
    border: 1px solid #e0e0e0;
    padding: 4px 8px;
  }
  code {
    background: #f0f0f0;
    padding: 2px 4px;
    border-radius: 3px;
  }
}

/* ── 思考中动画 ── */
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
    background: #409eff;
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
  font-size: 13px;
  color: #909399;
  font-style: italic;
}

/* ── 打字中动画 ── */
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
  0%, 60%, 100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  30% {
    opacity: 1;
    transform: translateY(-4px);
  }
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
  font-size: 13px;

  &:not(:last-child) {
    border-bottom: 1px dashed #e8e8e8;
  }
}

.tool-loading {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #409eff;
  font-size: 13px;
}

.tool-completed {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #67c23a;
  font-size: 13px;
}

.tool-failed {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #f56c6c;
  font-size: 13px;
}

.tool-result-detail {
  font-size: 12px;
  color: #606266;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow-y: auto;
}

/* ── 错误重试按钮 ── */
.error-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

/* ── 快捷操作栏 ── */
.quick-actions {
  display: flex;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid #e0e0e0;
  background: white;
}

/* ── 输入区域 ── */
.input-area {
  display: flex;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid #e0e0e0;
  background: white;

  .el-input {
    flex: 1;
  }
}

/* ── 附件预览 ── */
.message-attachment {
  margin-top: 8px;

  img {
    max-width: 200px;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
  }
}

/* ── 多图附件网格 ── */
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
    border: 1px solid #e0e0e0;
  }
}
</style>