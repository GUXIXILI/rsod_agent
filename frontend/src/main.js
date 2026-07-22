/**
 * 应用入口文件
 * 注册核心插件：Pinia（状态管理）、Router（路由）、Element Plus（UI组件库）
 * 引入全局样式
 */
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
// Element Plus 中文语言包
import zhCn from 'element-plus/es/locale/lang/zh-cn'

import App from './App.vue'
import pinia from './stores'
import router from './router'
import { setupErrorReporting } from './utils/errorReporter'

// 全局样式
import './assets/styles/global.scss'

const app = createApp(App)

// 注册 Element Plus 组件库，使用中文语言包
app.use(ElementPlus, { locale: zhCn })

// 注册 Pinia 状态管理
app.use(pinia)

// 注册 Vue Router 路由
app.use(router)

// 初始化全局错误监控（Vue 组件错误、JS 运行时错误、未处理 Promise 异常）
setupErrorReporting(app)

app.mount('#app')