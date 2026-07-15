<template>
  <!-- 侧边栏导航 -->
  <aside class="app-sidebar">
    <el-menu
      :default-active="activeMenu"
      :router="true"
      class="app-sidebar__menu"
      background-color="#1A1A2E"
      text-color="#bfcbd9"
      active-text-color="#FF6B35"
    >
      <!-- 智能对话 -->
      <el-menu-item index="/chat">
        <el-icon>
          <ChatDotRound />
        </el-icon>
        <span>智能对话</span>
      </el-menu-item>

      <!-- 检测工作台 -->
      <el-menu-item index="/detection">
        <el-icon>
          <Picture />
        </el-icon>
        <span>检测工作台</span>
      </el-menu-item>

      <!-- 摄像头检测 -->
      <el-menu-item index="/camera-detection">
        <el-icon>
          <VideoCamera />
        </el-icon>
        <span>摄像头检测</span>
      </el-menu-item>

      <!-- 模型训练 -->
      <el-menu-item index="/training">
        <el-icon>
          <Cpu />
        </el-icon>
        <span>模型训练</span>
      </el-menu-item>

      <!-- 历史记录 -->
      <el-menu-item index="/history">
        <el-icon>
          <Clock />
        </el-icon>
        <span>历史记录</span>
      </el-menu-item>

      <!-- 数据看板 -->
      <el-menu-item index="/dashboard">
        <el-icon>
          <DataAnalysis />
        </el-icon>
        <span>数据看板</span>
      </el-menu-item>

      <!-- 个人设置 -->
      <el-menu-item index="/settings">
        <el-icon>
          <Setting />
        </el-icon>
        <span>个人设置</span>
      </el-menu-item>
    </el-menu>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  ChatDotRound,
  Picture,
  VideoCamera,
  Cpu,
  Clock,
  DataAnalysis,
  Setting
} from '@element-plus/icons-vue'

// 获取当前路由信息
const route = useRoute()

/**
 * 当前激活的菜单项，根据路由路径动态计算
 * 确保菜单高亮与当前页面保持一致
 */
const activeMenu = computed(() => route.path)
</script>

<style lang="scss" scoped>
/* 侧边栏 —— 固定定位在左侧，顶部偏移 $header-height */
.app-sidebar {
  position: fixed;
  top: $header-height;
  left: 0;
  z-index: 900;
  width: $sidebar-width;
  height: calc(100vh - $header-height);
  overflow-y: auto;
  overflow-x: hidden;

  /* 菜单容器 */
  &__menu {
    min-height: 100%;
    border-right: none;

    /* 高亮菜单项背景色 */
    :deep(.el-menu-item.is-active) {
      background-color: #16213E !important;
    }

    /* 菜单项悬停效果 */
    :deep(.el-menu-item:hover) {
      background-color: #16213E;
    }
  }
}
</style>