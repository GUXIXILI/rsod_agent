/**
 * SSE 流式处理工具
 * 使用 fetch + ReadableStream + AbortController 实现
 */

/**
 * 发送流式聊天请求，通过 SSE 逐条接收消息
 *
 * @param {string} url - 请求地址
 * @param {object} body - POST 请求体（JSON 对象）
 * @param {object} callbacks - 回调函数集合
 * @param {function} callbacks.onMessage - 收到一条消息时调用，参数为解析后的 JSON 数据
 * @param {function} callbacks.onDone - 流结束时调用
 * @param {function} callbacks.onError - 发生错误时调用，参数为 error 对象
 * @returns {{ stop: function }} 返回包含 stop 方法的对象，调用 stop 可中断连接
 */
export function streamChat(url, body, callbacks) {
  const { onMessage, onDone, onError } = callbacks

  // 创建 AbortController 用于中断请求
  const abortController = new AbortController()

  // 从 localStorage 读取 token
  const token = localStorage.getItem('token')

  // 发起 POST 请求
  fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(body),
    signal: abortController.signal
  })
    .then(async (response) => {
      // 检查响应状态
      if (!response.ok) {
        throw new Error(`HTTP 错误: ${response.status} ${response.statusText}`)
      }

      // 获取 ReadableStream 的 reader
      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      // 逐块读取数据
      while (true) {
        const { done, value } = await reader.read()

        // 流结束
        if (done) {
          // 处理 buffer 中可能残留的数据
          if (buffer.trim()) {
            const lines = buffer.split('\n')
            for (const line of lines) {
              processLine(line.trim(), onMessage, onDone)
            }
          }
          onDone && onDone()
          break
        }

        // 解码并追加到缓冲区
        buffer += decoder.decode(value, { stream: true })

        // 按行分割处理
        const lines = buffer.split('\n')
        // 最后一行可能不完整，保留在 buffer 中
        buffer = lines.pop() || ''

        for (const line of lines) {
          processLine(line.trim(), onMessage, onDone)
        }
      }
    })
    .catch((error) => {
      // AbortError 由用户主动中断触发，静默处理，不触发 onError
      if (error.name === 'AbortError') {
        return
      }
      onError && onError(error)
    })

  // 返回 stop 方法供外部调用
  return {
    stop() {
      abortController.abort()
    }
  }
}

/**
 * 处理单行 SSE 数据
 *
 * @param {string} line - 单行文本
 * @param {function} onMessage - 消息回调
 * @param {function} onDone - 完成回调
 */
function processLine(line, onMessage, onDone) {
  // 跳过空行和非 data 行
  if (!line || !line.startsWith('data:')) {
    return
  }

  // 提取 data: 后面的内容
  const dataStr = line.slice(5).trim()

  // 收到 [DONE] 标记，流结束
  if (dataStr === '[DONE]') {
    onDone && onDone()
    return
  }

  // 空数据跳过
  if (!dataStr) {
    return
  }

  // 尝试解析 JSON
  try {
    const data = JSON.parse(dataStr)
    onMessage && onMessage(data)
  } catch (e) {
    // JSON 解析失败，忽略该行
    console.warn('SSE 数据解析失败:', dataStr)
  }
}