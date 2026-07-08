/**
 * Vite 构建工具配置
 * - 配置前端开发服务器、路径别名、CSS 预处理器、API 代理
 * - 配置 Vitest 测试框架
 */
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],

  // 路径别名：@ 指向 src 目录
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },

  // CSS 预处理器配置
  css: {
    preprocessorOptions: {
      scss: {
        // 全局注入 SCSS 变量文件，所有组件可直接使用变量
        additionalData: `@use "@/assets/styles/variables.scss" as *;`,
      },
    },
  },

  // 开发服务器配置
  server: {
    port: 5173,
    open: false,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },

  // Vitest 测试配置
  test: {
    // 测试环境：使用 happy-dom 模拟浏览器 DOM
    environment: 'happy-dom',
    // 测试前执行的 setup 文件
    setupFiles: ['./tests/setup.js'],
    // 测试文件匹配模式
    include: ['tests/**/*.test.js'],
  },
})