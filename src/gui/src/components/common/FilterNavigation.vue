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
                <v-icon size="x-large" class="pa-0" icon="mdi-chevron-right">
                </v-icon>
              </v-btn>
            </template>
          </v-text-field>
        </v-row>

        <v-divider class="my-2"></v-divider>

        <!-- scope -->
        <v-row no-gutters class="ma-2 my-4 px-2">
          <v-col cols="6" class="pr-1">
            <v-select
              v-model="limitState"
              :items="itemsPerPage"
              label="display"
              variant="outlined"
              density="compact"
              hide-details
            ></v-select>
          </v-col>
          <v-col cols="6" class="pl-1">
            <v-select
              v-model="offsetState"
              :items="offsetRange"
              label="offset"
              variant="outlined"
              density="compact"
              hide-details
            ></v-select>
          </v-col>
        </v-row>

        <v-divider class="mt-0 mb-0"></v-divider>

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
    limit: {
      type: Number,
      default: 20
    },
    offset: {
      type: Number,
      default: 0
    }
  },
  emits: ['update:search', 'update:limit', 'update:offset'],
  setup(props, { emit }) {
    const showOmniSearch = ref(false)
    const itemsPerPage = [5, 10, 20, 50, 100]
    const timeout = ref(null)
    const store = useMainStore()

    const { drawerVisible, itemCountTotal } = storeToRefs(store)

    const limitState = computed({
      get: () => props.limit,
      set: (value) => emit('update:limit', value)
    })

    const offsetState = computed({
      get: () => props.offset,
      set: (value) => emit('update:offset', value)
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

    const offsetRange = computed(() =>
      Array.from({ length: itemCountTotal.value + 1 }, (_, i) => i)
    )

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

    watch(
      () => props.offset,
      () => {
        offsetState.value = props.offset
      }
    )

    return {
      showOmniSearch,
      itemsPerPage,
      timeout,
      limitState,
      offsetState,
      searchState,
      offsetRange,
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
