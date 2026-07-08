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

  // ---- 认证路由：需登录后访问，包裹在 MainLayout 中 ----
  {
    path: '/',
    component: () => import('@/components/layout/MainLayout.vue'),
    redirect: '/chat',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'chat',
        name: 'Chat',
        component: () => import('@/views/ChatPage.vue'),
        meta: { title: '智能对话' },
      },
      {
        path: 'detection',
        name: 'Detection',
        component: () => import('@/views/DetectionPage.vue'),
        meta: { title: '检测工作台' },
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

router.beforeEach((to, from, next) => {
  // 1. 设置页面标题
  document.title = to.meta.title
    ? `${to.meta.title} - RSOD Agent Platform`
    : 'RSOD Agent Platform'

  // 2. 从 localStorage 直接读取 token，避免在守卫中导入 Pinia store 导致循环依赖
  const token = localStorage.getItem('token')

  // 3. 未登录访问需要认证的页面 → 跳转登录页，携带 redirect 参数供登录后回跳
  if (to.meta.requiresAuth !== false && !token) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  // 4. 已登录访问登录/注册页 → 跳转首页（会自动重定向到 /chat）
  if (token && (to.path === '/login' || to.path === '/register')) {
    next({ path: '/' })
    return
  }

  // 5. 放行
  next()
})

export default router