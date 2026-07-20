<template>
  <!-- 主布局：顶部 Header + 内容区 -->
  <div class="main-layout">
    <!-- 顶部导航栏 -->
    <AppHeader />

    <!-- 主内容区 -->
    <main class="main-layout__content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import AppHeader from './AppHeader.vue'
</script>

<style lang="scss" scoped>
/* 主布局容器 */
.main-layout {
  width: 100%;
  min-height: 100vh;

  /* 主内容区 —— 仅避开顶部 Header */
  &__content {
    margin-left: 0;
    margin-top: $header-height;
    min-height: calc(100vh - $header-height);
    padding: 20px;
    background-color: $bg-page;
    box-sizing: border-box;
  }
}
</style>