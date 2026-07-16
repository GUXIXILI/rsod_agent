import { defineStore } from 'pinia'

/**
 * 智能体状态管理 Store
 * 管理会话、消息和 SSE 连接状态
 */
export const useAgentStore = defineStore('agent', {
  state: () => ({
    /** 当前会话 ID */
    currentSessionId: null,
    /** 会话列表，每项 { id, title, created_at, messages[] } */
    sessions: [],
    /** 当前会话的消息列表，每项 { role, content, timestamp, loading, error, detectionResult, toolCall, toolCalls, thinking } */
    messages: [],
    /** 是否正在等待 AI 回复 */
    isLoading: false,
    /** 当前 SSE 连接的中断函数，用于中断请求 */
    abortController: null
  }),

  actions: {
    /**
     * 创建新会话
     * 保存当前会话到列表，清空消息列表，生成新的会话 ID
     */
    newChat() {
      // 保存当前会话（如果有消息）
      if (this.currentSessionId && this.messages.length > 0) {
        this._saveCurrentSession()
      }
      this.currentSessionId = Date.now().toString()
      this.messages = []
      this.isLoading = false
      // 若有正在进行的请求，先中断
      this.abort()
    },

    /**
     * 切换会话
     * @param {string} sessionId - 目标会话 ID
     */
    switchSession(sessionId) {
      if (sessionId === this.currentSessionId) return
      // 保存当前会话
      this._saveCurrentSession()
      // 加载目标会话
      const session = this.sessions.find(s => s.id === sessionId)
      if (session) {
        this.currentSessionId = session.id
        this.messages = session.messages || []
      }
    },

    /**
     * 内部方法：保存当前会话到列表
     */
    _saveCurrentSession() {
      if (!this.currentSessionId || this.messages.length === 0) return
      const idx = this.sessions.findIndex(s => s.id === this.currentSessionId)
      const title = this._generateSessionTitle()
      const sessionData = {
        id: this.currentSessionId,
        title,
        created_at: this.messages[0]?.timestamp || Date.now(),
        messages: [...this.messages]
      }
      if (idx >= 0) {
        this.sessions[idx] = sessionData
      } else {
        this.sessions.unshift(sessionData)
      }
    },

    /**
     * 内部方法：根据首条用户消息生成会话标题
     */
    _generateSessionTitle() {
      const firstUser = this.messages.find(m => m.role === 'user')
      if (firstUser && firstUser.content) {
        return firstUser.content.substring(0, 30) + (firstUser.content.length > 30 ? '...' : '')
      }
      return '新对话'
    },

    /**
     * 添加消息到当前会话
     * @param {Object} message - 消息对象 { role, content, timestamp, ... }
     */
    addMessage(message) {
      if (!message.timestamp) {
        message.timestamp = Date.now()
      }
      this.messages.push(message)
    },

    /**
     * 更新最后一条 assistant 消息的内容（流式渲染用）
     * @param {string} content - 新的完整内容
     */
    updateLastAssistantMessage(content) {
      const msgs = this.messages
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === 'assistant') {
          msgs[i].content = content
          // 有内容时自动取消 loading 状态
          if (content && content.length > 0) {
            msgs[i].loading = false
          }
          return
        }
      }
    },

    /**
     * 获取最后一条 assistant 消息
     * @returns {Object|null} 最后一条 assistant 消息
     */
    getLastAssistantMessage() {
      for (let i = this.messages.length - 1; i >= 0; i--) {
        if (this.messages[i].role === 'assistant') {
          return this.messages[i]
        }
      }
      return null
    },

    /**
     * 设置加载状态
     * @param {boolean} val - 是否正在加载
     */
    setLoading(val) {
      this.isLoading = val
    },

    /**
     * 中断当前 SSE 连接
     */
    abort() {
      if (this.abortController && typeof this.abortController === 'function') {
        this.abortController()
        this.abortController = null
      }
      this.isLoading = false
    }
  }
})