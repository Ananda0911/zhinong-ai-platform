/** 管理后台：统计看板 / 用户管理 / 内容治理 / 政策文档管理 */
import request from '@/api'

// ── 统计 ──
export function getStats() {
  return request.get('/admin/stats')
}

// ── 用户管理 ──
export function listUsers(params) {
  return request.get('/admin/users', { params })
}

export function setUserStatus(id, isActive) {
  return request.put(`/admin/users/${id}/status`, { is_active: isActive })
}

// ── 内容治理 ──
export function listContents(params) {
  return request.get('/admin/contents', { params })
}

export function setContentStatus(type, id, status) {
  return request.put(`/admin/contents/${type}/${id}/status`, { status })
}

// ── 政策文档 ──
export function uploadPolicyDoc(file, title) {
  const form = new FormData()
  form.append('file', file)
  return request.post('/admin/policy-docs', form, {
    params: title ? { title } : {},
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function listPolicyDocs() {
  return request.get('/admin/policy-docs')
}

export function deletePolicyDoc(id) {
  return request.delete(`/admin/policy-docs/${id}`)
}
