<template>
  <div class="login-page">
    <div class="hero-section">
      <div class="hero-content">
        <div class="fire-wrapper" :style="{ width: 200 + 'px', height: 200 + 'px' }">
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

        <h1 class="hero-title">Fire & Smoke Detection Platform</h1>
        <p class="hero-subtitle">火灾烟雾智能检测系统</p>

        <div class="hero-features">
          <h3 class="features-title">✨ Core Features</h3>
          <ul class="features-list">
            <li> 1.  Multi-format upload: images, videos and ZIP archives</li>
            <li> 2.  Real-time detection via web camera without delay</li>
            <li> 3.  AI assistant: support natural language interaction</li>
            <li> 4.  Custom model: load your own YOLO .pt files</li>
            <li> 5. Complete operation history & data statistics</li>
          </ul>
        </div>
      </div>
    </div>

    <div class="login-card">
      <div class="logo-area">
        <div class="logo-icon">
          <span class="logo-text">FS</span>
        </div>
        <h2 class="logo-title">Welcome</h2>
        <p class="logo-subtitle">Fire & Smoke Detection Platform</p>
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
            placeholder="Please enter username or email"
            :prefix-icon="User"
            size="large"
            class="custom-input"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="formData.password"
            type="password"
            placeholder="Please enter password"
            :prefix-icon="Lock"
            size="large"
            class="custom-input"
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item v-if="loginError" class="error-message-item">
          <div class="login-error-message">
            <el-icon><Warning /></el-icon>
            <span>Wrong username or password</span>
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
            {{ loading ? 'Logging in...' : 'Login' }}
          </el-button>
        </el-form-item>
      </el-form>

      <div class="forgot-password-link">
        <router-link to="/forgot-password" class="link-action">Forgot password?</router-link>
      </div>

      <div class="bottom-link">
        <span class="link-text">Don't have an account?</span>
        <router-link to="/register" class="link-action">Sign up</router-link>
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
    { required: true, message: 'Please enter username or email', trigger: 'blur' }
  ],
  password: [
    { required: true, message: 'Please enter password', trigger: 'blur' },
    { min: 6, message: 'Password must be at least 6 characters', trigger: 'blur' }
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
    ElMessage.success('Login successful')

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
  width: 60%;
  display: flex;
  align-items: center;
  justify-content: center;
  /* Припыленный дымчатый градиент по указанным цветам */
  background: linear-gradient(135deg, #a9a6a2, #dcc9b7);
  color: #ffffff;
  padding: 60px 50px;
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
      font-size: 48px;
      font-weight: 700;
      margin: 0 0 18px;
      line-height: 1.3;
      text-shadow: 0 3px 10px rgba(0, 0, 0, 0.35);
    }

    .hero-subtitle {
      font-size: 26px;
      margin: 0 0 55px;
      opacity: 0.95;
      text-shadow: 0 3px 8px rgba(0, 0, 0, 0.3);
    }

    .features-title {
      font-size: 28px;
      margin: 0 0 24px;
      text-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
    }

    .features-list {
      list-style: none;
      padding: 0;
      margin: 0;
      text-align: left;

      li {
        padding: 16px 0;
        font-size: 20px;
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
  width: 40%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 50px 45px;
  background-color: #fff;
  box-shadow: -6px 0 24px rgba(0, 0, 0, 0.08);
  position: relative;

  .logo-area {
    text-align: center;
    margin-bottom: 45px;

    .logo-icon {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 76px;
      height: 76px;
      margin-bottom: 22px;
      background: linear-gradient(135deg, #a9a6a2, #dcc9b7);
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
      font-size: 17px;
      color: #666;
    }
  }

  .login-form {
    :deep(.custom-input .el-input__inner) {
      height: 54px;
      font-size: 16px;
    }

    .submit-btn {
      width: 100%;
      height: 54px;
      background: linear-gradient(135deg, #a9a6a2, #dcc9b7);
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
    margin: 14px 0;
    font-size: 16px;

    .link-action {
      color: #a9a6a2;
      text-decoration: none;

      &:hover {
        text-decoration: underline;
      }
    }
  }

  .bottom-link {
    text-align: center;
    margin-top: 22px;
    font-size: 16px;

    .link-text {
      color: #666;
    }

    .link-action {
      color: #a9a6a2;
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