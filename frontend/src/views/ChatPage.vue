<template>
  <div class="chat-page">
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
          <div
            v-if="msg.images && msg.images.length"
            class="message-attachments-grid"
          >
            <img
              v-for="(src, i) in msg.images"
              :key="i"
              :src="src"
              alt="附件图片"
            />
          </div>
          <!-- 视频附件 -->
          <div v-if="msg.videoUrl" class="message-attachment video-attachment">
            <video :src="msg.videoUrl" controls preload="metadata"></video>
          </div>
        </div>

        <!-- AI 消息 -->
        <div
          v-else-if="msg.role === 'assistant'"
          class="message-bubble assistant-bubble"
        >
          <div v-if="msg.loading" class="typing-indicator">
            <span></span><span></span><span></span>
          </div>
          <div
            v-else
            class="message-content markdown-body"
            v-html="renderMarkdown(msg.content)"
          ></div>

          <!-- 知识来源显示区域 -->
          <div
            v-if="msg.knowledgeSources && msg.knowledgeSources.length > 0"
            class="knowledge-sources"
          >
            <el-icon color="#67c23a"><CircleCheckFilled /></el-icon>
            <span class="knowledge-label">知识库检索</span>
            <span class="tag knowledge">[Knowledge]</span>
            <span class="tag content">[Content]</span>
            <span
              v-for="(source, idx) in msg.knowledgeSources"
              :key="idx"
              class="tag source"
              >* "{{ source.title || source.source }}"</span
            >
          </div>
          <div
            v-else-if="msg.hasKnowledge === false"
            class="knowledge-sources no-knowledge"
          >
            <el-icon color="#909399"><InfoFilled /></el-icon>
            <span class="knowledge-label">知识库检索</span>
            <span class="tag knowledge">[Knowledge]</span>
            <span class="no-knowledge-text">知识库中暂无相关内容，答案来自【LLM】</span>
          </div>

          <!-- 工具调用状态展示 -->
          <div
            v-if="msg.toolCalls && msg.toolCalls.length > 0"
            class="tool-calls"
          >
            <div
              v-for="(tc, idx) in msg.toolCalls"
              :key="idx"
              class="tool-call-item"
              :class="{ 'is-loading': tc.status === 'loading' }"
            >
              <el-icon v-if="tc.status === 'loading'" class="is-loading">
                <Loading />
              </el-icon>
              <el-icon v-else color="#67c23a"><CircleCheckFilled /></el-icon>
              <span class="tool-name">{{ getToolName(tc.tool) }}</span>
              <template v-if="tc.titles && tc.titles.length > 0">
                <span class="tool-tags">
                  <span class="tag knowledge">[Knowledge]</span>
                  <span class="tag content">[Content]</span>
                  <span class="tag source">* "{{ tc.titles[0] }}"</span>
                </span>
              </template>
              <template v-else>
                <span class="tool-arrow">→</span>
                <span
                  class="tool-summary"
                  :class="{
                    success: tc.summary === '检索成功',
                    warning: tc.summary.includes('暂无'),
                  }"
                  >{{
                    tc.summary ||
                    (tc.status === "loading" ? "执行中..." : "完成")
                  }}</span
                >
              </template>
            </div>
          </div>
          <!-- 检测结果卡片 -->
          <DetectionResultCard
            v-if="msg.detectionResult"
            :result="msg.detectionResult"
          />

          <!-- 多智能体调用链可视化 -->
          <div
            v-if="msg.agentChain && msg.agentChain.length > 0"
            class="agent-chain"
          >
            <div class="agent-chain-title">
              <el-icon><Connection /></el-icon>
              <span>多智能体调用链</span>
            </div>
            <div class="agent-chain-path">
              <div
                v-for="(step, idx) in msg.agentChain"
                :key="idx"
                class="agent-chain-step"
                :class="getAgentNodeClass(step.node)"
              >
                <div class="agent-node">
                  <el-icon><component :is="getAgentIcon(step.node)" /></el-icon>
                  <span>{{ getAgentNodeName(step.node) }}</span>
                </div>
                <div v-if="idx < msg.agentChain.length - 1" class="agent-arrow">
                  <el-icon><ArrowRight /></el-icon>
                </div>
              </div>
            </div>
            <div class="agent-chain-details">
              <div
                v-for="(step, idx) in msg.agentChain"
                :key="idx"
                class="agent-step-detail"
              >
                <span class="detail-label">{{ getAgentNodeName(step.node) }}:</span>
                <span class="detail-value">{{ getAgentStepSummary(step) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 工具调用提示 -->
        <div v-if="msg.toolCall" class="tool-call-info">
          <el-tag size="small" type="info">
            🔧 调用工具: {{ msg.toolCall.tool }}
          </el-tag>
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
      <el-button @click="handleVideoDetect" :disabled="agentStore.isLoading"
        >🎬 视频</el-button
      >
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
        accept="image/*,video/mp4,video/avi,video/quicktime,video/x-msvideo,.zip"
        style="display: none"
        @change="handleFileSelect"
        multiple
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
</template>

<script setup>
/**
 * ChatPage.vue — 智能对话界面
 *
 * 功能：
 *   - 消息气泡（用户/AI 区分）
 *   - 文件附件上传（图片/ZIP 拖拽或选择）
 *   - SSE 流式渲染 AI 回复
 *   - 检测结果卡片展示
 *   - 快捷操作栏（单图/批量/视频/摄像头）
 *   - 中断当前对话
 */
import {
  detectBatch,
  detectSingle,
  detectVideo,
  detectZip,
  getVideoStatus,
} from "@/api/detection";
import DetectionResultCard from "@/components/DetectionResultCard.vue";
import { useAgentStore } from "@/stores/agent";
import { renderMarkdown } from "@/utils/markdown";
import request from "@/utils/request";
import { streamChat } from "@/utils/stream";
import {
  ArrowRight,
  Camera,
  CircleCheck,
  CircleCheckFilled,
  Connection,
  InfoFilled,
  Loading,
  MessageBox,
  PieChart,
  Setting
} from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, nextTick, onMounted, ref } from "vue";

// ── Store ──
const agentStore = useAgentStore();

// ── 响应式状态 ──
const inputText = ref("");
const selectedFile = ref(null);
const selectedFiles = ref([]);
const selectedVideo = ref(null);
const messageListRef = ref(null);
const fileInputRef = ref(null);

// ── 计算属性 ──
const canSend = computed(() => {
  return (
    inputText.value.trim() ||
    selectedFile.value ||
    selectedFiles.value.length > 0
  );
});

/** 发送消息 */
async function sendMessage() {
  const text = inputText.value.trim();
  if (
    !text &&
    !selectedFile.value &&
    selectedFiles.value.length === 0 &&
    !selectedVideo.value
  )
    return;

  const message = text;
  const filesToSend =
    selectedFiles.value.length > 0
      ? selectedFiles.value
      : selectedFile.value
        ? [selectedFile.value]
        : [];
  const videoToSend = selectedVideo.value;
  const isZip = selectedFile.value && selectedFile.value.name.endsWith(".zip");

  let imagePreviews = [];
  let videoPreview = null;

  if (isZip) {
    agentStore.addMessage({
      role: "user",
      content: message,
      image: selectedFile.value.name,
      imagePreview: URL.createObjectURL(selectedFile.value),
    });
  } else if (videoToSend) {
    videoPreview = URL.createObjectURL(videoToSend);
    agentStore.addMessage({
      role: "user",
      content: message || `[视频检测] ${videoToSend.name}`,
      videoUrl: videoPreview,
    });
  } else if (filesToSend.length > 0) {
    imagePreviews = filesToSend.map((f) => URL.createObjectURL(f));
    agentStore.addMessage({
      role: "user",
      content: message,
      image:
        filesToSend.length === 1
          ? filesToSend[0].name
          : `${filesToSend.length} 张图片`,
      images: filesToSend.length > 1 ? imagePreviews : [],
      imagePreview: filesToSend.length === 1 ? imagePreviews[0] : null,
    });
  } else {
    agentStore.addMessage({
      role: "user",
      content: message,
    });
  }

  inputText.value = "";
  selectedFile.value = null;
  selectedFiles.value = [];
  selectedVideo.value = null;

  agentStore.addMessage({
    role: "assistant",
    content: "",
    loading: true,
    toolCalls: [],
  });

  scrollToBottom();

  let serverImagePath = null;
  let serverVideoPath = null;
  let serverImagePaths = [];

  try {
    if (isZip) {
      const formData = new FormData();
      formData.append("file", selectedFile.value);
      const uploadResult = await request.post("/chat/upload", formData);
      serverImagePath = uploadResult.image_path;
    } else if (videoToSend) {
      const formData = new FormData();
      formData.append("file", videoToSend);
      const uploadResult = await request.post("/chat/upload", formData);
      serverVideoPath = uploadResult.image_path;
    } else if (filesToSend.length === 1) {
      const formData = new FormData();
      formData.append("file", filesToSend[0]);
      const uploadResult = await request.post("/chat/upload", formData);
      serverImagePath = uploadResult.image_path;
    } else if (filesToSend.length > 1) {
      const formData = new FormData();
      filesToSend.forEach((f) => formData.append("files", f));
      const uploadResult = await request.post("/chat/upload", formData);
      serverImagePaths = uploadResult.image_paths || [];
    }
  } catch (err) {
    console.error("[文件上传失败]", err);
    const lastMsg = agentStore.messages[agentStore.messages.length - 1];
    lastMsg.content = `文件上传失败：${err.message || "未知错误"}`;
    lastMsg.loading = false;
    lastMsg.error = true;
    return;
  }

  if (!agentStore.currentSessionId) {
    agentStore.currentSessionId = Math.random().toString(36).slice(2, 10);
  }

  const requestBody = {
    message:
      message ||
      (isZip
        ? `检测 ZIP 文件: ${selectedFile.value.name}`
        : videoToSend
          ? `检测视频: ${videoToSend.name}`
          : `检测图片`),
    session_id: agentStore.currentSessionId,
    ...(serverImagePath ? { image_path: serverImagePath } : {}),
    ...(serverVideoPath ? { video_path: serverVideoPath } : {}),
    ...(serverImagePaths.length > 0 ? { image_paths: serverImagePaths } : {}),
  };

  let fullContent = "";

  const stop = streamChat("/api/chat/multi-agent", requestBody, {
    onMessage: (data) => {
      const lastMsg = agentStore.messages[agentStore.messages.length - 1];

      if (data.type === "text_chunk") {
        fullContent += data.content;
        agentStore.updateLastAssistantMessage(fullContent);
        const latestMsg = agentStore.messages[agentStore.messages.length - 1];
        if (data.knowledge_sources) {
          latestMsg.knowledgeSources = data.knowledge_sources;
        }
        if (data.has_knowledge !== undefined) {
          latestMsg.hasKnowledge = data.has_knowledge;
        }
        scrollToBottom();
      } else if (data.type === "tool_start") {
        // Day 11：添加工具调用记录（loading 状态）
        if (!lastMsg.toolCalls) lastMsg.toolCalls = [];
        lastMsg.toolCalls.push({
          tool: data.tool,
          status: "loading",
          summary: "",
        });
        scrollToBottom();
      } else if (data.type === "tool_end") {
        if (!lastMsg.toolCalls) lastMsg.toolCalls = [];
        const tc = lastMsg.toolCalls.find(
          (t) => t.tool === data.tool && t.status === "loading",
        );
        if (tc) {
          tc.status = "done";
          tc.summary = data.summary?.slice(0, 80) || "完成";
        }
        if (data.result) {
          try {
            const result =
              typeof data.result === "string"
                ? JSON.parse(data.result)
                : data.result;
            const isDetectionResult =
              result.annotated_image_url ||
              result.annotated_video_url ||
              result.annotated_images ||
              result.type === "video";
            if (isDetectionResult) {
              lastMsg.detectionResult = result;
            }
            if (data.tool === "search_knowledge") {
              if (result.knowledge && result.knowledge.length > 0) {
                const sources = [
                  ...new Set(result.knowledge.map((k) => k.source)),
                ];
                const titles = [
                  ...new Set(
                    result.knowledge.map(
                      (k) => k.content.match(/#\s+(.+)/)?.[1] || k.source,
                    ),
                  ),
                ];
                if (tc) {
                  tc.summary = "检索成功";
                  tc.sources = sources;
                  tc.titles = titles;
                }
              } else if (result.answer === "知识库中暂无相关内容") {
                if (tc) tc.summary = "知识库中暂无此内容，回答来自LLM";
              }
            }
          } catch (e) {
            console.error("[解析工具结果失败]", e);
          }
        }
        scrollToBottom();
      } else if (data.type === "tool_call") {
        // 兼容旧版事件类型
        lastMsg.toolCall = { tool: data.tool, input: data.input };
      } else if (data.type === "tool_result") {
        // 兼容旧版事件类型
        try {
          const result = JSON.parse(data.result);
          if (result.detections) {
            lastMsg.detectionResult = result;
            lastMsg.loading = false;
          }
        } catch (e) {
          lastMsg.content += `\n[工具结果: ${data.result?.substring(0, 100)}...]`;
        }
        scrollToBottom();
      } else if (data.type === "error") {
        lastMsg.content = data.content;
        lastMsg.loading = false;
        lastMsg.error = true;
      } else if (data.type === "multi_agent") {
        if (!lastMsg.agentChain) lastMsg.agentChain = [];
        lastMsg.agentChain.push({
          node: data.node,
          data: data.data,
        });
        if (data.data.detection_result) {
          const result = data.data.detection_result;
          const isDetectionResult =
            result.annotated_image_url ||
            result.annotated_video_url ||
            result.annotated_images ||
            result.type === "video";
          if (isDetectionResult) {
            lastMsg.detectionResult = result;
          }
        }
        scrollToBottom();
      }
    },
    onDone: () => {
      const lastMsg = agentStore.messages[agentStore.messages.length - 1];
      if (lastMsg.loading) {
        lastMsg.loading = false;
      }
      agentStore.setLoading(false);
    },
    onError: (err) => {
      const lastMsg = agentStore.messages[agentStore.messages.length - 1];
      lastMsg.content = `抱歉，处理出错了：${err.message}`;
      lastMsg.loading = false;
      lastMsg.error = true;
      agentStore.setLoading(false);
      ElMessage.error("对话请求失败，请重试");
    },
  });

  // 保存中断函数到 store
  agentStore.abortController = stop;
}

/** 停止生成 */
function handleStop() {
  agentStore.abort();
  const lastMsg = agentStore.messages[agentStore.messages.length - 1];
  if (lastMsg.loading) {
    lastMsg.loading = false;
    lastMsg.content += "\n[已停止生成]";
  }
}

/** 触发文件选择框 */
function triggerFileInput() {
  fileInputRef.value?.click();
}

/** 文件选择回调 */
function handleFileSelect(event) {
  const files = Array.from(event.target.files);
  if (!files.length) return;

  const isZip = files.some((f) => f.name.endsWith(".zip"));
  const isVideo = files.some((f) => f.type.startsWith("video/"));
  const isImage = files.some((f) => f.type.startsWith("image/"));

  if (isZip && files.length === 1) {
    selectedFile.value = files[0];
    selectedFiles.value = [];
    selectedVideo.value = null;
    files[0]._tempPath = URL.createObjectURL(files[0]);
    ElMessage.info(`ZIP 文件已选择: ${files[0].name}`);
  } else if (isVideo) {
    const videoFile = files.find((f) => f.type.startsWith("video/"));
    selectedFile.value = videoFile;
    selectedFiles.value = [];
    selectedVideo.value = videoFile;
    videoFile._tempPath = URL.createObjectURL(videoFile);
    ElMessage.info(`视频文件已选择: ${videoFile.name}`);
  } else if (isImage) {
    if (files.length === 1) {
      selectedFile.value = files[0];
      selectedFiles.value = [];
      selectedVideo.value = null;
      files[0]._tempPath = URL.createObjectURL(files[0]);
      ElMessage.info(`图片已选择: ${files[0].name}`);
    } else {
      selectedFiles.value = files;
      selectedFile.value = null;
      selectedVideo.value = null;
      files.forEach((f) => {
        f._tempPath = URL.createObjectURL(f);
      });
      ElMessage.info(`${files.length} 张图片已选择`);
    }
  }

  event.target.value = "";
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
      });

      // 构造 FormData 并调用 API
      const formData = new FormData();
      formData.append("file", file);

      try {
        const result = await detectSingle(formData);
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.content = `检测完成！发现 ${result.total_objects} 个目标。`;
        lastMsg.loading = false;
        lastMsg.detectionResult = result;
      } catch (err) {
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.content = "检测失败，请重试";
        lastMsg.loading = false;
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
      });

      try {
        const apiCall = isZip ? detectZip(formData) : detectBatch(formData);
        const result = await apiCall;
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];

        // 检查是否有错误
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
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.content = `批量检测失败：${err.message || err}`;
        lastMsg.loading = false;
        lastMsg.error = true;
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

    // 校验文件大小（50MB）
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
      ElMessage.warning("视频文件不能超过 50MB");
      return;
    }

    // 创建视频的 Blob URL 用于预览
    const videoUrl = URL.createObjectURL(file);

    // 添加用户消息
    agentStore.addMessage({
      role: "user",
      content: `[视频检测] ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)}MB)`,
      videoUrl,
    });

    // 添加加载占位
    agentStore.addMessage({
      role: "assistant",
      content: "正在上传视频...",
      loading: true,
    });

    // 上传视频
    const formData = new FormData();
    formData.append("file", file);

    try {
      const uploadResult = await detectVideo(formData);
      const taskId = uploadResult.task_id;

      // 更新加载消息
      const lastMsg = agentStore.messages[agentStore.messages.length - 1];
      lastMsg.content = "视频已上传，正在处理中...";

      // 开始轮询进度
      await pollVideoProgress(taskId);
    } catch (err) {
      console.error("[视频检测失败]", err);
      const lastMsg = agentStore.messages[agentStore.messages.length - 1];
      lastMsg.content = `视频检测失败：${err.message || err}`;
      lastMsg.loading = false;
      lastMsg.error = true;
    }
  };
  input.click();
}

/**
 * 轮询视频检测进度
 * @param {number} taskId - 视频检测任务 ID
 */
async function pollVideoProgress(taskId) {
  const maxRetries = 300; // 最多轮询 300 次（5 分钟 @1s 间隔）
  let retries = 0;

  return new Promise((resolve, reject) => {
    const timer = setInterval(async () => {
      retries++;

      try {
        const status = await getVideoStatus(taskId);

        const lastMsg = agentStore.messages[agentStore.messages.length - 1];

        if (status.status === "completed") {
          clearInterval(timer);
          lastMsg.content = `视频检测完成！共处理 ${status.result?.processed_frames || 0} 帧，发现 ${status.result?.total_objects || 0} 个目标。`;
          lastMsg.loading = false;
          lastMsg.detectionResult = {
            ...status.result,
            type: "video",
          };
          resolve(status);
        } else if (status.status === "failed") {
          clearInterval(timer);
          lastMsg.content = `视频检测失败：${status.message || "未知错误"}`;
          lastMsg.loading = false;
          lastMsg.error = true;
          reject(new Error(status.message));
        } else {
          // 仍在处理中
          lastMsg.content = `视频处理中... ${status.message || ""}`;
        }

        // 防止超时
        if (retries >= maxRetries) {
          clearInterval(timer);
          const lastMsg = agentStore.messages[agentStore.messages.length - 1];
          lastMsg.content = "视频处理超时，请稍后在历史记录中查看结果";
          lastMsg.loading = false;
          reject(new Error("timeout"));
        }
      } catch (err) {
        console.error("[轮询视频进度失败]", err);
        // 不立即 reject，继续重试
      }
    }, 1000); // 每秒轮询一次
  });
}

// 消息对象的数据结构增强
const createMessage = (role, content = "") => ({
  id: Date.now() + Math.random(),
  role, // "user" | "ai"
  content, // 文本内容
  toolCalls: [], // 工具调用记录 [{tool, status, summary}]
  isStreaming: false, // 是否正在流式接收
  error: null, // 错误信息
});

// 工具名称映射
function getToolName(toolKey) {
  const map = {
    detect_single_image: "单图检测",
    detect_batch_images: "批量检测",
    detect_zip_images_file: "ZIP 检测",
    detect_video_file: "视频检测",
    search_knowledge: "知识库检索",
    query_detection_stats: "统计查询",
    query_detection_history: "历史查询",
    query_user_list: "用户查询",
  };
  return map[toolKey] || toolKey;
}

function getAgentNodeName(node) {
  const map = {
    supervisor: "Supervisor",
    detection: "检测 Agent",
    analysis: "分析 Agent",
    qa: "问答 Agent",
    summarize: "汇总",
  };
  return map[node] || node;
}

function getAgentIcon(node) {
  const icons = {
    supervisor: Setting,
    detection: Camera,
    analysis: PieChart,
    qa: MessageBox,
    summarize: CircleCheck,
  };
  return icons[node] || CircleCheck;
}

function getAgentNodeClass(node) {
  const classes = {
    supervisor: "node-supervisor",
    detection: "node-detection",
    analysis: "node-analysis",
    qa: "node-qa",
    summarize: "node-summarize",
  };
  return classes[node] || "node-default";
}

function getAgentStepSummary(step) {
  const node = step.node;
  const data = step.data || {};

  if (node === "supervisor") {
    return `路由决策: ${data.next_agent || "未知"}`;
  } else if (node === "detection") {
    const result = data.detection_result || {};
    if (result.error) return `失败: ${result.error}`;
    return `检测到 ${result.total_objects || 0} 个目标`;
  } else if (node === "analysis") {
    const result = data.analysis_result || {};
    if (result.error) return `失败: ${result.error}`;
    return `任务数: ${result.total_tasks || 0}, 目标数: ${result.total_objects || 0}`;
  } else if (node === "qa") {
    const result = data.qa_result || {};
    if (result.error) return `失败: ${result.error}`;
    if (result.knowledge && result.knowledge.length > 0) {
      return `检索到 ${result.knowledge.length} 条知识`;
    }
    return "知识库中暂无相关内容";
  } else if (node === "summarize") {
    return "生成最终回复";
  }
  return JSON.stringify(data).slice(0, 50);
}

onMounted(() => {
  // 页面加载时显示欢迎消息
  if (agentStore.messages.length === 0) {
    agentStore.addMessage({
      role: "assistant",
      content:
        "你好！我是 RSOD 目标检测智能体助手。\n\n你可以：\n- 上传一张图片，让我帮你检测目标\n- 使用下方的快捷按钮直接触发检测\n- 用自然语言描述你的需求\n\n试试发一张图片给我吧！",
    });
  }
});
</script>

<style lang="scss" scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f5f5;
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

.markdown-body {
  /* markdown 渲染后的 HTML 样式 */
  h1,
  h2,
  h3 {
    margin-top: 8px;
    margin-bottom: 4px;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    margin: 8px 0;
  }
  th,
  td {
    border: 1px solid #e0e0e0;
    padding: 4px 8px;
  }
  code {
    background: #f0f0f0;
    padding: 2px 4px;
    border-radius: 3px;
  }
}

.typing-indicator {
  display: flex;
  gap: 4px;

  span {
    width: 6px;
    height: 6px;
    background: #999;
    border-radius: 50%;
    animation: typing 1.2s infinite;
  }

  span:nth-child(2) {
    animation-delay: 0.2s;
  }
  span:nth-child(3) {
    animation-delay: 0.4s;
  }
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

/* ── 视频附件 ── */
.video-attachment {
  video {
    max-width: 280px;
    max-height: 200px;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
    background: #000;
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

/* ── 工具调用信息 ── */
.tool-call-info {
  margin-top: 8px;
  padding: 4px 8px;
  background: #f5f5f5;
  border-radius: 4px;
  font-size: 12px;
  color: #666;
}

@keyframes typing {
  0%,
  60%,
  100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  30% {
    opacity: 1;
    transform: translateY(-4px);
  }
}

.tool-calls {
  margin: 8px 0;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.tool-call-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  font-size: 13px;
  color: #606266;

  &.is-loading {
    color: #409eff;
  }

  .tool-name {
    font-weight: 500;
  }

  .tool-arrow {
    color: #909399;
    font-size: 14px;
    font-weight: bold;
  }

  .tool-summary {
    color: #909399;
    font-size: 12px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;

    &.success {
      color: #67c23a;
      font-weight: 500;
    }

    &.warning {
      color: #e6a23c;
      font-weight: 500;
    }
    max-width: 300px;
  }

  .tool-tags {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .tag {
    font-size: 12px;
    padding: 2px 6px;
    border-radius: 4px;

    &.knowledge {
      background: #e8f5e9;
      color: #2e7d32;
    }

    &.content {
      background: #e3f2fd;
      color: #1565c0;
    }

    &.source {
      background: #fff8e1;
      color: #f57c00;
      font-style: italic;
    }
  }
}

.knowledge-sources {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 0;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  font-size: 13px;
  color: #606266;

  .knowledge-label {
    font-weight: 500;
  }

  .tag {
    font-size: 12px;
    padding: 2px 6px;
    border-radius: 4px;

    &.knowledge {
      background: #e8f5e9;
      color: #2e7d32;
    }

    &.content {
      background: #e3f2fd;
      color: #1565c0;
    }

    &.source {
      background: #fff8e1;
      color: #f57c00;
      font-style: italic;
    }
  }

  &.no-knowledge {
    .no-knowledge-text {
      color: #909399;
      margin-left: 4px;
    }
  }
}

.agent-chain {
  margin: 12px 0;
  padding: 12px;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
}

.agent-chain-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 12px;
}

.agent-chain-path {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.agent-chain-step {
  display: flex;
  align-items: center;
  gap: 8px;
}

.agent-node {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
}

.node-supervisor .agent-node {
  background: #e0e7ff;
  color: #4338ca;
}

.node-detection .agent-node {
  background: #d1fae5;
  color: #065f46;
}

.node-analysis .agent-node {
  background: #dbeafe;
  color: #1e40af;
}

.node-qa .agent-node {
  background: #fef3c7;
  color: #92400e;
}

.node-summarize .agent-node {
  background: #f3f4f6;
  color: #374151;
}

.agent-arrow {
  color: #94a3b8;
  font-size: 16px;
}

.agent-chain-details {
  padding-top: 8px;
  border-top: 1px dashed #cbd5e1;
  font-size: 12px;
}

.agent-step-detail {
  display: flex;
  gap: 8px;
  padding: 4px 0;
}

.detail-label {
  color: #64748b;
  font-weight: 500;
  min-width: 80px;
}

.detail-value {
  color: #334155;
}
</style>