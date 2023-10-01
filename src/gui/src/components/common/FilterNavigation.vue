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
        <v-row v-if="!showOmniSearch" class="mx-2 my-4 px-2">
          <v-text-field
            v-model="search_state"
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
              v-model="limit_state"
              :items="items_per_page"
              label="display"
              variant="outlined"
              density="compact"
              hide-details
            ></v-select>
          </v-col>
          <v-col cols="6" class="pl-1">
            <v-select
              v-model="offset_state"
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

<style lang="scss">
.search-field .v-input__append {
  margin-left: 8px;
}
</style>
