import request from '@/utils/request'

export const getOverview = () => request.get('/stats/overview')

export const getFireLevelDistribution = () => request.get('/stats/fire-level-distribution')

export const getTrend = (params) => request.get('/stats/trend', { params })