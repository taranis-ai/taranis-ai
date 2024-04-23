<template>
  <v-app class="grey lighten-2">
    <keep-alive>
      <MainMenu v-if="isAuthenticated" />
    </keep-alive>

    <router-view v-slot="{ Component }" name="nav">
      <keep-alive>
        <component :is="Component" />
      </keep-alive>
    </router-view>

    <v-main class="d-flex">
      <router-view v-slot="{ Component }">
        <keep-alive :include="['AssessView']">
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </v-main>

    <Notification v-if="isAuthenticated" />
  </v-app>
</template>

<script>
import MainMenu from '@/components/MainMenu.vue'
import Notification from '@/components/common/Notification.vue'
import { defineComponent, onMounted, watch } from 'vue'
import { useAuthStore } from '@/stores/AuthStore'
// import { useSseStore } from '@/stores/SseStore'
import { storeToRefs } from 'pinia'
import { useDisplay } from 'vuetify'

export default defineComponent({
  name: 'App',
  components: {
    MainMenu,
    Notification
  },
  setup() {
    const { isAuthenticated, timeToRefresh } = storeToRefs(useAuthStore())
    const authStore = useAuthStore()
    const { name: display } = useDisplay()
    // const sseStore = useSseStore()
    // const { isConnected } = storeToRefs(sseStore)

    // if (!isConnected.value) {
    //   if (isAuthenticated.value) {
    //     sseStore.connectSSE()
    //   }
    // }

    watch(display, (val) => {
      console.debug('Display:', val)
    })

    onMounted(() => {
      isAuthenticated.value || authStore.logout()

      if (timeToRefresh.value > 0) {
        setTimeout(() => {
          console.debug('Refreshing token')
          if (isAuthenticated.value) {
            authStore.refresh()
          }
        }, timeToRefresh.value)
      }
    })

    return {
      isAuthenticated
    }
  }
})
</script>

<style src="./assets/common.css"></style>

<style lang="scss">
@import '@/styles/awake.scss';

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
