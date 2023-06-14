<template>
  <v-menu close-on-back close-on-content-click>
    <template #activator="{ props }">
      <v-btn icon="mdi-account" v-bind="props" />
    </template>
    <v-list>
      <v-list-item prepend-icon="mdi-account" @click="userview">
        <v-list-item-title>{{ user.name }}</v-list-item-title>
        <v-list-item-subtitle>{{
          user.organization_name
        }}</v-list-item-subtitle>
      </v-list-item>
      <v-divider></v-divider>

      <v-list-item prepend-icon="mdi-cog-outline" @click="settings">
        <v-list-item-title> {{ $t('user_menu.settings') }}</v-list-item-title>
      </v-list-item>

      <v-list-item prepend-icon="mdi-logout" @click="logout">
        <v-list-item-title> {{ $t('user_menu.logout') }}</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script>
import { useAuthStore } from '@/stores/AuthStore'
import { useMainStore } from '@/stores/MainStore'
import { useRouter } from 'vue-router'

export default {
  name: 'UserMenu',
  setup() {
    const { user } = useMainStore()
    const authStore = useAuthStore()
    const router = useRouter()

    const logout = async () => {
      await authStore.logout()
      window.location.reload()
    }

    const settings = () => {
      router.push({ path: '/user/settings' })
    }

    const userview = () => {
      router.push({ path: '/user' })
    }

    return {
      user,
      logout,
      settings,
      userview
    }
  }
}
</script>
