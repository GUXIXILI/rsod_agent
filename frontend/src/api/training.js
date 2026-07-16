import request from '@/utils/request'

/**
 * 获取活跃场景列表
 * @returns {Promise} 活跃场景列表响应
 */
export const getActiveScenes = () => {
  return request.get('/scenes')
}

/**
 * 启动训练
 * @param {Object} data - 训练配置信息
 * @returns {Promise} 训练启动响应
 */
export const startTraining = (data) => {
  return request.post('/training/start', data)
}

/**
 * 获取训练任务列表
 * @returns {Promise} 训练任务列表响应
 */
export const getTrainingTasks = () => {
  return request.get('/training/tasks')
}

/**
 * 获取训练状态
 * @param {string} taskUuid - 任务UUID
 * @returns {Promise} 训练状态响应
 */
export const getTrainingStatus = (taskId) => {
  return request.get(`/training/status/${taskId}`)
}

/**
 * 获取所有epoch指标
 * @param {string} taskUuid - 任务UUID
 * @returns {Promise} 训练指标响应
 */
export const getTrainingMetrics = (taskId) => {
  return request.get(`/training/metrics/${taskId}`)
}

/**
 * 停止训练
 * @param {string} taskUuid - 任务UUID
 * @returns {Promise} 停止响应
 */
export const stopTraining = (taskId) => {
  return request.post(`/training/stop/${taskId}`)
}

/**
 * 获取训练结果 CSV
 * @param {string} taskUuid - 任务UUID
 * @returns {Promise} CSV 数据响应
 */
export const getTrainingResults = (taskUuid) => {
  return request.get(`/training/results/${taskUuid}`)
}

/**
 * 评估模型（运行 model.val()）
 * @param {string} taskId - 任务UUID
 * @param {Object} data - 评估配置 { split, conf, iou }
 * @returns {Promise}
 */
export const validateModel = (taskId, data) => {
  return request.post(`/training/validate/${taskId}`, data, { timeout: 300000 })
}

/**
 * 导出模型
 * @param {string} taskId - 任务UUID
 * @param {Object} data - 导出配置 { version, description, set_default, upload_minio, format }
 * @returns {Promise}
 */
export const exportModel = (taskId, data) => {
  return request.post(`/training/export/${taskId}`, data)
}

/**
 * 测试图预测
 * @param {FormData} formData - 包含 file, task_uuid, conf, iou 的 FormData
 * @returns {Promise}
 */
export const predictModel = (formData) => {
  return request.post('/training/predict', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
