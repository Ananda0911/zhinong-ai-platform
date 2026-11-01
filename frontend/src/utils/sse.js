/**
 * SSE 客户端：fetch POST + ReadableStream 解析（Axios 不支持流式）。
 * 约定事件：message(delta) / done(message_id) / error(message)
 */
export async function ssePost(url, body, { onMessage, onDone, onError } = {}) {
  const token = localStorage.getItem('zn_token')
  const resp = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  })

  if (!resp.ok) {
    // 非 200：尝试解析 JSON 错误（FastAPI detail）
    let msg = `请求失败（${resp.status}）`
    try {
      const data = await resp.json()
      msg = data.detail || data.message || msg
      // 422 校验错误的 detail 是数组/对象，必须转成字符串（下游 ElMessage 收到对象会导致渲染崩溃）
      if (Array.isArray(msg)) {
        msg = msg.map((e) => (e && e.msg ? `${e.loc?.slice(-1)[0] || ''} ${e.msg}` : String(e))).join('；')
      } else if (msg && typeof msg === 'object') {
        msg = msg.message || JSON.stringify(msg)
      }
    } catch {
      /* ignore */
    }
    onError?.(String(msg))
    return
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  const handleEvent = (block) => {
    let event = 'message'
    const dataLines = []
    for (const line of block.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim()
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
    }
    if (!dataLines.length) return
    let data
    try {
      data = JSON.parse(dataLines.join('\n'))
    } catch {
      return
    }
    if (event === 'message') onMessage?.(data)
    else if (event === 'done') onDone?.(data)
    else if (event === 'error') onError?.(data.message || '生成失败，请重试')
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    // 事件块以空行分隔
    let idx
    while ((idx = buffer.indexOf('\n\n')) !== -1) {
      const block = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      if (block.trim()) handleEvent(block)
    }
  }
  if (buffer.trim()) handleEvent(buffer)
}
