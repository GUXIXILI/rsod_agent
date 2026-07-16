import request from '@/utils/request'

/**
 * 上传文件到聊天
 * @param {FormData} formData - 包含 file 字段的 FormData
 * @returns {Promise}
 */
export function uploadChatFile(formData) {
  return request.post('/chat/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

/**
 * 获取会话列表
 * @returns {Promise}
 */
export function getSessions() {
  return request.get('/chat/sessions')
}

/**
 * 获取会话消息历史
 * @param {number} sessionId - 会话 ID
 * @returns {Promise}
 */
export function getSessionMessages(sessionId) {
  return request.get(`/chat/sessions/${sessionId}/messages`)
}

/**
 * 删除会话
 * @param {number} sessionId - 会话 ID
 * @returns {Promise}
 */
export function deleteSession(sessionId) {
  return request.delete(`/chat/sessions/${sessionId}`)
}

/**
 * 重命名会话
 * @param {number} sessionId - 会话 ID
 * @param {string} title - 新标题
 * @returns {Promise}
 */
export function renameSession(sessionId, title) {
  return request.patch(`/chat/sessions/${sessionId}`, { title })
}