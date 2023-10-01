<template>
  <v-app-bar
    dense
    flat
    class="bg-cx-app-header pr-0 pl-0"
    :height="48"
    app
    clipped-left
  >
    <template #prepend>
      <v-btn color="primary" @click.stop="navClicked">
        <v-icon
          :class="['menu-icon', { closed: !drawerVisible }]"
          icon="mdi-menu-open"
        />
      </v-btn>
    </template>

    <v-toolbar-title>
      <img
        src="@/assets/taranis-logo.svg"
        alt="taranis logo"
        style="max-width: 360px; height: 100%"
        class="py-2"
      />
    </v-toolbar-title>

    <div v-if="showItemCount" class="mr-10">
      <span>
        total items: <strong>{{ itemCountTotal }}</strong>
      </span>
      <span v-if="isFiltered">
        / displayed items: <strong>{{ itemCountFiltered }}</strong>
      </span>
    </div>

    <template #append>
      <v-toolbar color="transparent">
        <div v-for="button in buttonList" :key="button.route">
          <v-btn variant="text" :ripple="false" :to="button.route">
            <v-icon left>{{ button.icon }}</v-icon>
            <span class="main-menu-item">
              {{ $t(button.title) }}
            </span>
          </v-btn>
        </div>
        <user-menu />
      </v-toolbar>
    </template>
  </v-app-bar>
</template>

<script>
import UserMenu from '@/components/UserMenu.vue'

import { storeToRefs } from 'pinia'
import { useMainStore } from '@/stores/MainStore'
import { defineComponent, computed } from 'vue'
import { useI18n } from 'vue-i18n'

export default defineComponent({
  name: 'MainMenu',
  components: { UserMenu },
  setup() {
    const store = useMainStore()
    const { d } = useI18n()

    store.updateFromLocalConfig()

    const { drawerVisible, itemCountTotal, itemCountFiltered, buildDate } =
      storeToRefs(store)

    const showItemCount = computed(() => {
      return itemCountTotal.value !== undefined && itemCountTotal.value > 0
    })

    const isFiltered = computed(() => {
      return itemCountFiltered.value === undefined
        ? false
        : itemCountFiltered.value !== itemCountTotal.value
    })

    const navClicked = () => {
      store.toggleDrawer()
    }
    const buttons = [
      {
        title: 'main_menu.dashboard',
        icon: 'mdi-monitor-dashboard',
        permission: 'ASSESS_ACCESS',
        route: '/',
        show: true
      },
      {
        title: 'main_menu.administration',
        icon: 'mdi-cog-outline',
        permission: 'CONFIG_ACCESS',
        route: '/config',
        show: true
      },
      {
        title: 'main_menu.enter',
        icon: 'mdi-location-enter',
        permission: 'ASSESS_CREATE',
        route: '/enter',
        show: false
      },
      {
        title: 'main_menu.assess',
        icon: 'mdi-google-circles-extended',
        permission: 'ASSESS_ACCESS',
        route: '/assess',
        show: true
      },
      {
        title: 'main_menu.analyze',
        icon: 'mdi-google-circles-communities',
        permission: 'ANALYZE_ACCESS',
        route: '/analyze',
        show: true
      },
      {
        title: 'main_menu.publish',
        icon: 'mdi-publish',
        permission: 'PUBLISH_ACCESS',
        route: '/publish',
        show: true
      },
      {
        title: 'main_menu.assets',
        icon: 'mdi-file-multiple-outline',
        permission: 'MY_ASSETS_ACCESS',
        route: '/assets',
        show: true
      }
    ]

    const buttonList = computed(() => {
      return buttons.filter(
        (button) =>
          store.user.permissions.includes(button.permission) && button.show
      )
    })

    return {
      d,
      buildDate,
      isFiltered,
      showItemCount,
      itemCountFiltered,
      itemCountTotal,
      drawerVisible,
      buttonList,
      navClicked
    }
  }
})
</script>

<style lang="scss">
.v-toolbar-title,
.v-toolbar-title div {
  height: 100%;
}
</style>
