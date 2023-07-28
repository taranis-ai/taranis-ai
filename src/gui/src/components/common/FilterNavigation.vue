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
        v-model="search_state"
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
        <v-row v-if="!showOmniSearch" class="my-2 mr-0 px-2">
          <v-text-field
            v-model="search_state"
            placeholder="search"
            varint="outlined"
            hide-details
            density="compact"
            prepend-inner-icon="mdi-magnify"
            class="ml-3"
          >
            <template #append>
              <v-btn
                class="mb-1"
                density="compact"
                color="primary"
                icon="mdi-chevron-right"
                @click="showOmniSearch = !showOmniSearch"
              />
            </template>
          </v-text-field>
        </v-row>

        <v-divider class="mt-0 mb-0"></v-divider>

        <!-- scope -->
        <v-row no-gutters class="my-2 mr-0 px-2">
          <v-col cols="6" class="mr-2">
            <v-select
              v-model="limit_state"
              :items="items_per_page"
              label="display"
              variant="solo"
              density="compact"
            ></v-select>
          </v-col>
          <v-col cols="5" class="pb-0">
            <v-select
              v-model="offset_state"
              :items="offsetRange"
              label="offset"
              variant="solo"
              density="compact"
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
import { mapState } from 'pinia'
import { useMainStore } from '@/stores/MainStore'

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
  data: () => ({
    showOmniSearch: false,
    items_per_page: [5, 10, 20, 50, 100],
    timeout: null
  }),
  computed: {
    ...mapState(useMainStore, ['drawerVisible', 'itemCountTotal']),
    limit_state: {
      get() {
        return this.limit
      },
      set(value) {
        this.$emit('update:limit', value)
      }
    },
    offset_state: {
      get() {
        return this.offset
      },
      set(value) {
        this.$emit('update:offset', value)
      }
    },
    search_state: {
      get() {
        return this.search
      },
      set(value) {
        clearTimeout(this.timeout)
        this.timeout = setTimeout(() => {
          this.$nextTick(() => {
            this.$emit('update:search', value)
          })
        }, 500)
      }
    },
    offsetRange() {
      const list = []
      for (let i = 0; i <= this.itemCountTotal; i++) {
        list.push(i)
      }
      return list
    },
    navigation_drawer_class() {
      return this.showOmniSearch ? 'mt-12' : ''
    }
  }
}
</script>
