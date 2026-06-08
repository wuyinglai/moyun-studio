/**
 * Scene Plan API 调用封装
 *
 * 提供 generate、save、load 三个核心 API 的类型安全调用。
 * 同时提供轻量状态共享，用于在组件间传递当前 Scene Plan。
 */

import { ref } from 'vue'
import api from '@/services/api'
import { API_ROUTES } from '@/shared/api/routes'

/** 全局共享状态 - 当前 Scene Plan */
const currentScenePlan = ref<ScenePlanData | null>(null)
const currentScenePlanValid = ref(false)
const currentScenePlanSourceFile = ref('')
const hasSavedScenePlan = ref(false)
const useScenePlanForGeneration = ref(false)

/** Scene Plan 结构（简化版） */
export interface ScenePlanData {
  project_id: string
  source_path: string
  title?: string
  goal?: string
  conflict?: string
  required_beats?: string[]
  output_intent?: {
    mode: string
    preserve_lines?: string[]
  }
  candidate_policy?: {
    require_candidate: boolean
    allow_direct_write: boolean
  }
  [key: string]: unknown
}

/** Scene Plan 生成请求 */
export interface ScenePlanGenerateRequest {
  project_id: string
  target_file: string
  instruction?: string
  dry_run?: boolean
  include_raw_output?: boolean
}

/** Scene Plan 生成响应 */
export interface ScenePlanGenerateResponse {
  scene_plan: ScenePlanData | null
  valid: boolean
  errors: Array<{ field: string; message: string }>
  warnings: Array<{ field: string; message: string }>
  raw_output?: string | null
  source_summary: {
    target_file: string
    used_story_state: boolean
    used_style_guide: boolean
    used_recent_context: boolean
  }
}

/** Scene Plan 保存请求 */
export interface ScenePlanSaveRequest {
  project_id: string
  target_file: string
  scene_plan: ScenePlanData
  overwrite?: boolean
  expected_mtime?: number | null
}

/** Scene Plan 保存响应 */
export interface ScenePlanSaveResponse {
  saved: boolean
  path: string | null
  valid: boolean
  errors: Array<{ field: string; message: string }>
  warnings: Array<{ field: string; message: string }>
  conflict: boolean
  message: string | null
}

/** Scene Plan 加载响应 */
export interface ScenePlanLoadResponse {
  exists: boolean
  path: string | null
  scene_plan: ScenePlanData | null
  mtime: number | null
  errors: Array<{ field: string; message: string }>
}

/** Scene Plan 校验响应 */
export interface ScenePlanValidateResponse {
  valid: boolean
  errors: Array<{ field: string; message: string }>
  warnings: Array<{ field: string; message: string }>
}

/** 生成 Scene Plan */
export async function generateScenePlan(
  request: ScenePlanGenerateRequest
): Promise<ScenePlanGenerateResponse> {
  const response = await api.post<ScenePlanGenerateResponse>(
    API_ROUTES.scenePlanGenerate,
    request
  )
  return response
}

/** 保存 Scene Plan */
export async function saveScenePlan(
  request: ScenePlanSaveRequest
): Promise<ScenePlanSaveResponse> {
  const response = await api.post<ScenePlanSaveResponse>(
    API_ROUTES.scenePlanSave,
    request
  )
  return response
}

/** 加载已保存的 Scene Plan */
export async function loadScenePlan(
  projectId: string,
  targetFile: string
): Promise<ScenePlanLoadResponse> {
  const response = await api.get<ScenePlanLoadResponse>(
    API_ROUTES.scenePlanLoad,
    {
      params: {
        project_id: projectId,
        target_file: targetFile,
      },
    }
  )
  return response
}

/** 校验 Scene Plan */
export async function validateScenePlan(
  scenePlan: ScenePlanData
): Promise<ScenePlanValidateResponse> {
  const response = await api.post<ScenePlanValidateResponse>(
    API_ROUTES.scenePlanValidate,
    scenePlan
  )
  return response
}

/**
 * Scene Plan 状态管理 - 用于组件间共享
 */

/** 设置当前 Scene Plan */
export function setCurrentScenePlan(
  plan: ScenePlanData | null,
  valid: boolean,
  sourceFile: string,
  saved: boolean = false
): void {
  currentScenePlan.value = plan
  currentScenePlanValid.value = valid
  currentScenePlanSourceFile.value = sourceFile
  hasSavedScenePlan.value = saved
}

/** 获取当前 Scene Plan */
export function getCurrentScenePlan(): ScenePlanData | null {
  return currentScenePlan.value
}

/** 获取当前 Scene Plan 是否有效 */
export function getCurrentScenePlanValid(): boolean {
  return currentScenePlanValid.value
}

/** 获取当前 Scene Plan 的源文件路径 */
export function getCurrentScenePlanSourceFile(): string {
  return currentScenePlanSourceFile.value
}

/** 是否有已保存的 Scene Plan */
export function getHasSavedScenePlan(): boolean {
  return hasSavedScenePlan.value
}

/** 设置是否在 Professional 生成时使用 Scene Plan */
export function setUseScenePlanForGeneration(enabled: boolean): void {
  useScenePlanForGeneration.value = enabled
}

/** 获取是否在 Professional 生成时使用 Scene Plan */
export function getUseScenePlanForGeneration(): boolean {
  return useScenePlanForGeneration.value
}

/** 清除当前 Scene Plan 状态（切换文件时调用） */
export function clearCurrentScenePlan(): void {
  currentScenePlan.value = null
  currentScenePlanValid.value = false
  currentScenePlanSourceFile.value = ''
  hasSavedScenePlan.value = false
  useScenePlanForGeneration.value = false
}

/**
 * 判断是否可以使用 Scene Plan 进行生成
 * @param targetFile 可选的 target file 路径，用于校验 source file 匹配
 * 如果传入 targetFile，则必须满足 currentScenePlanSourceFile === targetFile
 */
export function canUseScenePlanForGeneration(targetFile?: string): boolean {
  const hasPlan = currentScenePlan.value !== null
  const isValid = currentScenePlanValid.value
  const isEnabled = useScenePlanForGeneration.value

  // 如果传入了 targetFile，必须校验 source file 匹配
  if (targetFile !== undefined) {
    const sourceFile = currentScenePlanSourceFile.value
    const fileMatch = sourceFile === targetFile
    return isEnabled && hasPlan && isValid && fileMatch
  }

  // 不传入 targetFile 时，只做基本检查（用于 UI 显示）
  return isEnabled && hasPlan && isValid
}
