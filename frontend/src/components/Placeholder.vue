<template>
  <div class="placeholder-wrap">
    <div class="placeholder-card">
      <div class="ph-icon">
        <el-icon :size="34"><component :is="icon" /></el-icon>
      </div>
      <h3>{{ title }}</h3>
      <p>{{ description }}</p>
      <el-tag type="warning" effect="plain" round>
        <el-icon style="vertical-align: -2px"><Tools /></el-icon>
        {{ phase }} 开发中
      </el-tag>
    </div>
  </div>
</template>

<script setup>
import { Tools } from '@element-plus/icons-vue'

defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
  icon: { type: String, default: 'Box' },
  phase: { type: String, default: 'Phase 2' },
})
</script>

<style scoped>
.placeholder-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 140px);
}
.placeholder-card {
  text-align: center;
  background: #fff;
  border: 1px solid #e5ebe7;
  border-radius: 18px;
  padding: 56px 64px;
  box-shadow: 0 1px 2px rgba(20, 83, 45, 0.04), 0 8px 28px rgba(20, 83, 45, 0.06);
}
.ph-icon {
  width: 76px;
  height: 76px;
  margin: 0 auto 20px;
  border-radius: 20px;
  background: linear-gradient(135deg, #f0fdf4, #dcfce7);
  color: #16a34a;
  display: flex;
  align-items: center;
  justify-content: center;
}
h3 {
  margin: 0 0 10px;
  font-size: 19px;
  color: #1f2d27;
}
p {
  margin: 0 0 18px;
  font-size: 13.5px;
  color: #8aa294;
  max-width: 340px;
}
</style>
