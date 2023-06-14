<template>
  <v-container fluid class="login-screen" fill-height>
    <v-row no-gutters justify="center" align-content="center">
      <img
        :width="400"
        src="@/assets/taranis-logo-login.svg"
        alt="taranis logo"
      />
    </v-row>
    <v-form id="form" ref="form" @submit.prevent="authenticate">
      <v-row no-gutters justify="center" align-content="center">
        <v-col cols="3">
          <v-text-field
            v-model="username"
            :placeholder="$t('login.username')"
            name="username"
            prepend-icon="person"
            type="text"
            :rules="[acceptUser]"
            autocomplete="username"
            required
          />
        </v-col>
        <v-col cols="3">
          <v-text-field
            v-model="password"
            :placeholder="$t('login.password')"
            name="password"
            prepend-icon="lock"
            type="password"
            :rules="[acceptPassword]"
            autocomplete="password"
            required
          />
        </v-col>
        <v-col cols="1">
          <v-btn
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
  </v-container>
</template>

<script>
import { useAuthStore } from '@/stores/AuthStore'
import { useSettingsStore } from '@/stores/SettingsStore'
import { defineComponent, ref, computed, inject, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'

export default defineComponent({
  name: 'LoginView',

  setup() {
    const username = ref('')
    const password = ref('')
    const login_error = ref(undefined)
    const coreAPIURL = inject('$coreAPIURL')
    const router = useRouter()
    const authStore = useAuthStore()
    console.debug('coreAPIURL', coreAPIURL)

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
