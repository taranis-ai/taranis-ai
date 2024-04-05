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
        <v-icon :icon="drawerVisible ? 'mdi-menu-open' : 'mdi-menu-close'" />
      </v-btn>
    </template>

    <v-toolbar-title>
      <img
        src="@/assets/taranis-logo.svg"
        alt="taranis logo"
        style="max-width: 360px; height: 100%"
        class="py-3"
      />
    </v-toolbar-title>

    <div v-if="showItemCount && mdAndUp" class="mr-10">
      <span>
        total items: <strong>{{ itemCountTotal }}</strong>
      </span>
      <span v-if="isFiltered">
        / displayed items: <strong>{{ itemCountFiltered }}</strong>
      </span>
    </div>

    <template #append>
      <v-menu v-if="smAndDown" offset-y class="mx-5">
        <template #activator="{ props }">
          <v-btn
            v-ripple="false"
            density="compact"
            v-bind="props"
            icon="mdi-view-headline"
          />
        </template>

        <v-list dense>
          <v-list-item
            v-for="button in buttonList"
            :key="button.route"
            :to="button.route"
            :title="$t(button.title)"
          />
        </v-list>
      </v-menu>
      <v-toolbar v-else color="transparent">
        <div v-for="button in buttonList" :key="button.route">
          <v-btn
            variant="text"
            :ripple="false"
            :to="button.route"
            :prepend-icon="button.icon"
          >
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
import { useUserStore } from '@/stores/UserStore'
import { defineComponent, computed } from 'vue'
import { useDisplay } from 'vuetify'

export default defineComponent({
  name: 'MainMenu',
  components: { UserMenu },
  setup() {
    const mainStore = useMainStore()
    const userStore = useUserStore()
    const { smAndDown, mdAndUp } = useDisplay()

    const { drawerVisible, itemCountTotal, itemCountFiltered, buildDate } =
      storeToRefs(mainStore)

    const showItemCount = computed(() => {
      return itemCountTotal.value !== undefined && itemCountTotal.value > 0
    })

    const isFiltered = computed(() => {
      return itemCountFiltered.value === undefined
        ? false
        : itemCountFiltered.value !== itemCountTotal.value
    })

    const navClicked = () => {
      mainStore.toggleDrawer()
    }
    const buttons = [
      {
        title: 'main_menu.dashboard',
        icon: 'mdi-monitor-dashboard',
        permission: 'ASSESS_ACCESS',
        route: '/'
      },
      {
        title: 'main_menu.administration',
        icon: 'mdi-cog-outline',
        permission: 'CONFIG_ACCESS',
        route: '/config/dashboard'
      },
      {
        title: 'main_menu.assess',
        icon: 'mdi-google-circles-extended',
        permission: 'ASSESS_ACCESS',
        route: '/assess'
      },
      {
        title: 'main_menu.analyze',
        icon: 'mdi-google-circles-communities',
        permission: 'ANALYZE_ACCESS',
        route: '/analyze'
      },
      {
        title: 'main_menu.publish',
        icon: 'mdi-publish',
        permission: 'PUBLISH_ACCESS',
        route: '/publish'
      },
      {
        title: 'main_menu.assets',
        icon: 'mdi-file-multiple-outline',
        permission: 'ASSETS_ACCESS',
        route: '/assets'
      }
    ]

    const buttonList = computed(() => {
      return buttons.filter((button) =>
        userStore.permissions.includes(button.permission)
      )
    })

    return {
      buildDate,
      smAndDown,
      mdAndUp,
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

.v-btn--active i {
  color: #7468e8;
}
</style>
