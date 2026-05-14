import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      }
    }
  },
  optimizeDeps: {
    exclude: ['@codemirror/view'],
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
})
