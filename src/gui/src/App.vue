<template>
  <v-app class="grey lighten-2">
    <MainMenu v-if="isAuthenticated" />

    <router-view name="nav"></router-view>

    <v-main>
      <router-view />
    </v-main>

    <Notification v-if="isAuthenticated" />
  </v-app>
</template>

<script>
import MainMenu from '@/components/MainMenu.vue'
import Notification from '@/components/common/Notification.vue'
import { defineComponent, onMounted, onBeforeUpdate } from 'vue'
import { useAuthStore } from '@/stores/AuthStore'
import { connectSSE, reconnectSSE } from '@/utils/sse'
import { storeToRefs } from 'pinia'

export default defineComponent({
  name: 'App',
  components: {
    MainMenu,
    Notification
  },
  setup() {
    const { isAuthenticated, needTokenRefresh, jwt } = storeToRefs(
      useAuthStore()
    )
    const authStore = useAuthStore()

    onBeforeUpdate(() => {
      if (isAuthenticated.value) {
        if (needTokenRefresh.value) {
          authStore.refresh().then(() => {
            console.debug('Token refreshed')
            reconnectSSE()
          })
        }
      }
    })

    onMounted(() => {
      if (isAuthenticated.value) {
        authStore.setAuthURLs()
        connectSSE()
      } else {
        if (jwt) {
          authStore.logout()
        }
      }
    })

    return {
      isAuthenticated
    }
  }
})
</script>

<style src="./assets/common.css"></style>
<style src="./assets/centralize.css"></style>

<style lang="scss">
@import '@/styles/awake.scss';
</style>
