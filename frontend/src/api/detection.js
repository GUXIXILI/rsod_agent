import request from '@/utils/request'

export const detectSingle = (formData) => {
  return request.post('/detection/single', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const detectBatch = (formData) => {
  return request.post('/detection/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const detectVideo = (formData) => {
  return request.post('/detection/video', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const getDetectionTask = (taskId) => request.get(`/detection/tasks/${taskId}`)

export const getFireAlerts = (params) => request.get('/detection/alerts', { params })