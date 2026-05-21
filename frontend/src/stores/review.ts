import { defineStore } from 'pinia'
import api from '@/services/api'
import { API_ROUTES } from '@/shared/api/routes'
import type { ReviewRequest, ReviewResponse, BatchReviewRequest, BatchReviewResponse } from '@/types/chat'

export const useReviewStore = defineStore('review', () => {
  /**
   * 审查单个章节
   */
  async function reviewChapter(req: ReviewRequest): Promise<ReviewResponse> {
    return await api.post<ReviewResponse>('/quality/review', req)
  }

  /**
   * 批量审查多个章节
   */
  async function reviewBatch(req: BatchReviewRequest): Promise<BatchReviewResponse> {
    return await api.post<BatchReviewResponse>('/quality/review-batch', req)
  }

  /**
   * 获取项目的所有审查历史
   */
  async function listReviews(projectId: string): Promise<{ reviews: Record<string, unknown>[]; total: number }> {
    return await api.get(API_ROUTES.qualityReviews(projectId))
  }

  return {
    reviewChapter,
    reviewBatch,
    listReviews,
  }
})
