/**
 * SSE 流式处理工具（Day 11 增强版）
 *
 * 支持两种调用方式：
 *
 *   方式 1（Day 11 新 API）：
 *     await streamChat({ message, image_path, session_id, onTextChunk, onToolStart, ... })
 *
 *   方式 2（兼容旧 API，ChatPage.vue 使用）：
 *     const stop = streamChat("/api/chat/stream", { message, image_path }, { onMessage, onDone, onError })
 *     返回 abort 函数，调用 stop() 即可中断请求
 *
 * 支持的事件类型：
 *   - thinking    Agent 正在思考
 *   - tool_start  开始调用工具
 *   - tool_end    工具调用完成
 *   - text_chunk  LLM 回复文本片段
 *   - done        对话完成
 *   - error       出错
 */

/**
 * 发起 SSE 流式对话请求（统一入口）
 *
 * 判断逻辑：第一个参数是字符串 → 旧 API；否则 → 新 API
 *
 * @param {Object|string} arg1 - options 对象（新 API）或 URL 字符串（旧 API）
 * @param {Object} [arg2] - 请求体（旧 API）
 * @param {Object} [arg3] - 回调选项（旧 API）
 * @returns {Function|Promise} 旧 API 返回 abort 函数，新 API 返回 Promise
 */
export function streamChat(arg1, arg2, arg3) {
  if (typeof arg1 === "string") {
    return _streamChatLegacy(arg1, arg2, arg3);
  }
  return _streamChatNew(arg1);
}

/**
 * 新 API：接收单个 options 对象，返回 Promise
 */
async function _streamChatNew(options) {
  const {
    message,
    image_path,
    session_id,
    onThinking,
    onToolStart,
    onToolEnd,
    onTextChunk,
    onDone,
    onError,
    signal,
  } = options;

  const token = localStorage.getItem("rsod_token");

  const response = await fetch("/api/chat/stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message, image_path, session_id }),
    signal,
  });

  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem("rsod_token");
      localStorage.removeItem("user_info");
      window.location.href = "/login";
      return;
    }
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  await _processStream(response, {
    thinking: onThinking,
    tool_start: onToolStart,
    tool_end: onToolEnd,
    text_chunk: onTextChunk,
    done: onDone,
    error: onError,
  });
}

/**
 * 旧 API：接收 URL + body + callbacks，返回 abort 函数
 * 兼容 ChatPage.vue 的调用方式
 */
function _streamChatLegacy(_url, body, callbacks) {
  const { message, image_path, image_paths, video_path, session_id } = body || {};
  const { onMessage, onDone, onError } = callbacks || {};

  const abortController = new AbortController();

  const token = localStorage.getItem("rsod_token");

  fetch(_url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message, image_path, image_paths, video_path, session_id }),
    signal: abortController.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem("rsod_token");
          localStorage.removeItem("user_info");
          window.location.href = "/login";
          return;
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      await _processStream(response, {
        // 旧 API 使用统一的 onMessage 处理所有事件
        _onMessage: onMessage,
      });

      // 流结束，调用 onDone
      onDone?.();
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError?.(err);
      }
    });

  // 返回 abort 函数（同步返回）
  return () => abortController.abort();
}

/**
 * 处理 SSE 响应流
 *
 * @param {Response} response - fetch 响应
 * @param {Object} handlers - 事件处理函数映射
 *   handlers._onMessage 存在时使用统一回调模式（旧 API）
 *   否则使用按类型分发的回调（新 API）
 */
async function _processStream(response, handlers) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop(); // 保留不完整的行

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;

      const data = line.slice(6).trim();
      if (data === "[DONE]") return;

      try {
        const event = JSON.parse(data);

        // 旧 API：统一回调 onMessage
        if (handlers._onMessage) {
          handlers._onMessage(event);
          continue;
        }

        // 新 API：按类型分发
        const handler = handlers[event.type];
        handler?.(event);
      } catch (_e) {
        // JSON 解析失败，跳过
      }
    }
  }
}

/**
 * 工具名称中文映射
 */
export const TOOL_NAME_MAP = {
  detect_single_image: "单图检测",
  detect_batch_images: "批量检测",
  detect_zip_images_file: "ZIP 检测",
  detect_video_file: "视频检测",
  search_knowledge: "知识库检索",
  query_detection_stats: "统计查询",
  query_detection_history: "历史查询",
  query_user_list: "用户查询",
};