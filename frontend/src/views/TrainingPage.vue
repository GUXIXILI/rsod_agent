<!--
  模型训练页面占位组件
  提供标注数据集上传和训练参数配置入口，用于训练自定义目标检测模型
-->
<template>
  <div class="page-container">
    <div class="card-container placeholder-page">
      <el-icon :size="64" color="#C0C4CC">
        <Cpu />
      </el-icon>
      <h2>模型训练</h2>
      <p class="description">上传标注数据集，配置训练参数，训练自定义目标检测模型</p>
      <el-tag type="info">功能开发中，敬请期待</el-tag>
    </div>
  </div>
</template>

<script setup>
import { Cpu } from '@element-plus/icons-vue'
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