<template>
  <v-container class="login-container flex-column">
    <div class="ma-auto" style="max-width: 900px">
      <v-row
        no-gutters
        justify="center"
        align-content="center"
        style="margin-bottom: 4rem"
      >
        <img
          src="@/assets/taranis-logo-login.svg"
          alt="taranis logo"
          class="mb-5 pb-5"
          style="max-width: 600px"
        />
      </v-row>
      <v-form id="form" ref="form" @submit.prevent="authenticate">
        <v-row no-gutters justify="center" align-content="center">
          <v-col cols="12">
            <v-text-field
              v-model="username"
              class="mx-2"
              :placeholder="$t('login.username')"
              name="username"
              prepend-icon="mdi-account-outline"
              type="text"
              :rules="[acceptUser]"
              autocomplete="username"
              required
            />
          </v-col>
          <v-col cols="12">
            <v-text-field
              v-model="password"
              class="mx-2"
              :placeholder="$t('login.password')"
              name="password"
              prepend-icon="mdi-lock-outline"
              type="password"
              :rules="[acceptPassword]"
              autocomplete="password"
              required
            />
          </v-col>
          <v-col cols="12" class="d-flex">
            <v-btn
              class="ma-auto"
              icon="mdi-login-variant"
              type="submit"
              color="primary"
              :disabled="loginButtonDisabled"
              @click="authenticate"
            />
          </v-col>
        </v-row>
      </v-form>
      <v-alert v-if="login_error !== undefined" dense type="error" text>{{
        $t(login_error)
      }}</v-alert>
    </div>
  </v-container>
</template>

<script>
import { useAuthStore } from '@/stores/AuthStore'
import { useSettingsStore } from '@/stores/SettingsStore'
import { defineComponent, ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'

export default defineComponent({
  name: 'LoginView',

  setup() {
    const username = ref('')
    const password = ref('')
    const login_error = ref(undefined)
    const router = useRouter()
    const authStore = useAuthStore()

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
    const { loadUserProfile } = useSettingsStore()

    const authenticate = () => {
      authStore
        .login({ username: username.value, password: password.value })
        .then((error) => {
          if (error) {
            if (error.status > 500) {
              login_error.value = 'login.backend_error'
            } else {
              login_error.value = 'login.error'
            }
            return
          }

          login_error.value = undefined
          console.debug('login successful')
          loadUserProfile()
          router.push('/')
        })
    }

    onMounted(() => {
      if (isAuthenticated.value) {
        router.push('/')
      }
    })

    return {
      username,
      password,
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
