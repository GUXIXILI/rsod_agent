<template>
  <div class="login-page">
    <!-- 登录卡片容器 -->
    <div class="login-card">
      <!-- Logo 区域 -->
      <div class="logo-area">
        <div class="logo-icon">
          <span class="logo-text">RS</span>
        </div>
        <h2 class="logo-title">RSOD Agent Platform</h2>
        <p class="logo-subtitle">欢迎回来，请登录您的账号</p>
      </div>

      <!-- 登录表单 -->
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        class="login-form"
        @submit.prevent
      >
        <!-- 用户名/邮箱输入框（支持用户名或邮箱登录） -->
        <el-form-item prop="username">
          <el-input
            v-model="formData.username"
            placeholder="请输入用户名或邮箱"
            :prefix-icon="User"
            size="large"
          />
        </el-form-item>

        <!-- 密码输入框 -->
        <el-form-item prop="password">
          <el-input
            v-model="formData.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            size="large"
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <!-- 登录错误提示（不区分账号或密码错误，保护隐私） -->
        <el-form-item v-if="loginError" class="error-message-item">
          <div class="login-error-message">
            <el-icon><Warning /></el-icon>
            <span>账号或密码错误</span>
          </div>
        </el-form-item>

        <!-- 登录按钮 -->
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="submit-btn"
            @click="handleLogin"
          >
            {{ loading ? '登录中...' : '登 录' }}
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 底部注册链接 -->
      <div class="bottom-link">
        <span class="link-text">还没有账号？</span>
        <router-link to="/register" class="link-action">立即注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Warning } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// 表单引用
const formRef = ref(null)

// 加载状态
const loading = ref(false)

// 登录错误提示状态
const loginError = ref(false)

// 表单数据
const formData = reactive({
  username: '',
  password: ''
})

// 表单验证规则
const formRules = {
  username: [
    { required: true, message: '请输入用户名或邮箱', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少为 6 个字符', trigger: 'blur' }
  ]
}

/**
 * 处理登录提交
 * @param {Event} event - 可选的事件对象，用于阻止默认表单提交
 */
const handleLogin = async (event) => {
  // 阻止默认表单提交行为，防止页面刷新
  if (event && typeof event.preventDefault === 'function') {
    event.preventDefault()
  }

  // 清除之前的错误提示
  loginError.value = false

  // 表单校验
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    // 调用 userStore 的 login 方法
    await userStore.login({ ...formData })

    ElMessage.success('登录成功')

    // 优先跳转 redirect 参数，否则默认跳转 /chat
    const redirectPath = route.query.redirect || '/chat'
    router.push(redirectPath)
  } catch (error) {
    // 显示账号或密码错误提示（不区分具体是账号还是密码错误）
    loginError.value = true
    console.error('登录失败:', error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
// 全屏渐变色背景
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, $primary-dark, $primary-light);
}

// 居中白色卡片
.login-card {
  width: 400px;
  padding: 40px;
  background-color: #fff;
  border-radius: $border-radius-lg;
  box-shadow: $box-shadow-base;
}

// Logo 区域
.logo-area {
  text-align: center;
  margin-bottom: 32px;

  .logo-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 64px;
    height: 64px;
    margin-bottom: 16px;
    background: linear-gradient(135deg, $primary-dark, $primary-light);
    border-radius: 16px;

    .logo-text {
      font-size: 28px;
      font-weight: 700;
      color: #fff;
      letter-spacing: 2px;
    }
  }

  .logo-title {
    margin: 0 0 8px;
    font-size: 22px;
    font-weight: 600;
    color: $text-primary;
  }

  .logo-subtitle {
    margin: 0;
    font-size: 14px;
    color: $text-secondary;
  }
}

// 登录表单
.login-form {
  .submit-btn {
    width: 100%;
  }

  // 错误提示项：去除默认下边距，避免额外间距
  .error-message-item {
    margin-bottom: 8px;

    :deep(.el-form-item__content) {
      line-height: 1.5;
    }
  }

  // 登录错误提示样式
  .login-error-message {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    padding: 8px 12px;
    color: $danger-color;
    font-size: 14px;
    background-color: rgba($danger-color, 0.08);
    border: 1px solid rgba($danger-color, 0.2);
    border-radius: $border-radius-md;

    .el-icon {
      margin-right: 6px;
      font-size: 16px;
    }
  }
}

// 底部链接
.bottom-link {
  text-align: center;
  margin-top: 16px;
  font-size: 14px;

  .link-text {
    color: $text-secondary;
  }

  .link-action {
    color: $primary-color;
    text-decoration: none;
    margin-left: 4px;

    &:hover {
      text-decoration: underline;
    }
  }
}
</style>