import { ssePost } from '@/utils/sse'

/**
 * 农技对话（SSE 流式）。
 * @returns Promise，流结束（done 或 error）时 resolve
 */
export function agritechChat({ sessionId, content, imageUrl }, callbacks = {}) {
  return ssePost(
    '/api/agritech/chat',
    { session_id: sessionId, content, image_url: imageUrl || null },
    callbacks,
  )
}
