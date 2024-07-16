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
      <ExternalLogin v-if="authMethod === 'external'" />
      <LoginForm v-else />
    </div>
  </v-container>
</template>

<script setup>
import LoginForm from '@/components/common/LoginForm.vue'
import ExternalLogin from '@/components/common/ExternalLogin.vue'
import { useAuthStore } from '@/stores/AuthStore'
import { storeToRefs } from 'pinia'

const authStore = useAuthStore()

const { authMethod } = storeToRefs(authStore)

authStore.setAuthMethod()
</script>

<style scoped>
.login-container {
  margin-top: 10%;
}
</style>
