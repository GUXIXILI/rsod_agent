<template>
  <!-- 顶部导航栏 -->
  <header class="app-header">
    <!-- 左侧：Logo + 平台名称 -->
    <div class="app-header__left">
      <div class="app-header__logo">
        <!-- Logo 占位图标，后续可替换为实际 Logo 图片 -->
        <span class="app-header__logo-icon">RS</span>
      </div>
      <h1 class="app-header__title">RSOD Agent Platform</h1>
    </div>

    <!-- 右侧：用户下拉菜单 -->
    <div class="app-header__right">
      <el-dropdown trigger="click" @command="handleCommand">
        <!-- 触发元素：用户头像 + 用户名 -->
        <span class="app-header__user">
          <el-avatar
            :size="32"
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

        <!-- 下拉菜单项 -->
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">
              <el-icon>
                <User />
              </el-icon>
              个人中心
            </el-dropdown-item>
            <el-dropdown-item command="logout" divided>
              <el-icon>
                <SwitchButton />
              </el-icon>
              退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User, SwitchButton, ArrowDown } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

// 用户状态管理
const userStore = useUserStore()

// 路由实例
const router = useRouter()

/**
 * 处理下拉菜单命令
 * @param {string} command - 菜单项标识
 */
const handleCommand = async (command) => {
  if (command === 'profile') {
    // 个人中心功能尚未实现，暂时只给出友好提示
    ElMessage.info('个人中心功能开发中')
  } else if (command === 'logout') {
    try {
      // 退出登录确认对话框
      await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      })
      // 确认后执行退出
      await userStore.logout()
      router.push('/login')
    } catch {
      // 用户取消操作，不做任何处理
    }
  }
}
</script>

<style lang="scss" scoped>
/* 顶部导航栏 —— 固定定位在最顶部 */
.app-header {
  position: fixed;
  top: 0;
  left: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  height: $header-height;
  padding: 0 20px;
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  box-sizing: border-box;

  /* 左侧区域 */
  &__left {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  /* Logo 图标 */
  &__logo {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 6px;
    background: linear-gradient(135deg, #409eff, #67c23a);
    flex-shrink: 0;
  }

  &__logo-icon {
    color: #fff;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 1px;
  }

  /* 平台名称 */
  &__title {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    color: #303133;
    white-space: nowrap;
  }

  /* 右侧用户区域 */
  &__right {
    display: flex;
    align-items: center;
  }

  /* 用户信息触发区域 */
  &__user {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    user-select: none;
  }

  /* 用户头像 */
  &__avatar {
    background-color: #409eff;
    flex-shrink: 0;
  }

  /* 用户名 */
  &__username {
    font-size: 14px;
    color: #303133;
    max-width: 120px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* 下拉箭头 */
  &__arrow {
    font-size: 12px;
    color: #909399;
    transition: transform 0.2s ease;
  }
}
</style>