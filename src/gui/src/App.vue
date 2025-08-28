<template>
  <v-app class="grey lighten-2">
    <v-main class="d-flex"> MAIN VIEW </v-main>

    <HotKeysDialog v-if="isAuthenticated" />
    <Notification v-if="isAuthenticated" />
  </v-app>
</template>

<script>
import MainMenu from '@/components/MainMenu.vue'
import Notification from '@/components/common/Notification.vue'
import HotKeysDialog from '@/components/common/HotKeysDialog.vue'
import { defineComponent, onMounted, watch } from 'vue'
import { useAuthStore } from '@/stores/AuthStore'
import { storeToRefs } from 'pinia'
import { useDisplay } from 'vuetify'
import { sseHandler } from '@/utils/sse'

export default defineComponent({
  name: 'App',
  components: {
    MainMenu,
    Notification,
    HotKeysDialog
  },
  setup() {
    const { isAuthenticated } = storeToRefs(useAuthStore())
    const authStore = useAuthStore()
    const { name: display } = useDisplay()

    watch(display, (val) => {
      console.debug('Display:', val)
    })

    onMounted(() => {
      authStore.refresh()
      isAuthenticated.value || authStore.logout()
      sseHandler()
    })

    return {
      isAuthenticated
    }
  }
})
</script>

<style src="./assets/common.css"></style>

<style lang="scss">
@use '@/styles/awake.scss' as *;

.v-application {
  font-size: 14px;
  letter-spacing: normal;
  h2 {
    font-size: 1.3rem;
  }
  p {
    font-size: 0.95rem;
    font-weight: 300;
  }
}
</style>
