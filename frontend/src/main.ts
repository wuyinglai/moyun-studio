import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPersistedstate from 'pinia-plugin-persistedstate'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import router from './router'
import './assets/styles/base.css'
import App from './App.vue'
import { useUIStore } from './stores/ui'

const pinia = createPinia()
pinia.use(piniaPersistedstate)

const app = createApp(App)
app.use(pinia)
app.use(router)
app.use(Antd)

// 初始化主题（Pinia persist 恢复后自动 applyTheme）
useUIStore()

app.mount('#app')
