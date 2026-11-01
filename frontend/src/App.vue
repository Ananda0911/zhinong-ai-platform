<template>
  <el-config-provider :locale="zhCn">
    <router-view />
  </el-config-provider>
</template>

<script setup>
// 按需引入模式下，locale 通过 ConfigProvider 提供（日期/分页/弹窗等中文文案）
import zhCn from 'element-plus/es/locale/lang/zh-cn'
</script>
