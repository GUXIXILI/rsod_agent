<template>
  <div class="register-page">
    <div class="register-card">
      <div class="logo-area">
        <div class="logo-icon">
          <span class="logo-text">FS</span>
        </div>
        <h2 class="logo-title">Fire & Smoke Detection Platform</h2>
        <p class="logo-subtitle">创建新账号，开启智能之旅</p>
      </div>

      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        class="register-form"
        @submit.prevent
      >
        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item prop="username">
              <el-input
                v-model="formData.username"
                placeholder="请输入用户名"
                :prefix-icon="User"
                size="large"
                class="custom-input"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item prop="email">
              <el-input
                v-model="formData.email"
                placeholder="请输入邮箱地址"
                :prefix-icon="Message"
                size="large"
                class="custom-input"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item prop="password">
              <el-input
                v-model="formData.password"
                type="password"
                placeholder="请输入密码"
                :prefix-icon="Lock"
                size="large"
                show-password
                class="custom-input"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item prop="confirmPassword">
              <el-input
                v-model="formData.confirmPassword"
                type="password"
                placeholder="请再次输入密码"
                :prefix-icon="Lock"
                size="large"
                show-password
                class="custom-input"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item v-if="registerError" class="error-message-item">
          <div class="register-error-message">
            <el-icon><Warning /></el-icon>
            <span>{{ registerErrorMsg }}</span>
          </div>
        </el-form-item>

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
const formRef = ref(null)
const loading = ref(false)
const registerError = ref(false)
const registerErrorMsg = ref('')

const formData = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('请再次输入密码'))
  } else if (value !== formData.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

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

const handleRegister = async () => {
  registerError.value = false
  registerErrorMsg.value = ''

  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await registerApi({
      username: formData.username,
      email: formData.email,
      password: formData.password
    })

    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (error) {
    const response = error?.response
    if (response?.data) {
      const detail = response.data?.detail || response.data?.message
      registerErrorMsg.value = detail || '注册失败，请稍后重试'
    } else {
      registerErrorMsg.value = '网络异常，请检查网络连接后重试'
    }
    registerError.value = true
    console.error('Register failed:', error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
.register-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #5B9BD5, #A8D8EA);
  padding: 20px;
}

.register-card {
  width: 720px;
  padding: 50px 40px;
  background-color: #fff;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
}

.logo-area {
  text-align: center;
  margin-bottom: 40px;

  .logo-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 76px;
    height: 76px;
    margin-bottom: 20px;
    background: linear-gradient(135deg, #5B9BD5, #A8D8EA);
    border-radius: 18px;

    .logo-text {
      font-size: 34px;
      font-weight: 700;
      color: #fff;
      letter-spacing: 2px;
    }
  }

  .logo-title {
    margin: 0 0 10px;
    font-size: 28px;
    font-weight: 600;
    color: #333;
  }

  .logo-subtitle {
    margin: 0;
    font-size: 18px;
    color: #666;
  }
}

.register-form {
  :deep(.custom-input .el-input__inner) {
    height: 54px;
    font-size: 16px;
  }

  .error-message-item {
    margin-bottom: 12px;

    :deep(.el-form-item__content) {
      line-height: 1.5;
    }
  }

  .register-error-message {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    padding: 12px 14px;
    color: #f44336;
    font-size: 16px;
    background-color: rgba(244, 67, 54, 0.08);
    border: 1px solid rgba(244, 67, 54, 0.2);
    border-radius: 8px;

    .el-icon {
      margin-right: 6px;
      font-size: 18px;
    }
  }

  .submit-btn {
    width: 100%;
    height: 54px;
    background: linear-gradient(135deg, #5B9BD5, #A8D8EA);
    border: none;
    font-size: 18px;
    border-radius: 8px;
    color: #fff;

    &:hover {
      opacity: 0.92;
    }
  }
}

.bottom-link {
  text-align: center;
  margin-top: 24px;
  font-size: 16px;

  .link-text {
    color: #666;
  }

  .link-action {
    color: #5B9BD5;
    text-decoration: none;
    margin-left: 6px;

    &:hover {
      text-decoration: underline;
    }
  }
}
</style>