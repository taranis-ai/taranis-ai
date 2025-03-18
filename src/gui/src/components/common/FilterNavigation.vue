<template>
  <v-navigation-drawer
    v-model="drawerVisible"
    color="cx-drawer-bg"
    :permanent="true"
    :width="300"
    data-testid="filter-navigation-div"
  >
    <v-container class="pa-0 ma-0">
      <!-- search -->
      <v-row class="mx-2 my-4 px-2">
        <v-text-field
          v-model="searchState"
          placeholder="search"
          variant="outlined"
          hide-details
          density="compact"
          prepend-inner-icon="mdi-magnify"
          class="search-field"
        />
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
          menu-icon="mdi-chevron-down"
        />
      </v-row>

      <slot name="navdrawer"></slot>
      <v-row class="ml-0 mr-0">
        <v-col cols="12">
          <v-btn
            block
            variant="plain"
            prepend-icon="mdi-keyboard-outline"
            text="Show Hotkeys"
            @click="hotkeyDialogVisible = !hotkeyDialogVisible"
          />
        </v-col>
      </v-row>
    </v-container>
  </v-navigation-drawer>
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
    const itemsPerPage = [20, 40, 100, 200, 400]
    const timeout = ref(null)
    const store = useMainStore()

    const { drawerVisible, hotkeyDialogVisible } = storeToRefs(store)

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

    watch(
      () => props.search,
      () => {
        if (props.search === '') {
          searchState.value = undefined
        } else {
          searchState.value = props.search
        }
      }
    )

    watch(
      () => props.limit,
      () => {
        limitState.value = props.limit
      }
    )

    return {
      itemsPerPage,
      limitState,
      searchState,
      drawerVisible,
      hotkeyDialogVisible
    }
  }
}
</script>
