import Permissions from '@/services/auth/permissions'
import { store } from '@/store/store'

const AuthMixin = {
  data: () => ({
    permissions: Permissions
  }),

  methods: {
    isAuthenticated() {
      return store.getters.isAuthenticated
    },
    needTokenRefresh() {
      return store.getters.needTokenRefresh
    },
    checkPermission(permission) {
      return store.getters.getPermissions.includes(permission)
    }
  }
}

export default AuthMixin
