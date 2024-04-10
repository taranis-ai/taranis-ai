import { authenticate, refresh } from '@/api/auth'
import { apiService } from '@/main'
import { Base64 } from 'js-base64'
import { useUserStore } from './UserStore'
import { useSseStore } from './SseStore'
import { useAssessStore } from './AssessStore'
import { useMainStore } from './MainStore'
import { useConfigStore } from './ConfigStore'
import { defineStore } from 'pinia'
import { router } from '@/router'

export const useAuthStore = defineStore('authenticator', {
  state: () => ({
    jwt: '',
    login_uri: '/login',
    user: {},
    sub: '',
    exp: 0
  }),
  getters: {
    isAuthenticated: (state) => new Date() < new Date(state.exp * 1000),
    timeToRefresh: (state) => state.exp * 1000 - Date.now() - 300 * 1000,
    expirationDate: (state) => new Date(state.exp * 1000),
    needTokenRefresh: (state) =>
      new Date() > new Date(state.exp * 1000 - 300 * 1000)
  },
  actions: {
    async login(userData) {
      try {
        const response = await authenticate(userData)
        this.setJwtToken(response.data.access_token)
        const userStore = useUserStore()
        userStore.loadUser()
      } catch (error) {
        this.clearJwtToken()
        console.error(error)
        return error
      }
    },
    async logout() {
      this.clearJwtToken()
      this.$reset()
      const userStore = useUserStore()
      userStore.reset_user()
      const assessStore = useAssessStore()
      const sseStore = useSseStore()
      const mainStore = useMainStore()
      const configStore = useConfigStore()
      configStore.$reset()
      mainStore.reset()
      sseStore.resetSSE()
      assessStore.reset()
      router.push({ name: 'login' })
    },
    async refresh() {
      try {
        console.debug('Refreshing token')
        const response = await refresh()
        this.setJwtToken(response.data.access_token)
        const userStore = useUserStore()
        userStore.loadUser()
      } catch {
        this.clearJwtToken()
      }
    },
    hasAccess(permission) {
      const userStore = useUserStore()
      const { permissions } = userStore
      if (permissions && permissions.length > 0) {
        return permissions.includes(permission)
      }
      return false
    },
    setJwtToken(access_token) {
      localStorage.ACCESS_TOKEN = access_token
      apiService.setHeader()
      this.jwt = access_token
      const data = JSON.parse(Base64.decode(access_token.split('.')[1]))
      this.user = data.user_claims
      this.sub = data.sub
      this.exp = data.exp
    },
    clearJwtToken() {
      localStorage.ACCESS_TOKEN = ''
    }
  },
  persist: true
})
