import { createApp } from 'vue'
import { createPinia } from 'pinia'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import { ElLoading } from 'element-plus'
// 按需引入模式：命令式 API 与指令的样式兜底（模板组件由 unplugin 自动注入）
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/message-box/style/css'
import 'element-plus/es/components/loading/style/css'
import '@/styles/theme.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(createPinia())
app.use(router)
app.use(ElLoading) // 注册 v-loading 指令（按需模式下指令需手动注册）
app.mount('#app')
