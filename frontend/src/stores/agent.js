import { defineStore } from 'pinia'
import request from '@/utils/request'

/**
 * 智能体状态管理 Store
 * 管理会话、消息和 SSE 连接状态，与后端 API 同步
 */
export const useAgentStore = defineStore('agent', {
  state: () => ({
    /** 当前会话 ID（后端主键，整数） */
    currentSessionId: null,
    /** 会话列表，每项来自后端 { id, title, created_at, message_count, last_message_at, ... } */
    sessions: [],
    /** 当前会话的消息列表，每项 { role, content, timestamp, loading, error, detectionResult, toolCalls, thinking } */
    messages: [],
    /** 是否正在等待 AI 回复 */
    isLoading: false,
    /** 当前 SSE 连接的中断函数，用于中断请求 */
    abortController: null
  }),

  actions: {
    // ══════════════════════════════════════════════════════════════
    // 会话管理（与后端 API 同步）
    // ══════════════════════════════════════════════════════════════

    /**
     * 从后端加载会话列表（分页）
     * GET /api/chat/sessions → { code, message, data: { items, total, skip, limit } }
     * 响应拦截器已解包 response.data，所以 res 直接是 { code, message, data }
     */
    async fetchSessions() {
      try {
        const res = await request.get('/chat/sessions')
        this.sessions = res.data?.items || []
      } catch (err) {
        console.error('获取会话列表失败:', err)
      }
    },

    /**
     * 从后端加载指定会话的消息历史
     * GET /api/chat/sessions/{id}/messages → { code, message, data: [...] }
     */
    async loadSessionMessages(sessionId) {
      this.currentSessionId = sessionId
      this.messages = []
      try {
        const res = await request.get(`/chat/sessions/${sessionId}/messages`)
        const rawMessages = res.data || []
        this.messages = rawMessages.map(m => this._transformMessage(m))
      } catch (err) {
        console.error('加载会话消息失败:', err)
        this.messages = []
      }
    },

    /**
     * 删除会话（含消息级联删除）
     * DELETE /api/chat/sessions/{id}
     */
    async deleteSession(sessionId) {
      try {
        await request.delete(`/chat/sessions/${sessionId}`)
        this.sessions = this.sessions.filter(s => s.id !== sessionId)
        if (this.currentSessionId === sessionId) {
          this.newChat()
        }
      } catch (err) {
        console.error('删除会话失败:', err)
      }
    },

    /**
     * 重命名会话
     * PATCH /api/chat/sessions/{id}
     * @param {number} sessionId - 会话 ID
     * @param {string} title - 新标题
     */
    async renameSession(sessionId, title) {
      try {
        await request.patch(`/chat/sessions/${sessionId}`, { title })
        const session = this.sessions.find(s => s.id === sessionId)
        if (session) {
          session.title = title
        }
      } catch (err) {
        console.error('重命名会话失败:', err)
        throw err
      }
    },

    /**
     * 创建新会话（仅重置前端状态，不调用后端创建）
     * 后端会在用户发送第一条消息时自动创建会话
     */
    newChat() {
      this.abort()
      this.currentSessionId = null
      this.messages = []
      this.isLoading = false
    },

    /**
     * 切换会话：从后端加载目标会话的消息历史
     * @param {number} sessionId - 目标会话 ID
     */
    async switchSession(sessionId) {
      if (sessionId === this.currentSessionId) return
      this.abort()
      await this.loadSessionMessages(sessionId)
      this.isLoading = false
    },

    // ══════════════════════════════════════════════════════════════
    // 消息管理
    // ══════════════════════════════════════════════════════════════

    /**
     * 将后端消息格式转换为前端消息格式
     */
    _transformMessage(m) {
      return {
        role: m.role,
        content: m.content || '',
        timestamp: m.created_at ? new Date(m.created_at).getTime() : Date.now(),
        toolCalls: this._parseToolCalls(m.tool_calls),
        detectionResult: this._parseDetectionResult(m.tool_result),
        loading: false,
        thinking: false,
        error: false,
      }
    },

    /**
     * 解析工具调用列表（后端存储为 JSON 字符串或 None）
     */
    _parseToolCalls(toolCalls) {
      if (!toolCalls) return []
      if (typeof toolCalls === 'string') {
        try { return JSON.parse(toolCalls) } catch { return [] }
      }
      return Array.isArray(toolCalls) ? toolCalls : []
    },

    /**
     * 解析检测结果（从 tool_result 中提取包含 detections 的 JSON）
     */
    _parseDetectionResult(toolResult) {
      if (!toolResult) return null
      try {
        const parsed = typeof toolResult === 'string' ? JSON.parse(toolResult) : toolResult
        if (parsed && parsed.detections) return parsed
        return null
      } catch {
        return null
      }
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