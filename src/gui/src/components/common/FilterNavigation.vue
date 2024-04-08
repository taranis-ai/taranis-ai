<template>
  <div>
    <v-app-bar v-if="!drawerVisible || showOmniSearch" :elevation="1">
      <v-btn
        v-if="showOmniSearch && drawerVisible"
        style="margin-left: 230px"
        prepend-icon="mdi-chevron-left"
        color="primary"
        @click="showOmniSearch = !showOmniSearch"
      />
      <v-text-field
        v-model="searchState"
        placeholder="search"
        varint="outlined"
        hide-details
        density="compact"
        prepend-icon="mdi-magnify"
        class="mr-5 ml-5"
      />
      <slot name="appbar"></slot>
    </v-app-bar>
    <v-navigation-drawer
      v-if="drawerVisible"
      color="cx-drawer-bg"
      :permanent="true"
      :width="300"
    >
      <v-container class="pa-0 ma-0">
        <!-- search -->
        <v-row v-if="!showOmniSearch" class="mx-2 my-4 px-2">
          <v-text-field
            v-model="searchState"
            placeholder="search"
            variant="outlined"
            hide-details
            density="compact"
            prepend-inner-icon="mdi-magnify"
            class="search-field"
          >
            <template #append>
              <v-btn
                density="compact"
                color="primary"
                variant="tonal"
                size="small"
                class="pa-0"
                style="height: 100%"
                @click="showOmniSearch = !showOmniSearch"
              >
                <v-icon size="x-large" class="pa-0" icon="mdi-chevron-right" />
              </v-btn>
            </template>
          </v-text-field>
        </v-row>

        <v-divider class="my-2" />

        <!-- scope -->
        <v-row v-if="showPaging" no-gutters class="ma-2 my-4 px-2">
          <v-autocomplete
            v-model="limitState"
            :items="itemsPerPage"
            label="Items per page"
            variant="outlined"
            density="compact"
            hide-details
          />
        </v-row>

        <slot name="navdrawer"></slot>
      </v-container>
    </v-navigation-drawer>
  </div>
</template>

<script>
import { computed, ref, watch } from 'vue'
import { useMainStore } from '@/stores/MainStore'
import { storeToRefs } from 'pinia'

export default {
  name: 'FilterNavigation',
  props: {
    search: {
      type: String,
      default: ''
    },
    showPaging: {
      type: Boolean,
      default: true
    },
    limit: {
      type: Number,
      default: 20
    }
  },
  emits: ['update:search', 'update:limit'],
  setup(props, { emit }) {
    const showOmniSearch = ref(false)
    const itemsPerPage = [20, 40, 100, 200, 400]
    const timeout = ref(null)
    const store = useMainStore()

    const { drawerVisible } = storeToRefs(store)

    const limitState = computed({
      get: () => props.limit,
      set: (value) => emit('update:limit', value)
    })

    const searchState = computed({
      get: () => props.search,
      set: (value) => {
        clearTimeout(timeout.value)
        timeout.value = setTimeout(() => {
          emit('update:search', value)
        }, 500)
      }
    })

    const navigationDrawerClass = computed(() => {
      return showOmniSearch.value ? 'mt-12' : ''
    })

    watch(
      () => props.search,
      () => {
        searchState.value = props.search
      }
    )

    watch(
      () => props.limit,
      () => {
        limitState.value = props.limit
      }
    )

    return {
      showOmniSearch,
      itemsPerPage,
      timeout,
      limitState,
      searchState,
      drawerVisible,
      navigationDrawerClass
    }
  }
}
</script>

<style lang="scss">
.search-field .v-input__append {
  margin-left: 8px;
}
</style>
