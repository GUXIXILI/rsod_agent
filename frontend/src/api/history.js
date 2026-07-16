import request from '@/utils/request'

/**
 * 获取检测历史任务列表（分页）
 * @param {Object} params - 查询参数 { page, page_size, fire_level, task_type, file_name, start_time, end_time, scene_id }
 * @returns {Promise}
 */
export const getHistoryTasks = (params) => request.get('/history/tasks', { params })

/**
 * 获取检测任务详情
 * @param {number} taskId - 检测任务 ID
 * @returns {Promise}
 */
export const getHistoryTaskDetail = (taskId) => request.get(`/history/tasks/${taskId}`)

/**
 * 删除检测任务
 * @param {number} taskId - 检测任务 ID
 * @returns {Promise}
 */
export const deleteHistoryTask = (taskId) => request.delete(`/history/tasks/${taskId}`)