import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

export const useStoryStateStore = defineStore('storyState', () => {
  const content = ref('')
  const isLoading = ref(false)

  async function load(projectId: string) {
    isLoading.value = true
    try {
      const data = await api.get('/file', {
        params: { project_id: projectId, path: 'story-state.md' },
      })
      content.value = data?.content || ''
    } catch {
      content.value = ''
    } finally {
      isLoading.value = false
    }
  }

  async function save(projectId: string) {
    await api.post(`/file?project_id=${projectId}`, {
      path: 'story-state.md',
      content: content.value,
    })
  }

  async function updateAfterChapter(projectId: string, chapterContent: string, filePath = '') {
    const timestamp = new Date().toLocaleString()
    const excerpt = chapterContent
      .replace(/^# .*\n?/, '')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 360)
    const title = filePath ? `｜${filePath}` : ''
    const entry = [
      '',
      '',
      `## ${timestamp}${title}`,
      '',
      `- 已写内容：${excerpt || '当前章节暂无正文。'}`,
      '- 人物欲望：请根据本节正文补充主角此刻最想要的东西。',
      '- 冲突推进：记录本节新暴露的阻力、对手或代价。',
      '- 读者期待：记录下一节最应该兑现或反转的期待。',
    ].join('\n')
    content.value += entry
    await save(projectId)
  }

  return { content, isLoading, load, save, updateAfterChapter }
})
