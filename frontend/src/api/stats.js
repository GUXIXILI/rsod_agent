import request from '@/utils/request'

/**
 * 获取总览统计数据
 * @returns {Promise} { total_detections, fire_detected, smoke_detected, warning_count }
 */
export const getOverview = () => request.get('/stats/overview')

/**
 * 获取火情等级分布数据（饼图用）
 * @returns {Promise} [{ fire_level, count }]
 */
export const getFireLevelDistribution = () => request.get('/stats/fire-level-distribution')

/**
 * 获取近 N 天检测趋势数据（折线图用）
 * @param {Object} params - { days: 7 }
 * @returns {Promise} [{ date, count }]
 */
export const getTrend = (params) => request.get('/stats/trend', { params })

/**
 * 获取场景分布统计（柱状图数据）
 * @returns {Promise} [{ scene_name, count }]
 */
export const getSceneDistribution = () => request.get('/stats/scene-dist')