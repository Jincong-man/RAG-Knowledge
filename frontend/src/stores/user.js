import { defineStore } from 'pinia'
import { authApi } from '../api/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    user: JSON.parse(localStorage.getItem('user_info') || 'null'),
    token: localStorage.getItem('access_token') || null,
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    isAdmin: (state) => state.user?.role === 'admin',
    username: (state) => state.user?.username || '',
  },

  actions: {
    async login(username, password) {
      const data = await authApi.login(username, password)
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      this.token = data.access_token
      // 获取用户信息
      await this.fetchUserInfo()
      return data
    },

    async fetchUserInfo() {
      try {
        const user = await authApi.getMe()
        this.user = user
        localStorage.setItem('user_info', JSON.stringify(user))
      } catch {
        // ignore
      }
    },

    logout() {
      this.user = null
      this.token = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user_info')
    },
  },
})
