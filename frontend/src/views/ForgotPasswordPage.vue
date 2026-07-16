<template>
  <div class="forgot-password-page">
    <div class="forgot-password-card">
      <!-- Logo 区域 -->
      <div class="logo-area">
        <div class="logo-icon">
          <span class="logo-text">FS</span>
        </div>
        <h2 class="logo-title">Fire & Smoke Detection Platform</h2>
        <p class="logo-subtitle">密码重置</p>
      </div>

      <!-- 忘记密码表单 -->
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        class="forgot-form"
        @submit.prevent
      >
        <el-form-item prop="email">
          <el-input
            v-model="formData.email"
            placeholder="请输入注册邮箱"
            :prefix-icon="Message"
            size="large"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="submit-btn"
            @click="handleSubmit"
          >
            {{ loading ? '发送中...' : '发送重置邮件' }}
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 返回登录 -->
      <div class="bottom-link">
        <router-link to="/login" class="link-action">返回登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Message } from '@element-plus/icons-vue'
import { forgotPasswordApi } from '@/api/auth'

const formRef = ref(null)
const loading = ref(false)

const formData = reactive({
  email: ''
})

const formRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ]
}

const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await forgotPasswordApi({ email: formData.email })
    ElMessage.success('重置邮件已发送，请查收邮箱')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '发送失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
.forgot-password-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, $primary-dark, $primary-light);
}

.forgot-password-card {
  width: 400px;
  padding: 40px;
  background-color: #fff;
  border-radius: $border-radius-lg;
  box-shadow: $box-shadow-base;
}

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

.forgot-form {
  .submit-btn {
    width: 100%;
  }
}

.bottom-link {
  text-align: center;
  font-size: 14px;

  .link-action {
    color: $primary-color;
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }
}
</style>