<template>
  <div>
    <v-app-bar
      clipped-left
      :elevation="2"
      app
      class="mt-12"
      v-if="!drawerVisible || showOmniSearch"
    >
      <v-btn
        style="margin-left: 230px"
        icon
        @click="showOmniSearch = !showOmniSearch"
        color="primary"
        v-if="showOmniSearch && drawerVisible"
      >
        <v-icon left> mdi-chevron-left </v-icon>
      </v-btn>
      <v-text-field
        v-model="search_state"
        label="search"
        outlined
        dense
        hide-details
        prepend-icon="mdi-magnify"
        class="mr-5 ml-5"
      ></v-text-field>
      <slot name="appbar"></slot>
    </v-app-bar>
    <v-navigation-drawer
      clipped
      app
      color="cx-drawer-bg"
      class="sidebar"
      :width="300"
      v-if="drawerVisible"
    >
      <v-container class="pa-0 ma-0">
        <!-- search -->
        <v-row class="my-2 mr-0 px-2" v-if="!showOmniSearch">
          <v-text-field
            v-model="search_state"
            label="search"
            outlined
            dense
            hide-details
          >
            <template #append>
              <v-btn
                class="mb-1"
                icon
                @click="showOmniSearch = !showOmniSearch"
                color="primary"
              >
                <v-icon> mdi-chevron-right </v-icon>
              </v-btn>
            </template>
          </v-text-field>
        </v-row>

        <v-divider class="mt-0 mb-0"></v-divider>

        <!-- scope -->
        <v-row class="my-2 mr-0 px-2">
          <v-col cols="6" class="pb-0">
            <h4>Display</h4>
            <v-select
              v-model="limit_state"
              :items="items_per_page"
              label="display"
              :hide-details="true"
              solo
              clearable
              dense
            ></v-select>
          </v-col>
          <v-col cols="6" class="pb-0">
            <h4>Offset</h4>
            <v-select
              v-model="offset_state"
              :items="offsetRange"
              :hide-details="true"
              label="offset"
              solo
              clearable
              dense
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
import { mapState, mapGetters } from 'vuex'

export default {
  name: 'FilterNavigation',
  data: () => ({
    showOmniSearch: false,
    items_per_page: [5, 15, 25, 50, 100]
  }),
  emits: ['update:search', 'update:limit', 'update:offset'],
  props: {
    search: {
      type: String
    },
    limit: {
      type: Number
    },
    offset: {
      type: Number
    }
  },
  computed: {
    ...mapState(['drawerVisible']),
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
        this.$emit('update:search', value)
      }
    },
    offsetRange() {
      const list = []
      for (let i = 0; i <= this.getItemCount().total; i++) {
        list.push(i)
      }
      return list
    },
    navigation_drawer_class() {
      return this.showOmniSearch ? 'mt-12' : ''
    }
  },
  methods: {
    ...mapGetters(['getItemCount'])
  }
}
</script>
