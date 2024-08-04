<template>
  <v-alert
    v-if="login_error !== undefined"
    dense
    type="error"
    :text="$t(login_error)"
  />
</template>

<script>
import { useAuthStore } from '@/stores/AuthStore'
import { defineComponent, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'

export default defineComponent({
  name: 'ExternalLogin',

  setup() {
    const login_error = ref(undefined)
    const router = useRouter()
    const authStore = useAuthStore()

    const { isAuthenticated } = storeToRefs(authStore)

    async function authenticate() {
      try {
        await authStore.login()
        login_error.value = undefined
        router.push('/')
      } catch (error) {
        if (error.status > 500) {
          login_error.value = 'login.backend_error'
        } else {
          login_error.value = 'login.external_error'
        }
        return
      }
    }

    onMounted(() => {
      if (isAuthenticated.value) {
        router.push('/')
        return
      }
      authenticate()
    })

    return {
      login_error
    }
  }
})
</script>

<style scoped>
.login-container {
  margin-top: 10%;
}
</style>
