<!--
  根组件
  包含 router-view 和错误边界
  当子组件渲染出错时显示友好错误提示，避免空白页面
-->
<template>
  <div v-if="hasError" class="app-error">
    <div class="app-error__content">
      <div class="app-error__icon">!</div>
      <h2>页面加载失败</h2>
      <p>请刷新页面重试，或联系管理员</p>
      <button class="app-error__btn" @click="handleRetry">刷新页面</button>
    </div>
  </div>
  <router-view v-else />
</template>

<script setup>
import { onErrorCaptured, ref } from 'vue'

const hasError = ref(false)
const errorMessage = ref('')

/**
 * 错误边界钩子
 * 捕获子组件树中任何未被处理的渲染错误
 * 返回 false 阻止错误继续向上传播
 */
onErrorCaptured((err, instance, info) => {
  console.error('[App Error] 捕获到渲染错误:', err, info)
  hasError.value = true
  errorMessage.value = err instanceof Error ? err.message : String(err)
  // 返回 false 阻止错误继续传播
  return false
})

function handleRetry() {
  window.location.reload()
}
</script>

<style scoped>
.app-error {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background-color: #FFFAF5;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.app-error__content {
  text-align: center;
  padding: 40px;
}

.app-error__icon {
  width: 64px;
  height: 64px;
  line-height: 64px;
  border-radius: 50%;
  background: #FFF0F0;
  color: #E55555;
  font-size: 28px;
  font-weight: 700;
  margin: 0 auto 20px;
}

.app-error__content h2 {
  font-size: 20px;
  font-weight: 600;
  color: #2C3E50;
  margin: 0 0 8px;
}

.app-error__content p {
  font-size: 14px;
  color: #7F8C8D;
  margin: 0 0 24px;
}

.app-error__btn {
  display: inline-block;
  padding: 10px 28px;
  background: #4A90D9;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  cursor: pointer;
  transition: background 0.2s;
}

.app-error__btn:hover {
  background: #3A7BC8;
}
</style>