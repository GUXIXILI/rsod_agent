<!--
  历史记录页面占位组件
  提供过往检测结果和对话历史的查看入口
-->
<template>
  <div class="page-container">
    <div class="card-container placeholder-page">
      <el-icon :size="64" color="#C0C4CC">
        <Clock />
      </el-icon>
      <h2>历史记录</h2>
      <p class="description">查看过往的检测结果和对话历史</p>
      <el-tag type="info">功能开发中，敬请期待</el-tag>
    </div>
  </div>
</template>

<script setup>
import { Clock } from '@element-plus/icons-vue'
</script>

<style scoped lang="scss">
.placeholder-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  min-height: 400px;
  gap: $spacing-lg;

  h2 {
    margin: 0;
    font-size: 24px;
    color: $primary-color;
  }

  .description {
    max-width: 480px;
    margin: 0;
    color: $text-secondary;
    font-size: 14px;
    line-height: 1.6;
  }
}
</style>