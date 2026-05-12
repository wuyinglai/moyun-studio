// API 统一响应格式
export interface ApiResponse<T = unknown> {
  success: boolean
  data?: T
  message?: string
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

// 通用错误
export interface ApiError {
  code: string
  message: string
  details?: Record<string, unknown>
}
