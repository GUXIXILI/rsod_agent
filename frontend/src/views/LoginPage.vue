<template>
  <div class="login-page">
    <div class="hero-section">
      <div class="hero-content">
        <div class="fire-wrapper" :style="{ width: 200 + 'px', height: 140 + 'px' }">
          <svg 
            viewBox="0 0 500 500" 
            width="100%" 
            height="100%" 
            xmlns="http://www.w3.org/2000/svg"
          >
            <ellipse cx="250" cy="460" rx="110" ry="8" fill="#E0E0E0" />
            <path 
              d="M260,30 C260,30 330,120 310,180 C360,200 400,260 370,330 C330,420 170,430 130,340 C100,270 140,210 170,180 C150,140 180,90 200,100 C220,110 210,60 260,30 Z" 
              fill="#DE4444" 
            />
            <path 
              d="M255,140 C255,140 290,200 280,240 C320,260 340,310 310,360 C280,410 190,410 170,360 C150,310 190,260 210,240 C200,210 220,170 240,180 C250,185 245,160 255,140 Z" 
              fill="#FF873D" 
            />
            <path 
              d="M250,240 C250,240 270,280 265,310 C290,320 295,350 275,380 C250,410 200,410 195,370 C190,330 215,300 225,290 C220,270 235,260 250,240 Z" 
              fill="#FFD053" 
            />
          </svg>
        </div>

        <h1 class="hero-title">火灾烟雾智能检测系统</h1>
        <p class="hero-subtitle">基于深度学习的实时火灾烟雾检测平台</p>

        <div class="hero-features">
          <h3 class="features-title">核心功能</h3>
          <ul class="features-list">
            <li> 1. 多格式上传：支持图片、视频和ZIP压缩包</li>
            <li> 2. 实时摄像头检测：无需延迟</li>
            <li> 3. AI智能助手：支持自然语言对话</li>
            <li> 4. 自定义模型：加载自有YOLO权重文件</li>
            <li> 5. 完整操作历史与数据统计</li>
          </ul>
        </div>
      </div>
    </div>

    <div class="login-card">
      <div class="logo-area">
        <div class="logo-icon">
          <span class="logo-text">FS</span>
        </div>
        <h2 class="logo-title">欢迎</h2>
        <p class="logo-subtitle">火灾烟雾智能检测系统</p>
      </div>

      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        class="login-form"
        @submit.prevent
      >
        <el-form-item prop="username">
          <el-input
            v-model="formData.username"
            placeholder="请输入用户名或邮箱"
            :prefix-icon="User"
            size="large"
            class="custom-input"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="formData.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            size="large"
            class="custom-input"
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item v-if="loginError" class="error-message-item">
          <div class="login-error-message">
            <el-icon><Warning /></el-icon>
            <span>用户名或密码错误</span>
          </div>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="submit-btn"
            @click="handleLogin"
          >
            {{ loading ? '登录中...' : '登录' }}
          </el-button>
        </el-form-item>
      </el-form>

      <div class="forgot-password-link">
        <router-link to="/forgot-password" class="link-action">忘记密码？</router-link>
      </div>

      <div class="bottom-link">
        <span class="link-text">没有账号？</span>
        <router-link to="/register" class="link-action">注册</router-link>
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

const formRef = ref(null)
const loading = ref(false)
const loginError = ref(false)

const formData = reactive({
  username: '',
  password: ''
})

const formRules = {
  username: [
    { required: true, message: '请输入用户名或邮箱', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ]
}

const handleLogin = async (event) => {
  if (event && typeof event.preventDefault === 'function') {
    event.preventDefault()
  }

  loginError.value = false

  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await userStore.login({ ...formData })
    ElMessage.success('登录成功')

    const redirectPath = route.query.redirect || '/chat'
    router.push(redirectPath)
  } catch (error) {
    loginError.value = true
    console.error('Login failed:', error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
.login-page {
  display: flex;
  align-items: stretch;
  min-height: 100vh;
  margin: 0;
  padding: 0;
}

.hero-section {
  width: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  /* Припыленный дымчатый градиент по указанным цветам */
  background: linear-gradient(135deg, #4A90D9, #87CEEB);
  color: #ffffff;
  padding: 30px 30px;
  position: relative;

  .hero-content {
    max-width: 700px;
    text-align: center;
    z-index: 1;

    .fire-wrapper {
      display: inline-block;
      vertical-align: middle;
      animation: flicker 3s ease-in-out infinite alternate;
      margin-bottom: 32px;
      filter: drop-shadow(0 4px 12px rgba(0, 0, 0, 0.25));
    }

    .hero-title {
      font-size: 32px;
      font-weight: 700;
      margin: 0 0 10px;
      line-height: 1.3;
      text-shadow: 0 3px 10px rgba(0, 0, 0, 0.35);
    }

    .hero-subtitle {
      font-size: 18px;
      margin: 0 0 20px;
      opacity: 0.95;
      text-shadow: 0 3px 8px rgba(0, 0, 0, 0.3);
    }

    .features-title {
      font-size: 18px;
      margin: 0 0 12px;
      text-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
    }

    .features-list {
      list-style: none;
      padding: 0;
      margin: 0;
      text-align: left;

      li {
        padding: 8px 0;
        font-size: 14px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.25);
        display: flex;
        align-items: center;
        text-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);

        &:last-child {
          border-bottom: none;
        }
      }
    }
  }
}

.login-card {
  width: 50%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 30px 35px;
  background-color: #fff;
  box-shadow: -6px 0 24px rgba(0, 0, 0, 0.08);
  position: relative;

  .logo-area {
    text-align: center;
    margin-bottom: 20px;

    .logo-icon {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 56px;
      height: 56px;
      margin-bottom: 12px;
      background: linear-gradient(135deg, #4A90D9, #87CEEB);
      border-radius: 18px;

      .logo-text {
        font-size: 26px;
        font-weight: 700;
        color: #fff;
        letter-spacing: 2px;
      }
    }

    .logo-title {
      margin: 0 0 4px;
      font-size: 22px;
      font-weight: 600;
      color: #2C3E50;
    }

    .logo-subtitle {
      margin: 0;
      font-size: 14px;
      color: #5A6C7D;
    }
  }

  .login-form {
    :deep(.custom-input .el-input__inner) {
      height: 44px;
      font-size: 16px;
    }

    .submit-btn {
      width: 100%;
      height: 44px;
      background: linear-gradient(135deg, #4A90D9, #87CEEB);
      border: none;
      font-size: 18px;
      border-radius: 8px;
      color: #fff;

      &:hover {
        opacity: 0.92;
      }
    }

    .error-message-item {
      margin-bottom: 12px;

      :deep(.el-form-item__content) {
        line-height: 1.5;
      }
    }

    .login-error-message {
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
  }

  .forgot-password-link {
    text-align: right;
    margin: 8px 0;
    font-size: 16px;

    .link-action {
      color: #4A90D9;
      text-decoration: none;

      &:hover {
        text-decoration: underline;
      }
    }
  }

  .bottom-link {
    text-align: center;
    margin-top: 12px;
    font-size: 16px;

    .link-text {
      color: #5A6C7D;
    }

    .link-action {
      color: #4A90D9;
      text-decoration: none;
      margin-left: 6px;

      &:hover {
        text-decoration: underline;
      }
    }
  }
}

@keyframes flicker {
  0% { transform: scale(1); }
  100% { transform: scale(1.02); }
}
</style>