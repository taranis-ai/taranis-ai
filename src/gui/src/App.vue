<template>
  <v-app class="grey lighten-2">
    <MainMenu v-if="isAuthenticated" />

    <router-view name="nav"></router-view>

    <v-main class="d-flex">
      <router-view />
    </v-main>

    <Notification v-if="isAuthenticated" />
  </v-app>
</template>

<script>
import MainMenu from '@/components/MainMenu.vue'
import Notification from '@/components/common/Notification.vue'
import { defineComponent, onMounted, watch } from 'vue'
import { useAuthStore } from '@/stores/AuthStore'
import { useFilterStore } from '@/stores/FilterStore'
import { useMainStore } from '@/stores/MainStore'
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
    const { compactView, compactViewSetByUser } = storeToRefs(useFilterStore())
    const { drawerVisible, drawerSetByUser } = storeToRefs(useMainStore())

    const { mdAndDown, lgAndDown, name: displayName } = useDisplay()

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

    watch(
      () => mdAndDown.value,
      (nv) => {
        if (compactViewSetByUser.value) return
        compactView.value = nv
      },
      { immediate: true }
    )

    watch(
      () => lgAndDown.value,
      (nv) => {
        if (drawerSetByUser.value) return
        drawerVisible.value = !nv
      },
      { immediate: true }
    )

    watch(
      () => displayName.value,
      (newValue) => {
        console.debug('Display name changed to', newValue)
      },
      { immediate: true }
    )

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

mark {
  background-color: $primary;
  color: white;
  padding: 2px 5px;
}
</style>
