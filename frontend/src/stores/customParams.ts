import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface CustomParamCategory {
  key: string
  label: string
  options: string[]
}

export const useCustomParamsStore = defineStore('customParams', () => {
  // 默认选项
  const categories = ref<CustomParamCategory[]>([
    { key: 'genre', label: '题材', options: ['都市', '玄幻', '修仙', '科幻', '悬疑', '历史', '言情', '武侠'] },
    { key: 'tone', label: '基调', options: ['热血', '轻松', '悬疑', '治愈', '黑暗', '搞笑'] },
    { key: 'writing_style', label: '写作风格', options: ['细腻', '简洁', '幽默', '严肃', '抒情', '快节奏'] },
    { key: 'background', label: '背景', options: ['现代都市', '古代架空', '未来世界', '异界大陆', '校园生活', '末世废土', '西方奇幻'] },
    { key: 'theme', label: '主题', options: ['成长冒险', '爱恨情仇', '权谋斗争', '探索揭秘', '逆袭崛起', '团队协作', '文明冲突'] },
  ])

  function getOptions(key: string): string[] {
    return categories.value.find(c => c.key === key)?.options || []
  }

  function addOption(key: string, option: string) {
    const cat = categories.value.find(c => c.key === key)
    if (cat && !cat.options.includes(option)) {
      cat.options.push(option)
    }
  }

  function removeOption(key: string, option: string) {
    const cat = categories.value.find(c => c.key === key)
    if (cat) {
      cat.options = cat.options.filter(o => o !== option)
    }
  }

  function resetDefaults() {
    const defaults: Record<string, string[]> = {
      genre: ['都市', '玄幻', '修仙', '科幻', '悬疑', '历史', '言情', '武侠'],
      tone: ['热血', '轻松', '悬疑', '治愈', '黑暗', '搞笑'],
      writing_style: ['细腻', '简洁', '幽默', '严肃', '抒情', '快节奏'],
      background: ['现代都市', '古代架空', '未来世界', '异界大陆', '校园生活', '末世废土', '西方奇幻'],
      theme: ['成长冒险', '爱恨情仇', '权谋斗争', '探索揭秘', '逆袭崛起', '团队协作', '文明冲突'],
    }
    for (const cat of categories.value) {
      cat.options = defaults[cat.key] || []
    }
  }

  return {
    categories,
    getOptions,
    addOption,
    removeOption,
    resetDefaults,
  }
}, {
  persist: {
    storage: localStorage,
    pick: ['categories'],
  },
})
