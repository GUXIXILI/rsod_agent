/**
 * Vue Router 路由配置模块
 *
 * 功能说明：
 * - 定义应用所有路由规则，包含公开路由（登录/注册）与认证路由（主布局子路由）
 * - 全局前置守卫实现登录状态校验与页面重定向
 * - 通过 localStorage 直接读取 token 判断登录状态，避免与 Pinia store 产生循环依赖
 * - 每次路由切换自动更新 document.title
 *
 * @module router
 */

import { createRouter, createWebHistory } from 'vue-router'

// ==================== 路由表 ====================

const routes = [
  // ---- 公开路由：无需登录即可访问 ----
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginPage.vue'),
    meta: { title: '登录', requiresAuth: false },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/RegisterPage.vue'),
    meta: { title: '注册', requiresAuth: false },
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('@/views/ForgotPasswordPage.vue'),
    meta: { title: '忘记密码', requiresAuth: false },
  },

  // ---- 认证路由：需登录后访问，包裹在 MainLayout 中 ----
  {
    path: '/',
    component: () => import('@/components/layout/MainLayout.vue'),
    redirect: '/chat',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'camera-detection',
        name: 'CameraDetection',
        component: () => import('@/views/CameraDetectionPage.vue'),
        meta: { title: '摄像头检测' },
      },
      {
        path: 'chat',
        name: 'Chat',
        component: () => import('@/views/ChatPage.vue'),
        meta: { title: '智能对话' },
      },
      {
        path: 'training',
        name: 'Training',
        component: () => import('@/views/TrainingPage.vue'),
        meta: { title: '模型训练' },
      },
      {
        path: 'history',
        name: 'History',
        component: () => import('@/views/HistoryPage.vue'),
        meta: { title: '历史记录' },
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/DashboardPage.vue'),
        meta: { title: '数据看板' },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/SettingsPage.vue'),
        meta: { title: '个人设置' },
      },
    ],
  },

  // ---- 404 通配路由：匹配所有未定义路径，重定向到登录页 ----
  {
    path: '/:pathMatch(.*)*',
    redirect: '/login',
  },
]

// ==================== 路由实例 ====================

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// ==================== 全局前置守卫 ====================

router.beforeEach(async (to, from, next) => {
  // 1. 设置页面标题
  document.title = to.meta.title
    ? `${to.meta.title} - Fire & Smoke Detection Platform`
    : 'Fire & Smoke Detection Platform'

  // 2. BUG-007: 登录后 token 写入 localStorage 存在时序延迟
  //    需要认证但 token 为空时，轮询等待 token 就绪（最多 2 秒）
  if (to.meta.requiresAuth !== false) {
    let token = localStorage.getItem('rsod_token')
    if (!token) {
      // 轮询等待 token 写入（最多 20 次 × 100ms = 2 秒）
      for (let i = 0; i < 20; i++) {
        await new Promise(resolve => setTimeout(resolve, 100))
        token = localStorage.getItem('rsod_token')
        if (token) break
      }
    }
    if (!token) {
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }
  }

  // 3. 从 localStorage 直接读取 token，避免在守卫中导入 Pinia store 导致循环依赖
  const token = localStorage.getItem('rsod_token')

  // 4. 已登录访问登录/注册页 → 跳转首页（会自动重定向到 /chat）
  if (token && (to.path === '/login' || to.path === '/register')) {
    next({ path: '/' })
    return
  }

  // 5. 放行
  next()
})

export default router