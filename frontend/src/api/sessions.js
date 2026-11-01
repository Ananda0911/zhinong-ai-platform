import request from '@/api'

export function listSessions(type) {
  return request.get('/sessions', { params: { type } })
}

export function createSession(type) {
  return request.post('/sessions', { type })
}

export function listMessages(sessionId) {
  return request.get(`/sessions/${sessionId}/messages`)
}

export function deleteSession(sessionId) {
  return request.delete(`/sessions/${sessionId}`)
}

export function uploadImage(file) {
  const form = new FormData()
  form.append('file', file)
  return request.post('/upload/image', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
