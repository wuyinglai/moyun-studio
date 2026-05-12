/**
 * usePanelConfig - 面板配置持久化 composable
 * 管理三栏布局比例和编辑区/聊天区比例
 */
import { ref, computed } from 'vue'
import { getStorage, setStorage, STORAGE_KEYS } from '@/utils/storage'

// 默认比例：[左栏, 中栏, 右栏]，单位 %
const DEFAULT_H_SIZES = [20, 55, 25]
const DEFAULT_V_SIZES = [75, 25] // 编辑区, 聊天区

const hSizes = ref<number[]>(getStorage<number[]>(STORAGE_KEYS.LAYOUT_SIZES, DEFAULT_H_SIZES))
const vSizes = ref<number[]>(getStorage<number[]>(STORAGE_KEYS.EDITOR_CHAT_SIZES, DEFAULT_V_SIZES))

export function usePanelConfig() {
  /** 更新水平三栏比例 */
  function setHorizontalSizes(sizes: number[]) {
    hSizes.value = sizes
    setStorage(STORAGE_KEYS.LAYOUT_SIZES, sizes)
  }

  /** 更新编辑区/聊天区垂直比例 */
  function setVerticalSizes(sizes: number[]) {
    vSizes.value = sizes
    setStorage(STORAGE_KEYS.EDITOR_CHAT_SIZES, sizes)
  }

  /** 重置为默认值 */
  function reset() {
    setHorizontalSizes(DEFAULT_H_SIZES)
    setVerticalSizes(DEFAULT_V_SIZES)
  }

  /** 获取当前配置 */
  const config = computed(() => ({
    horizontal: [...hSizes.value],
    vertical: [...vSizes.value],
  }))

  return {
    hSizes,
    vSizes,
    setHorizontalSizes,
    setVerticalSizes,
    reset,
    config,
    DEFAULT_H_SIZES,
    DEFAULT_V_SIZES,
  }
}
