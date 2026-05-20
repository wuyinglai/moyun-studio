import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  // 从 .env 加载后端地址，默认 8000
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  const apiTarget = env.VITE_API_TARGET || 'http://127.0.0.1:8000'

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    server: {
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          logLevel: 'debug',
        }
      }
    },
    optimizeDeps: {
      exclude: [
        '@codemirror/view', '@codemirror/state', '@codemirror/language',
        '@codemirror/commands', '@codemirror/lang-markdown', '@codemirror/search',
        '@lezer/highlight', '@lezer/common', '@lezer/lr', '@lezer/markdown',
      ],
    },
    css: {
      preprocessorOptions: {
        scss: {}
      }
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: (id) => {
            if (id.includes('@codemirror')) return 'codemirror'
            if (id.includes('ant-design-vue')) return 'antd'
            if (id.includes('marked') || id.includes('dompurify')) return 'markup'
            return undefined
          }
        }
      },
      chunkSizeWarningLimit: 1500
    }
  }
})
