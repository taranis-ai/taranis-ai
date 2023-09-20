import { authenticate, refresh } from '@/api/auth'
import { apiService } from '@/main'
import { Base64 } from 'js-base64'
import { useMainStore } from './MainStore'
import { useAssessStore } from './AssessStore'
import { defineStore } from 'pinia'
import { router } from '@/router'

export const useAuthStore = defineStore('authenticator', {
  state: () => ({
    jwt: '',
    login_uri: '/login',
    logout_uri: '/logout',
    external_login_uri: false,
    external_logout_uri: false,
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
        const store = useMainStore()
        store.user = this.user
      } catch (error) {
        this.clearJwtToken()
        console.error(error)
        return error
      }
    },
    logout() {
      this.clearJwtToken()
      this.$reset()
      const mainStore = useMainStore()
      mainStore.reset_user()
      const assessStore = useAssessStore()
      assessStore.$reset()
      router.push({ name: 'login' })
    },
    async refresh() {
      try {
        const response = await refresh()
        this.setJwtToken(response.data.access_token)
        const store = useMainStore()
        store.user = this.user
      } catch {
        this.clearJwtToken()
      }
    },
    setToken(access_token) {
      this.setJwtToken(access_token)
      const store = useMainStore()
      store.user = this.user
    },
    setAuthURLs() {
      this.setLoginURL()
      this.setLogoutURL()
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
    },
    setLoginURL() {
      if (import.meta.env.VITE_TARANIS_NG_LOGIN_URL) {
        this.login_uri = import.meta.env.VITE_TARANIS_NG_LOGIN_URL
        this.external_login_uri = true
      }
    },
    setLogoutURL() {
      if (
        typeof import.meta.env !== 'undefined' &&
        import.meta.env.VITE_TARANIS_NG_LOGOUT_URL != null
      ) {
        this.logout_uri = import.meta.env.VITE_TARANIS_NG_LOGOUT_URL
        this.external_logout_uri = true
      }
    }
  },
  persist: true
})
