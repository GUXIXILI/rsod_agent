import request from '@/utils/request'

export const getHistoryTasks = (params) => request.get('/history/tasks', { params })

export const getHistoryTaskDetail = (taskId) => request.get(`/history/tasks/${taskId}`)

export const deleteHistoryTask = (taskId) => request.delete(`/history/tasks/${taskId}`)