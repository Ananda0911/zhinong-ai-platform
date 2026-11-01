/** 营销工具：文案生成（SSE 流式）+ 生成历史 */
import request from '@/api'
import { ssePost } from '@/utils/sse'

export function generateMarketing(payload, handlers) {
  return ssePost('/api/marketing/generate', payload, handlers)
}

export function listMarketingRecords() {
  return request.get('/marketing/records')
}
