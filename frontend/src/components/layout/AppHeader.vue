<template>
  <!-- 顶部导航栏 -->
  <header class="app-header">
    <!-- 左侧：Logo + 平台名称 -->
    <div class="app-header__brand">
      <div class="app-header__logo">
        <span class="app-header__logo-icon">RS</span>
      </div>
      <h1 class="app-header__title">火灾烟雾智能检测系统</h1>
    </div>

    <!-- 中部：全局横向导航菜单 -->
    <el-menu
      :default-active="activeMenu"
      :router="true"
      mode="horizontal"
      :ellipsis="false"
      class="app-header__nav"
    >
      <el-menu-item index="/chat">
        <el-icon><ChatDotRound /></el-icon>
        <span>智能对话</span>
      </el-menu-item>
      <el-menu-item index="/camera-detection">
        <el-icon><VideoCamera /></el-icon>
        <span>摄像头检测</span>
      </el-menu-item>
      <el-menu-item index="/training">
        <el-icon><Cpu /></el-icon>
        <span>模型训练</span>
      </el-menu-item>
      <el-menu-item index="/history">
        <el-icon><Clock /></el-icon>
        <span>历史记录</span>
      </el-menu-item>
      <el-menu-item index="/dashboard">
        <el-icon><DataAnalysis /></el-icon>
        <span>数据看板</span>
      </el-menu-item>
      <el-menu-item index="/settings">
        <el-icon><Setting /></el-icon>
        <span>个人设置</span>
      </el-menu-item>
    </el-menu>

    <!-- 右侧：用户下拉菜单 -->
    <div class="app-header__right">
      <el-dropdown trigger="click" @command="handleCommand">
        <span class="app-header__user">
          <el-avatar
            :size="36"
            class="app-header__avatar"
          >
            {{ (userStore.username || 'U').charAt(0).toUpperCase() }}
          </el-avatar>
          <span class="app-header__username">
            {{ userStore.username || '未登录' }}
          </span>
          <el-icon class="app-header__arrow">
            <ArrowDown />
          </el-icon>
        </span>

        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">
              <el-icon><User /></el-icon>
              个人中心
            </el-dropdown-item>
            <el-dropdown-item command="logout" divided>
              <el-icon><SwitchButton /></el-icon>
              退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowDown,
  ChatDotRound,
  Clock,
  Cpu,
  DataAnalysis,
  Setting,
  SwitchButton,
  User,
  VideoCamera
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const route = useRoute()
const router = useRouter()

const activeMenu = computed(() => route.path)

const handleCommand = async (command) => {
  if (command === 'profile') {
    ElMessage.info('个人中心功能开发中')
  } else if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      })
      await userStore.logout()
      router.push('/login')
    } catch {
      // 用户取消操作
    }
  }
}
</script>

<style lang="scss" scoped>
$color-main-dark: #5B9BD5;
$color-main-light: #A8D8EA;
$header-height: 70px;

.app-header {
  position: fixed;
  top: 0;
  left: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  width: 100%;
  height: $header-height;
  padding: 0 20px;
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  box-sizing: border-box;

  &__brand {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
  }

  &__logo {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 42px;
    height: 42px;
    border-radius: 6px;
    background: linear-gradient(135deg, $color-main-dark, $color-main-light);
    flex-shrink: 0;
  }

  &__logo-icon {
    color: #fff;
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 1px;
  }

  &__title {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: #303133;
    white-space: nowrap;
  }

  &__nav {
    flex: 1;
    margin-left: 32px;
    min-width: 0;
    height: $header-height;
    background-color: transparent;
    border-bottom: none;

    :deep(.el-menu-item) {
      height: $header-height;
      line-height: $header-height;
      padding: 0 20px;
      font-size: 16px;
      color: #606266;

      &:hover {
        color: $color-main-dark;
        background-color: transparent;
      }

      &.is-active {
        color: $color-main-dark !important;
        background-color: transparent;
        border-bottom: 3px solid $color-main-dark;
      }

      &.is-active .el-icon {
        color: $color-main-dark;
      }
    }
  }

  &__right {
    display: flex;
    align-items: center;
    margin-left: auto;
    flex-shrink: 0;
  }

  &__user {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    user-select: none;
  }

  &__avatar {
    background: linear-gradient(135deg, $color-main-dark, $color-main-light) !important;
    flex-shrink: 0;
  }

  &__username {
    font-size: 15px;
    color: #303133;
    max-width: 120px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__arrow {
    font-size: 12px;
    color: $color-main-dark;
    transition: transform 0.2s ease;
  }
}
</style>