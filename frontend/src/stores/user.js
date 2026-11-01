import { defineStore } from 'pinia'
import { login as loginApi, register as registerApi } from '@/api/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('zn_token') || '',
    user: JSON.parse(localStorage.getItem('zn_user') || 'null'),
  }),

  getters: {
    isLoggedIn: (s) => !!s.token,
    role: (s) => s.user?.role || '',
    roleLabel: (s) =>
      ({ farmer: '农户/合作社', buyer: '采购商', admin: '管理员' }[s.user?.role] || '用户'),
  },

  actions: {
    persist() {
      if (this.token) localStorage.setItem('zn_token', this.token)
      else localStorage.removeItem('zn_token')
      if (this.user) localStorage.setItem('zn_user', JSON.stringify(this.user))
      else localStorage.removeItem('zn_user')
    },

    async login(form) {
      const data = await loginApi(form)
      this.token = data.access_token
      this.user = data.user
      this.persist()
      return data.user
    },

    async register(form) {
      return registerApi(form)
    },

    async fetchMe() {
      const { fetchMe } = await import('@/api/auth')
      this.user = await fetchMe()
      this.persist()
      return this.user
    },

    logout() {
      this.token = ''
      this.user = null
      this.persist()
    },
  },
})
