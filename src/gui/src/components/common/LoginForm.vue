<template>
  <v-form id="form" ref="form" @submit.prevent="authenticate">
    <v-row no-gutters justify="center" align-content="center" class="mt-5">
      <v-col cols="8" sm="5" class="d-flex justify-center">
        <v-text-field
          ref="userfield"
          v-model="username"
          :placeholder="$t('login.username')"
          name="username"
          prepend-inner-icon="mdi-account-outline"
          type="text"
          variant="outlined"
          :rules="[acceptUser]"
          autocomplete="username"
          max-width="440px"
          required
        />
      </v-col>
    </v-row>
    <v-row no-gutters justify="center" align-content="center" class="mb-3">
      <v-col cols="8" sm="5" class="d-flex justify-center">
        <v-text-field
          v-model="password"
          :placeholder="$t('login.password')"
          name="password"
          prepend-inner-icon="mdi-lock-outline"
          type="password"
          variant="outlined"
          :rules="[acceptPassword]"
          autocomplete="current-password"
          max-width="440px"
          required
        />
      </v-col>
    </v-row>
    <v-row no-gutters justify="center" align-content="center">
      <v-col cols="8" sm="5" class="d-flex" style="max-width: 440px">
        <v-btn
          color="primary"
          prepend-icon="mdi-login-variant"
          type="submit"
          class="mb-5"
          block
          variant="outlined"
          :disabled="loginButtonDisabled"
        >
          login
        </v-btn>
      </v-col>
    </v-row>
  </v-form>
  <v-expand-transition>
    <v-alert
      v-if="login_error !== undefined"
      dense
      type="error"
      icon="mdi-close-circle-outline"
      :text="$t(login_error)"
      location="bottom"
      position="fixed"
      :rounded="false"
      width="100%"
      class="opacity-90 py-3"
    />
  </v-expand-transition>
</template>

<script>
import { useAuthStore } from '@/stores/AuthStore'
import { defineComponent, ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'

export default defineComponent({
  name: 'LoginForm',

  setup() {
    const username = ref('')
    const password = ref('')
    const login_error = ref(undefined)
    const router = useRouter()
    const authStore = useAuthStore()
    const userfield = ref(null)

    const acceptPassword = computed(() =>
      password.value.length > 0 ? true : 'Please enter a password'
    )
    const acceptUser = computed(() =>
      username.value.length > 0 ? true : 'Please enter a username'
    )
    const loginButtonDisabled = computed(
      () => password.value.length < 1 || username.value.length < 1
    )

    const { isAuthenticated } = storeToRefs(authStore)

    async function authenticate() {
      try {
        await authStore.login({
          username: username.value,
          password: password.value
        })
        login_error.value = undefined
        router.push('/')
      } catch (error) {
        if (error.status > 500) {
          login_error.value = 'login.backend_error'
        } else {
          login_error.value = 'login.error'
        }
        return
      }
    }

    onMounted(() => {
      if (isAuthenticated.value) {
        router.push('/')
      }
      userfield.value.focus()
    })

    return {
      username,
      password,
      userfield,
      login_error,
      acceptPassword,
      acceptUser,
      loginButtonDisabled,
      authenticate
    }
  }
})
</script>

<style scoped>
.login-container {
  margin-top: 10%;
}
</style>
