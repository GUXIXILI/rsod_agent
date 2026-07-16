/**
 * 检测相关 API 接口
 *
 * 快捷按钮直接调用这些接口（跳过 LLM），结果渲染在对话中
 */
import request from "@/utils/request";

/**
 * 单图检测
 * @param {FormData} formData - 包含 file 字段的 FormData
 * @param {number} [sceneId=1] - 场景 ID（默认 1）
 * @returns {Promise} - 检测结果（标注图 + 目标统计）
 */
export async function detectSingle(formData, sceneId = 1) {
  // 后端要求 scene_id 为 Form 字段，追加到 FormData
  if (!formData.has("scene_id")) {
    formData.append("scene_id", sceneId);
  }
  // 不设置 Content-Type，让 axios 自动添加 multipart/form-data + boundary
  return (await request.post("/detection/single", formData, {
    timeout: 60000,
  })).data;
}

/**
 * 批量检测
 * @param {FormData} formData - 包含多个 files 字段的 FormData
 * @param {number} [sceneId=1] - 场景 ID（默认 1）
 * @returns {Promise} - 批量检测结果
 */
export async function detectBatch(formData, sceneId = 1) {
  if (!formData.has("scene_id")) {
    formData.append("scene_id", sceneId);
  }
  return (await request.post("/detection/batch", formData, {
    timeout: 120000,
  })).data;
}

/**
 * ZIP 检测
 * @param {FormData} formData - 包含 file 字段的 FormData
 * @param {number} [sceneId=1] - 场景 ID（默认 1）
 * @returns {Promise} - ZIP 解压后的批量检测结果
 */
export async function detectZip(formData, sceneId = 1) {
  if (!formData.has("scene_id")) {
    formData.append("scene_id", sceneId);
  }
  return (await request.post("/detection/zip", formData, {
    timeout: 180000,
  })).data;
}

/**
 * 获取检测任务状态
 * @param {number} taskId - 检测任务 ID
 * @returns {Promise} - 任务状态和结果
 */
export function getDetectionStatus(taskId) {
  return request.get(`/detection/tasks/${taskId}`);
}

/**
 * 视频检测
 * @param {FormData} formData - 包含 file 字段的 FormData（视频文件）
 * @param {number} [sceneId=1] - 场景 ID（默认 1）
 * @returns {Promise} - { task_id, status, message }
 */
export function detectVideo(formData, sceneId = 1) {
  if (!formData.has("scene_id")) {
    formData.append("scene_id", sceneId);
  }
  return request.post("/detection/video", formData, {
    timeout: 120000, // 视频上传可能较慢
  });
}

/**
 * 查询视频检测进度
 * @param {number} taskId - 视频检测任务 ID
 * @returns {Promise} - { status, progress, result, ... }
 */
export function getVideoStatus(taskId) {
  return request.get(`/detection/video/status/${taskId}`);
}