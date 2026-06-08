/**
 * Scene Plan API 调用封装
 *
 * 提供 generate、save、load 三个核心 API 的类型安全调用。
 */

import api from '@/services/api'
import { API_ROUTES } from '@/shared/api/routes'

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
