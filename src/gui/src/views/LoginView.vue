<template>
  <v-container class="login-container d-flex flex-column pa-0 ma-auto">
    <v-row no-gutters justify="center" align-content="center" class="mb-5">
      <v-col cols="10" sm="5" class="d-flex justify-center">
        <img
          src="@/assets/taranis-logo-login.svg"
          alt="taranis logo"
          class="mb-5"
          style="max-width: 500px"
        />
      </v-col>
    </v-row>
    <ExternalLogin v-if="authMethod === 'external'" />
    <LoginForm v-else />
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
