import request from '@/utils/request'

/**
 * 用户注册
 * @param {Object} data - 注册信息 { username, email, password }
 * @returns {Promise} 注册响应
 */
export function registerApi(data) {
  return request.post('/auth/register', data)
}

/**
 * 用户登录
 * 后端 /api/auth/login 使用 Pydantic BaseModel 接收 JSON 格式数据
 * @param {Object} data - 登录信息 { username, password }
 * @returns {Promise} 登录响应，包含 access_token 和 refresh_token
 */
export function loginApi(data) {
  return request.post('/auth/login', data, {
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

/**
 * 获取当前用户信息
 * @returns {Promise} 用户信息响应
 */
export function getUserInfoApi() {
  return request.get('/auth/me')
}

/**
 * 忘记密码 - 发送重置邮件
 * @param {Object} data - { email }
 * @returns {Promise}
 */
export function forgotPasswordApi(data) {
  return request.post('/auth/forgot-password', data)
}

/**
 * 获取用户个人信息
 * @returns {Promise} 用户信息响应
 */
export function getProfileApi() {
  return request.get('/user/profile')
}

/**
 * 修改密码
 * @param {Object} data - { old_password, new_password }
 * @returns {Promise}
 */
export function changePasswordApi(data) {
  return request.put('/user/password', data)
}