/**
 * 爽文模式开局卡预取缓存
 * 提前生成开局卡，实现秒开体验
 */
import { fetchLiteIdeas, type LiteIdeaCard } from '@/services/liteService'

let _cache: LiteIdeaCard[] | null = null
let _fetchPromise: Promise<LiteIdeaCard[]> | null = null

async function _fetch(): Promise<LiteIdeaCard[]> {
  return await fetchLiteIdeas(String(Date.now()))
}

/**
 * 在后台预取下一批开局卡（如果尚未开始）
 * 失败时静默，后续 consumeOrFetch 自动重试
 */
export function prefetchIdeas(): void {
  if (!_fetchPromise) {
    _fetchPromise = _fetch()
      .then((cards) => {
        _cache = cards
        _fetchPromise = null
        return cards
      })
      .catch((err: unknown) => {
        console.error('预取开局卡失败:', err instanceof Error ? err.message : err)
        _fetchPromise = null
        return [] as LiteIdeaCard[]
      })
  }
}

/**
 * 消费缓存中的开局卡，秒返回；没有缓存则等待当前请求
 * 消费完后自动触发下一批预取
 */
export async function consumeOrFetch(): Promise<LiteIdeaCard[]> {
  if (_cache) {
    const cards = _cache
    _cache = null
    prefetchIdeas()
    return cards
  }

  if (!_fetchPromise) {
    prefetchIdeas()
  }

  // 必须在 await 之前捕获引用，因为 .then 中的 _fetchPromise = null 会在 await 恢复前执行
  const promise = _fetchPromise!
  const cards = await promise
  _cache = null
  prefetchIdeas()
  return cards || []
}
