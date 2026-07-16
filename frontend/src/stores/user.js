import { defineStore } from 'pinia'
import { loginApi, registerApi, getUserInfoApi } from '@/api/auth'

/**
 * 用户状态管理 Store
 * 管理用户认证状态、token 和用户信息
 */
export const useUserStore = defineStore('user', {
  state: () => ({
    /** 访问令牌 */
    token: localStorage.getItem('rsod_token') || '',
    /** 刷新令牌 */
    refreshToken: localStorage.getItem('rsod_refresh_token') || '',
    /** 用户信息对象 */
    user: (() => {
      try {
        return JSON.parse(localStorage.getItem('user')) || {}
      } catch {
        return {}
      }
    })()
  }),

  getters: {
    /**
     * 是否已登录
     * @returns {boolean}
     */
    isLoggedIn: (state) => !!state.token,

    /**
     * 当前用户名
     * @returns {string}
     */
    username: (state) => state.user.username || '',

    /**
     * 用户头像地址
     * @returns {string}
     */
    avatar: (state) => state.user.avatar || ''
  },

  actions: {
    /**
     * 用户登录
     * 调用登录接口，成功后保存 token 和用户信息到 state 和 localStorage
     * @param {Object} credentials - 登录凭据 { username, password }
     */
    async login(credentials) {
      const res = await loginApi(credentials)
      const { access_token, refresh_token, user } = res

      // 保存到 state
      this.token = access_token
      this.refreshToken = refresh_token
      this.user = user || {}

      // 持久化到 localStorage
      localStorage.setItem('rsod_token', access_token)
      localStorage.setItem('rsod_refresh_token', refresh_token || '')
      localStorage.setItem('user', JSON.stringify(user || {}))
    },

    /**
     * 用户登出
     * 清除 state 和 localStorage 中的认证信息
     */
    logout() {
      // 清除 state
      this.token = ''
      this.refreshToken = ''
      this.user = {}

      // 清除 localStorage
      localStorage.removeItem('rsod_token')
      localStorage.removeItem('rsod_refresh_token')
      localStorage.removeItem('user')
    },

    /**
     * 获取当前用户信息
     * 调用接口更新 user 信息，同时更新 localStorage
     */
    async fetchUserInfo() {
      const data = await getUserInfoApi()
      this.user = data
      localStorage.setItem('user', JSON.stringify(data))
    }
  }
})