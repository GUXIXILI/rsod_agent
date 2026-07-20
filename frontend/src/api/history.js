import request from '@/utils/request'

export const getHistoryTasks = (params) => request.get('/history/tasks', { params })

export const getHistoryTaskDetail = (taskId) => request.get(`/history/tasks/${taskId}`)

export const deleteHistoryTask = (taskId) => request.delete(`/history/tasks/${taskId}`)

// 批量删除检测记录（task_ids 为 ID 数组）
export const batchDeleteHistoryTasks = (taskIds) =>
  request.post('/history/tasks/batch-delete', { task_ids: taskIds })