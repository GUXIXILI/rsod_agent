<template>
  <!-- 主布局：Header + Sidebar + 内容区 三栏结构 -->
  <div class="main-layout">
    <!-- 顶部导航栏 -->
    <AppHeader />

    <!-- 左侧侧边栏 -->
    <AppSidebar />

    <!-- 右侧主内容区 -->
    <main class="main-layout__content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import AppHeader from './AppHeader.vue'
import AppSidebar from './AppSidebar.vue'
</script>

<style lang="scss" scoped>
/* 主布局容器 */
.main-layout {
  width: 100%;
  min-height: 100vh;

  /* 右侧主内容区 —— 避开 Header 和 Sidebar 的固定区域 */
  &__content {
    margin-left: $sidebar-width;
    margin-top: $header-height;
    min-height: calc(100vh - $header-height);
    padding: 20px;
    background-color: $bg-page;
    box-sizing: border-box;
  }
}
</style>