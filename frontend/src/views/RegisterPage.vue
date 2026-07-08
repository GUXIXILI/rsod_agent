<template>
  <div class="register-page">
    <!-- 注册卡片容器 -->
    <div class="register-card">
      <!-- Logo 区域 -->
      <div class="logo-area">
        <div class="logo-icon">
          <span class="logo-text">RS</span>
        </div>
        <h2 class="logo-title">RSOD Agent Platform</h2>
        <p class="logo-subtitle">创建新账号，开启智能之旅</p>
      </div>

      <!-- 注册表单 -->
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        class="register-form"
        @submit.prevent
      >
        <!-- 用户名输入框 -->
        <el-form-item prop="username">
          <el-input
            v-model="formData.username"
            placeholder="请输入用户名"
            :prefix-icon="User"
            size="large"
          />
        </el-form-item>

        <!-- 邮箱输入框 -->
        <el-form-item prop="email">
          <el-input
            v-model="formData.email"
            placeholder="请输入邮箱地址"
            :prefix-icon="Message"
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
            show-password
          />
        </el-form-item>

        <!-- 确认密码输入框 -->
        <el-form-item prop="confirmPassword">
          <el-input
            v-model="formData.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            :prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>

        <!-- 注册错误提示（由后端返回的业务错误，如用户名已存在等） -->
        <el-form-item v-if="registerError" class="error-message-item">
          <div class="register-error-message">
            <el-icon><Warning /></el-icon>
            <span>{{ registerErrorMsg }}</span>
          </div>
        </el-form-item>

        <!-- 注册按钮 -->
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="submit-btn"
            @click="handleRegister"
          >
            {{ loading ? '注册中...' : '注 册' }}
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 底部登录链接 -->
      <div class="bottom-link">
        <span class="link-text">已有账号？</span>
        <router-link to="/login" class="link-action">返回登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Message, Warning } from '@element-plus/icons-vue'
import { registerApi } from '@/api/auth'

const router = useRouter()

// 表单引用
const formRef = ref(null)

// 加载状态
const loading = ref(false)

// 注册错误提示状态
// 与登录页保持一致，采用页面内静态提示而非 ElMessage，避免消息弹窗未渲染导致用户无感知
const registerError = ref(false)
const registerErrorMsg = ref('')

// 表单数据
const formData = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

/**
 * 自定义校验：确认密码与密码一致
 */
const validateConfirmPassword = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('请再次输入密码'))
  } else if (value !== formData.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

// 表单验证规则
const formRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在 3 到 50 个字符之间', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入合法的邮箱地址', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 30, message: '密码长度在 6 到 30 个字符之间', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

/**
 * 处理注册提交
 */
const handleRegister = async () => {
  // 每次提交前清空之前的后端错误提示
  registerError.value = false
  registerErrorMsg.value = ''

  // 表单校验
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    // 调用注册 API
    await registerApi({
      username: formData.username,
      email: formData.email,
      password: formData.password
    })

    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (error) {
    // 认证页面（/register）被 request.js 的响应拦截器排除在全局 ElMessage 之外，
    // 因此页面层需要主动提取并展示错误信息，避免用户对失败状态无感知。
    // 使用与登录页一致的页面内静态提示，比 ElMessage 更可靠，且不会泄露内部细节。
    const response = error?.response
    if (response?.data) {
      const detail = response.data?.detail || response.data?.message
      registerErrorMsg.value = detail || '注册失败，请稍后重试'
    } else {
      registerErrorMsg.value = '网络异常，请检查网络连接后重试'
    }
    registerError.value = true
    console.error('注册失败:', error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
// 全屏渐变色背景（与登录页一致）
.register-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, $primary-dark, $primary-light);
}

// 居中白色卡片
.register-card {
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

// 注册表单
.register-form {
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

  // 注册错误提示样式（与登录页保持一致）
  .register-error-message {
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