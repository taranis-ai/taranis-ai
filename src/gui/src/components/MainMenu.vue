<template>
  <v-app-bar
    dense
    flat
    class="bg-cx-app-header pr-0 pl-0"
    :height="48"
    app
    clipped-left
  >
    <v-app-bar-nav-icon
      color="primary"
      :disabled="!showNavButton"
      :icon="drawerVisible ? 'mdi-menu-open' : 'mdi-menu-close'"
      @click.stop="navClicked"
    />
    <v-app-bar-title>
      <img
        src="@/assets/taranis-logo.svg"
        alt="Taranis AI"
        style="max-width: 360px; height: 100%"
        class="py-3"
      />
    </v-app-bar-title>

    <ItemCount />

    <v-text-field
      v-if="showSearchBar"
      id="omni-search"
      v-model="searchState"
      placeholder="search"
      variant="outlined"
      hide-details
      density="compact"
      prepend-inner-icon="mdi-magnify"
      class="mx-3 omni-search"
    >
      <template #append-inner>
        <v-btn
          text="ctrl+k"
          density="compact"
          size="small"
          variant="outlined"
          class="no-pointer"
          color="#cccccc"
        />
      </template>
    </v-text-field>

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
            :rounded="false"
            :to="button.route"
            :prepend-icon="button.icon"
            class="main-menu-btn"
          >
            <span class="main-menu-item">{{ $t(button.title) }}</span>
          </v-btn>
        </div>
        <user-menu />
      </v-toolbar>
      <user-menu v-if="smAndDown" />
    </template>
  </v-app-bar>
</template>

<script>
import UserMenu from '@/components/UserMenu.vue'
import ItemCount from '@/components/common/ItemCount.vue'

import { storeToRefs } from 'pinia'
import { useMainStore } from '@/stores/MainStore'
import { useUserStore } from '@/stores/UserStore'
import { useFilterStore } from '@/stores/FilterStore'
import { defineComponent, computed, ref } from 'vue'
import { useDisplay } from 'vuetify'
import { useRoute } from 'vue-router'

export default defineComponent({
  name: 'MainMenu',
  components: { UserMenu, ItemCount },
  setup() {
    const mainStore = useMainStore()
    const userStore = useUserStore()
    const filterStore = useFilterStore()
    const { smAndDown } = useDisplay()
    const route = useRoute()

    const { drawerVisible, buildDate } = storeToRefs(mainStore)

    const timeout = ref(null)
    const searchState = computed({
      get: () => {
        if (route.name === 'assess') {
          return filterStore.storyFilter.search
        }
        if (route.name === 'analyze') {
          return filterStore.reportFilter.search
        }
        if (route.name === 'publish') {
          return filterStore.productFilter.search
        }
        return ''
      },
      set: (value) => {
        clearTimeout(timeout.value)
        timeout.value = setTimeout(() => {
          if (route.name === 'assess') {
            filterStore.storyFilter.search = value
          }
          if (route.name === 'analyze') {
            filterStore.reportFilter.search = value
          }
          if (route.name === 'publish') {
            filterStore.productFilter.search = value
          }
        }, 500)
      }
    })

    const navClicked = () => {
      mainStore.toggleDrawer()
    }

    const showSearchBar = computed(() => {
      return (
        route.name === 'assess' ||
        route.name === 'analyze' ||
        route.name === 'publish'
      )
    })

    const showNavButton = computed(() => {
      return (
        route.name === 'assess' ||
        route.name === 'analyze' ||
        route.name === 'publish' ||
        route.name === 'assets' ||
        (route.path.startsWith('/config') &&
          !/^\/config\/sources\/[^/]+/.test(route.path))
      )
    })

    const buttons = [
      {
        title: 'main_menu.dashboard',
        icon: 'mdi-view-dashboard-variant-outline',
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
        icon: 'mdi-arrow-collapse-up',
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
      searchState,
      showSearchBar,
      drawerVisible,
      showNavButton,
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

.main-menu-btn.v-btn:hover,
.v-btn--active {
  color: rgb(var(--v-theme-primary));
  padding-top: 4px;
  border-bottom: 4px solid rgb(var(--v-theme-primary));
}

.main-menu-btn.v-btn {
  height: calc(var(--v-btn-height) + 12px) !important;
  & .v-btn__overlay {
    background-color: transparent;
  }
}

.omni-search {
  transition: max-width 100ms ease-in-out;
  max-width: 192px;
}

.omni-search:focus-within {
  max-width: 800px;
}
.no-pointer:hover {
  cursor: default !important;
}
</style>
