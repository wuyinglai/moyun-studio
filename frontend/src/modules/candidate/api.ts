/** 候选稿模块 - API 调用 */

import api from '@/services/api'
import { API_ROUTES } from '@/shared/api/routes'
import type { CandidateInfo, CandidateDetail, AdoptResult, CandidateRevisionRequest } from './types'

/** 获取项目的候选稿列表 */
export async function listCandidates(projectId: string, status?: string): Promise<CandidateInfo[]> {
  const params: Record<string, string> = {}
  if (status) params.status = status
  const res = await api.get<{ candidates: CandidateInfo[] }>(`/candidates/${projectId}`, params)
  return res.candidates || []
}

/** 获取候选稿详情（含正文） */
export async function getCandidateDetail(projectId: string, candidateId: string): Promise<CandidateDetail> {
  return await api.get<CandidateDetail>(`/candidates/${projectId}/${candidateId}`)
}

/** 采用候选稿 */
export async function adoptCandidate(projectId: string, candidateId: string): Promise<AdoptResult> {
  return await api.post<AdoptResult>(`/candidates/${projectId}/${candidateId}/adopt`, {
    project_id: projectId,
    candidate_id: candidateId,
  })
}

/** 根据用户反馈生成 child revision candidate */
export async function reviseCandidate(
  projectId: string,
  candidateId: string,
  request: CandidateRevisionRequest,
): Promise<CandidateInfo> {
  return await api.post<CandidateInfo>(API_ROUTES.candidateRevise(projectId, candidateId), request)
}

/** 删除候选稿 */
export async function deleteCandidate(projectId: string, candidateId: string): Promise<{ success: boolean; message: string }> {
  return await api.post(API_ROUTES.candidateDelete(projectId, candidateId), {
    project_id: projectId,
    candidate_id: candidateId,
  })
}
