import request from '@/api'

// ───── 供应 ─────
export function listSupply(params) {
  return request.get('/supply', { params })
}

export function getSupply(id) {
  return request.get(`/supply/${id}`)
}

export function createSupply(data) {
  return request.post('/supply', data)
}

export function updateSupply(id, data) {
  return request.put(`/supply/${id}`, data)
}

export function setSupplyStatus(id, status) {
  return request.put(`/supply/${id}/status`, { status })
}

export function deleteSupply(id) {
  return request.delete(`/supply/${id}`)
}

// ───── 求购 ─────
export function listPurchase(params) {
  return request.get('/purchase', { params })
}

export function getPurchase(id) {
  return request.get(`/purchase/${id}`)
}

export function createPurchase(data) {
  return request.post('/purchase', data)
}

export function updatePurchase(id, data) {
  return request.put(`/purchase/${id}`, data)
}

export function setPurchaseStatus(id, status) {
  return request.put(`/purchase/${id}/status`, { status })
}

export function deletePurchase(id) {
  return request.delete(`/purchase/${id}`)
}

// ───── AI 匹配 ─────
export function matchForSupply(id) {
  return request.get(`/match/supply/${id}`)
}

export function matchForPurchase(id) {
  return request.get(`/match/purchase/${id}`)
}
