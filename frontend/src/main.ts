import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPersistedstate from 'pinia-plugin-persistedstate'
import router from './router'
import './assets/styles/base.css'
import App from './App.vue'
import { useTheme } from './composables/useTheme'

const pinia = createPinia()
pinia.use(piniaPersistedstate)

const app = createApp(App)
app.use(pinia)
app.use(router)

// 初始化主题（读取 localStorage 并应用到 DOM）
const { initTheme } = useTheme()
initTheme()

app.mount('#app')
