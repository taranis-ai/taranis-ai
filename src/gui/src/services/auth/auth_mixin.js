import { useAuthStore } from '@/stores/AuthStore'

const AuthMixin = {
  methods: {
    isAuthenticated() {
      const authstore = useAuthStore()
      return authstore.isAuthenticated
    },
    needTokenRefresh() {
      const authstore = useAuthStore()
      return authstore.needTokenRefresh
    },
    checkPermission(permission) {
      const authstore = useAuthStore()
      return authstore.user.permissions.includes(permission)
    }
  }
}

export default AuthMixin
