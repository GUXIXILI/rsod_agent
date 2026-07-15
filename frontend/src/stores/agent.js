import { defineStore } from 'pinia'

/**
 * 智能体状态管理 Store
 * 管理会话、消息和 SSE 连接状态
 */
export const useAgentStore = defineStore('agent', {
  state: () => ({
    /** 当前会话 ID */
    currentSessionId: null,
    /** 会话列表 */
    sessions: [],
    /** 当前会话的消息列表，每项 { role, content, timestamp } */
    messages: [],
    /** 是否正在等待 AI 回复 */
    isLoading: false,
    /** 当前 SSE 连接的控制对象，用于中断请求 */
    streamController: null
  }),

  actions: {
    /**
     * 创建新会话
     * 清空消息列表，生成新的会话 ID
     */
    newChat() {
      this.currentSessionId = null
      this.messages = []
      this.isLoading = false
      // 若有正在进行的请求，先中断
      this.abort()
    },

    /**
     * 添加消息到当前会话
     * @param {Object} message - 消息对象 { role, content, timestamp }
     */
    addMessage(message) {
      if (!message.timestamp) {
        message.timestamp = Date.now()
      }
      this.messages.push(message)
    },

    /** 更新最后一条助手消息的流式文本。 */
    updateLastAssistantMessage(content) {
      for (let index = this.messages.length - 1; index >= 0; index -= 1) {
        if (this.messages[index].role === 'assistant') {
          this.messages[index].content = content
          return
        }
      }
    },

    /**
     * 设置加载状态
     * @param {boolean} val - 是否正在加载
     */
    setLoading(val) {
      this.isLoading = val
    },

    /**
     * 设置当前 SSE 连接的控制对象
     * @param {Object} controller - streamChat 返回的 { stop } 对象
     */
    setStreamController(controller) {
      this.streamController = controller
    },

    /**
     * 中断当前 SSE 连接
     */
    abort() {
      if (this.streamController && typeof this.streamController.stop === 'function') {
        this.streamController.stop()
        this.streamController = null
      }
      this.isLoading = false
    }
  }
})
