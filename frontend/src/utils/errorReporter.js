/**
 * 前端错误监控模块
 * 捕获 Vue 组件错误、JS 运行时错误、未处理 Promise 异常
 * 将错误信息存入 localStorage.error_logs，便于问题排查
 * 预留 reportToServer 接口，生产环境可配置开启后端上报
 */

/** 最大日志保留条数 */
const MAX_LOG_COUNT = 50

/** 错误日志存储键名 */
const STORAGE_KEY = 'error_logs'

/**
 * 读取当前已存储的错误日志
 * @returns {Array<Object>} 错误日志数组
 */
function readLogs() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    // 确保解析结果是数组
    return Array.isArray(parsed) ? parsed : []
  } catch {
    // 解析失败时返回空数组，避免阻塞后续逻辑
    return []
  }
}

/**
 * 将错误信息存入 localStorage.error_logs
 * 保留最近 MAX_LOG_COUNT 条，超出部分自动丢弃
 * @param {Object} errorEntry - 错误条目
 * @param {string} errorEntry.timestamp - 时间戳，ISO 格式
 * @param {string} errorEntry.type - 错误类型：'vue' | 'js' | 'promise'
 * @param {string} errorEntry.message - 错误消息
 * @param {string} [errorEntry.stack] - 错误堆栈（可选）
 * @param {string} errorEntry.url - 当前页面 URL
 */
function saveErrorLog(errorEntry) {
  const logs = readLogs()
  logs.push(errorEntry)

  // 超出最大条数时，保留最新的 MAX_LOG_COUNT 条
  if (logs.length > MAX_LOG_COUNT) {
    logs.splice(0, logs.length - MAX_LOG_COUNT)
  }

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(logs))
  } catch {
    // localStorage 写入失败（如配额已满）时静默忽略，不阻塞应用
  }
}

/**
 * 构建标准化的错误条目对象
 * @param {string} type - 错误类型
 * @param {string} message - 错误消息
 * @param {string} [stack] - 错误堆栈
 * @returns {Object} 标准化的错误条目
 */
function buildErrorEntry(type, message, stack) {
  return {
    timestamp: new Date().toISOString(),
    type,
    message: message || '未知错误',
    stack: stack || undefined,
    url: window.location.href
  }
}

/**
 * 向用户展示错误提示
 * 通过 Element Plus 的 ElMessage 组件提示用户
 * 如果 Element Plus 尚未加载，则静默跳过，避免二次报错
 */
function notifyUser() {
  try {
    // 动态导入 ElMessage，避免模块未加载时报错
    // 使用 require 风格导入确保兼容性
    import('element-plus').then(({ ElMessage }) => {
      if (ElMessage && typeof ElMessage.error === 'function') {
        ElMessage.error('应用发生错误，请刷新页面后重试')
      }
    }).catch(() => {
      // Element Plus 不可用时静默跳过
    })
  } catch {
    // 任何异常都静默忽略，避免通知逻辑本身引发新错误
  }
}

/**
 * 初始化全局错误监控
 * 应在 Vue 应用挂载之前调用，确保所有错误都能被捕获
 *
 * @param {import('vue').App} app - Vue 应用实例
 */
export function setupErrorReporting(app) {
  // ============================================================
  // 1. Vue 组件错误捕获
  // 捕获组件渲染、侦听器、生命周期钩子等执行过程中抛出的错误
  // ============================================================
  app.config.errorHandler = (err, instance, info) => {
    // 提取错误消息
    const message = err instanceof Error
      ? err.message
      : String(err)

    // 提取错误堆栈
    const stack = err instanceof Error
      ? err.stack
      : undefined

    // 可选的组件信息，帮助定位问题所在组件
    const componentInfo = instance ? ` (组件: ${instance.$.type?.name || '匿名组件'})` : ''

    console.error(`[Vue Error]${componentInfo} ${message}`, stack)

    // 存储错误日志
    const entry = buildErrorEntry('vue', message + componentInfo, stack)
    saveErrorLog(entry)

    // 提示用户
    notifyUser()
  }

  // ============================================================
  // 2. JS 运行时错误捕获
  // 捕获未被 try-catch 捕获的全局 JS 运行时错误
  // ============================================================
  window.onerror = (message, source, lineno, colno, error) => {
    // 格式化错误消息，包含发生位置
    const formattedMessage = `${message} (${source}:${lineno}:${colno})`

    // 提取堆栈信息
    const stack = error instanceof Error
      ? error.stack
      : undefined

    console.error(`[JS Error] ${formattedMessage}`, stack)

    // 存储错误日志
    const entry = buildErrorEntry('js', formattedMessage, stack)
    saveErrorLog(entry)

    // 提示用户
    notifyUser()

    // 返回 true 可阻止浏览器默认的错误处理（如控制台报错弹窗）
    // 这里返回 false 保留浏览器默认行为，便于开发调试
    return false
  }

  // ============================================================
  // 3. 未处理 Promise 异常捕获
  // 捕获 Promise 中未被 .catch() 处理的 rejection
  // ============================================================
  window.onunhandledrejection = (event) => {
    const reason = event.reason

    // 提取错误消息
    const message = reason instanceof Error
      ? reason.message
      : String(reason)

    // 提取堆栈信息
    const stack = reason instanceof Error
      ? reason.stack
      : undefined

    console.error(`[Promise Rejection] ${message}`, stack)

    // 存储错误日志
    const entry = buildErrorEntry('promise', message, stack)
    saveErrorLog(entry)

    // 提示用户
    notifyUser()

    // 调用 preventDefault 可阻止浏览器默认的 unhandledrejection 警告
    // 这里不阻止，保留浏览器默认行为便于开发时发现问题
    // event.preventDefault()
  }
}

/**
 * 上报错误到后端（预留接口，当前默认不调用）
 * 后续可通过配置文件或环境变量开启后端上报
 *
 * @param {Object} errorEntry - 错误条目对象
 * @param {string} errorEntry.timestamp - 时间戳
 * @param {string} errorEntry.type - 错误类型
 * @param {string} errorEntry.message - 错误消息
 * @param {string} [errorEntry.stack] - 错误堆栈
 * @param {string} errorEntry.url - 页面 URL
 */
export function reportToServer(errorEntry) {
  // TODO: 后续可通过配置开启后端上报
  // 示例：
  // fetch('/api/error-report', {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify(errorEntry)
  // }).catch(() => { /* 上报失败不影响主流程 */ })
}