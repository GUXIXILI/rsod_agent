import request from '@/utils/request'

export const getOverview = () => request.get('/stats/overview')

export const getFireLevelDistribution = () => request.get('/stats/fire-level-distribution')

export const getTrend = (params) => request.get('/stats/trend', { params })

/** 获取场景分布统计（柱状图数据） */
export const getSceneDistribution = (params) => request.get('/stats/scene-dist', { params })

/** 获取任务类型分布统计（环形图数据） */
export const getTypeDistribution = (params) => request.get('/stats/type-dist', { params })