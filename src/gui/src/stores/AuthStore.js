import { authenticate, authRefresh, authLogout } from '@/api/auth'
import { apiService } from '@/main'
import { Base64 } from 'js-base64'
import { useUserStore } from './UserStore'
import { useAssessStore } from './AssessStore'
import { useMainStore } from './MainStore'
import { useConfigStore } from './ConfigStore'
import { useAnalyzeStore } from './AnalyzeStore'
import { defineStore } from 'pinia'
import { router } from '@/router'
import { computed, ref } from 'vue'

export const useAuthStore = defineStore(
  'authenticator',
  () => {
    const jwt = ref('')
    const user = ref({})
    const sub = ref('')
    const exp = ref(0)

    const isAuthenticated = computed(
      () => new Date() < new Date(exp.value * 1000)
    )
    const timeToRefresh = computed(
      () => exp.value * 1000 - Date.now() - 300 * 1000
    )
    const expirationDate = computed(() => new Date(exp.value * 1000))
    const needTokenRefresh = computed(
      () => new Date() > new Date(exp.value * 1000 - 300 * 1000)
    )

    async function login(userData) {
      try {
        reset()
        const response = await authenticate(userData)
        setJwtToken(response.data.access_token)
        const userStore = useUserStore()
        userStore.loadUser()
      } catch (error) {
        reset()
        console.error(error)
        return error
      }
    }

    async function logout() {
      try {
        await authLogout()
      } catch (error) {
        console.error(error)
      }
      reset()
      router.push({ name: 'login' })
    }

    async function refresh() {
      try {
        console.debug('Refreshing token')
        const response = await authRefresh()
        setJwtToken(response.data.access_token)
        const userStore = useUserStore()
        userStore.loadUser()
      } catch {
        reset()
      }
    }

    function hasAccess(permission) {
      const userStore = useUserStore()
      const { permissions } = userStore
      if (permissions && permissions.length > 0) {
        return permissions.includes(permission)
      }
      return false
    }

    function setJwtToken(access_token) {
      localStorage.ACCESS_TOKEN = access_token
      apiService.setHeader()
      jwt.value = access_token
      const data = JSON.parse(Base64.decode(access_token.split('.')[1]))
      user.value = data.user_claims
      sub.value = data.sub
      exp.value = data.exp
    }

    function reset() {
      localStorage.ACCESS_TOKEN = ''
      jwt.value = ''
      user.value = {}
      sub.value = ''
      exp.value = 0
      const userStore = useUserStore()
      const assessStore = useAssessStore()
      const mainStore = useMainStore()
      const configStore = useConfigStore()
      const analyzeStore = useAnalyzeStore()
      userStore.reset_user()
      configStore.reset()
      mainStore.reset()
      assessStore.reset()
      analyzeStore.reset()
    }

    return {
      jwt,
      user,
      sub,
      exp,
      isAuthenticated,
      timeToRefresh,
      expirationDate,
      needTokenRefresh,
      login,
      logout,
      refresh,
      hasAccess,
      setJwtToken,
      reset
    }
  },
  {
    persist: true
  }
)
