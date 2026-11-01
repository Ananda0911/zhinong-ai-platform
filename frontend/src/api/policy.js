/** 政策问答（RAG，SSE 流式） */
import { ssePost } from '@/utils/sse'

export function policyChat(payload, handlers) {
  return ssePost('/api/policy/chat', payload, handlers)
}
