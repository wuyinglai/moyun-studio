import { computed } from 'vue'
import { useEditorStore } from '@/stores/editor'
import { usePipelineStore } from '@/stores/pipeline'
import { isSceneFile as isSceneFilePath } from '@/modules/scene/scenePath'

export function useEditorFileActions() {
  const editorStore = useEditorStore()
  const pipelineStore = usePipelineStore()

  /** 当前文件是否为场景正文文件（sec-*.md） */
  const isSceneFile = computed(() => {
    const path = editorStore.currentFilePath || ''
    return isSceneFilePath(path)
  })

  /** 兼容旧名称 */
  const isChapterFile = isSceneFile

  /** 当前文件是否为系统维护文件 */
  const isSystemFile = computed(() => {
    const path = editorStore.currentFilePath || ''
    return /style-guide\.md$|story-state\.md$|recent-context\.md$|\.json$/.test(path)
  })

  /** 自定义管线列表 */
  const customPipelines = computed(() =>
    pipelineStore.pipelines.filter(p => p.source === 'custom')
  )

  return {
    isSceneFile,
    isChapterFile,
    isSystemFile,
    customPipelines,
  }
}
