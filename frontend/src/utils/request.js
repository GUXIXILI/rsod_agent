import axios from 'axios'
import { ElMessage } from 'element-plus'

/**
 * 创建 axios 实例，配置基础 URL 和超时时间
 */
const request = axios.create({
  baseURL: '/api',
  timeout: 30000
})

/**
 * 判断当前是否处于登录或注册页面
 * 认证页面的错误提示由页面自身统一处理，避免全局 ElMessage 与页面内提示冲突
 * @returns {boolean}
 */
const isAuthPage = () => {
  const pathname = window.location.pathname
  return pathname === '/login' || pathname === '/register'
}

/**
 * 请求拦截器：从 localStorage 读取 token 并注入到请求头
 * 直接从 localStorage 读取，避免与 user store 产生循环依赖
 */
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('rsod_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

/**
 * 响应拦截器：统一处理错误状态码，使用 Element Plus 提示
 * 登录/注册页的错误由页面自身控制，避免暴露具体错误类型（如服务器错误）
 */
request.interceptors.response.use(
  (response) => {
    // 返回响应数据，调用层无需再访问 .data
    return response.data
  },
  async (error) => {
    // 网络错误（无 response 对象）
    if (!error.response) {
      // 认证页面由页面层统一给出"账号或密码错误"等隐私友好的提示
      if (!isAuthPage()) {
        ElMessage.error('网络连接异常，请检查后端服务是否启动')
      }
      return Promise.reject(error)
    }

    const { status, config } = error.response

    // ── 401 静默重试：解决登录后 token 尚未注入的竞态条件 ──
    // 场景：页面初始化时 fetchSessions 先于 token 写入 localStorage 发出请求
    // 重试时请求拦截器会重新从 localStorage 读取 token，此时 token 通常已就绪
    if (status === 401 && !config._retried && !isAuthPage()) {
      config._retried = true
      // 短暂延迟，等待 token 写入完成
      await new Promise(resolve => setTimeout(resolve, 300))
      try {
        return await request(config)
      } catch (retryError) {
        // 重试仍失败，回落使用 retryError 继续走后续错误处理流程
        error = retryError
        // 重试失败后不再重复触发 ElMessage，直接 reject
        return Promise.reject(error)
      }
    }

    switch (status) {
      case 401:
        // 在登录页触发的 401（如用户名或密码错误），不应再次跳转登录页，避免页面刷新
        // 错误提示完全交给 LoginPage.vue 控制，不暴露具体错误类型
        if (!isAuthPage()) {
          // 登录已过期，清除本地存储并跳转登录页
          ElMessage.error('登录已过期，请重新登录')
          localStorage.removeItem('rsod_token')
localStorage.removeItem('rsod_refresh_token')
          localStorage.removeItem('user')
          window.location.href = '/login'
        }
        break
      case 403:
        if (!isAuthPage()) {
          ElMessage.error('没有权限执行此操作')
        }
        break
      case 404:
        if (!isAuthPage()) {
          ElMessage.error('请求的资源不存在')
        }
        break
      case 422:
        if (!isAuthPage()) {
          ElMessage.error('参数验证失败')
        }
        break
      case 500:
        if (!isAuthPage()) {
          ElMessage.error('服务器内部错误')
        }
        break
      case 400:
      case 429:
      default:
        // 后端返回的具体错误信息通常位于 error.response.data.detail
        // 兜底显示通用错误提示
        if (!isAuthPage()) {
          const detail = error.response.data?.detail || error.response.data?.message
          if (detail) {
            ElMessage.error(detail)
          } else {
            ElMessage.error(`请求失败，状态码：${status}`)
          }
        }
        break
    }

    return Promise.reject(error)
  }
)

export default request