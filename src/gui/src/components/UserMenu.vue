<template>
  <v-menu close-on-back close-on-content-click>
    <template #activator="{ props }">
      <v-btn
        icon="mdi-account-outline"
        v-bind="props"
        data-testid="user-menu-button"
      />
    </template>
    <v-list>
      <v-list-item prepend-icon="mdi-account-outline" @click="userview">
        <v-list-item-title>{{ name }}</v-list-item-title>
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
import { useUserStore } from '@/stores/UserStore'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'

export default {
  name: 'UserMenu',
  setup() {
    const { name, organization, roles } = storeToRefs(useUserStore())
    const authStore = useAuthStore()
    const router = useRouter()

    const logout = async () => {
      await authStore.logout()
    }

    const settings = () => {
      router.push({ path: '/user/settings' })
    }

    const userview = () => {
      router.push({ path: '/user' })
    }

    return {
      name,
      organization,
      roles,
      logout,
      settings,
      userview
    }
  }
}
</script>
