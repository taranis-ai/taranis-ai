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

    <div v-if="showItemCount && mdAndUp" class="mr-4 menu-item-info">
      <span>
        total items: <strong>{{ itemCountTotal }}</strong>
      </span>
      <span v-if="isFiltered">
        / displayed: <strong>{{ itemCountFiltered }}</strong>
      </span>
      <v-tooltip activator="parent" location="bottom">
        <v-icon icon="mdi-eye-check-outline" size="x-small" class="mr-1" />
        read: <strong>{{ itemCountRead }}</strong
        ><br />
        <v-icon icon="mdi-eye-off-outline" size="x-small" class="mr-1" />
        unread: <strong>{{ itemCountUnread }}</strong>
        <br />
        <v-icon icon="mdi-star-check-outline" size="x-small" class="mr-1" />
        important: <strong>{{ itemCountImportant }}</strong>
        <br />
        <v-icon
          icon="mdi-google-circles-communities"
          size="x-small"
          class="mr-1"
        />
        in report: <strong>{{ itemCountInReport }}</strong>
        <br />
      </v-tooltip>
    </div>

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
    />

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
            <span class="main-menu-item"> {{ $t(button.title) }} </span>
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

import { storeToRefs } from 'pinia'
import { useMainStore } from '@/stores/MainStore'
import { useUserStore } from '@/stores/UserStore'
import { useFilterStore } from '@/stores/FilterStore'
import { defineComponent, computed, ref } from 'vue'
import { useDisplay } from 'vuetify'
import { useRoute } from 'vue-router'

export default defineComponent({
  name: 'MainMenu',
  components: { UserMenu },
  setup() {
    const mainStore = useMainStore()
    const userStore = useUserStore()
    const filterStore = useFilterStore()
    const { smAndDown, mdAndUp } = useDisplay()
    const route = useRoute()

    const { drawerVisible, itemCountTotal, itemCountFiltered, buildDate } =
      storeToRefs(mainStore)

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

    const showItemCount = computed(() => {
      return itemCountTotal.value !== undefined && itemCountTotal.value > 0
    })

    const isFiltered = computed(() => {
      return itemCountFiltered.value === undefined
        ? false
        : itemCountFiltered.value !== itemCountTotal.value
    })

    const itemCountRead = computed(() => {
      // TODO: Get value from store
      return 0
    })
    const itemCountUnread = computed(() => {
      // TODO: Get value from store
      return 0
    })
    const itemCountImportant = computed(() => {
      // TODO: Get value from store
      return 0
    })
    const itemCountInReport = computed(() => {
      // TODO: Get value from store
      return 0
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
        route.path.startsWith('/config')
      )
    })

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
      mdAndUp,
      searchState,
      showSearchBar,
      isFiltered,
      showItemCount,
      itemCountFiltered,
      itemCountTotal,
      drawerVisible,
      showNavButton,
      buttonList,
      navClicked,
      itemCountRead,
      itemCountUnread,
      itemCountImportant,
      itemCountInReport
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

.menu-item-info span {
  color: #969696;
  cursor: help;
}
</style>
