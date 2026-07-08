<!--
  智能对话页面占位组件
  提供与 AI 助手进行智能对话的入口，用于获取目标检测相关的帮助和建议
-->
<template>
  <div class="page-container">
    <div class="card-container placeholder-page">
      <el-icon :size="64" color="#C0C4CC">
        <ChatDotRound />
      </el-icon>
      <h2>智能对话</h2>
      <p class="description">在这里与 AI 助手进行智能对话，获取目标检测相关的帮助和建议</p>
      <el-tag type="info">功能开发中，敬请期待</el-tag>
    </div>
  </div>
</template>

<script setup>
import { ChatDotRound } from '@element-plus/icons-vue'
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