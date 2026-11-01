import request from '@/api'

export function register(data) {
  return request.post('/auth/register', data)
}

export function login(data) {
  return request.post('/auth/login', data)
}

export function fetchMe() {
  return request.get('/auth/me')
}
