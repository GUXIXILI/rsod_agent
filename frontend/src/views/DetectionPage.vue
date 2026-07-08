<!--
  检测工作台页面占位组件
  提供图片或视频上传入口，使用 YOLOv11 模型进行目标检测
-->
<template>
  <div class="page-container">
    <div class="card-container placeholder-page">
      <el-icon :size="64" color="#C0C4CC">
        <Picture />
      </el-icon>
      <h2>检测工作台</h2>
      <p class="description">上传图片或视频，使用 YOLOv11 模型进行目标检测</p>
      <el-tag type="info">功能开发中，敬请期待</el-tag>
    </div>
  </div>
</template>

<script setup>
import { Picture } from '@element-plus/icons-vue'
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