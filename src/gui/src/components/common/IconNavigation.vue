<template>
  <v-navigation-drawer
    v-if="filteredLinks.length > 0 && drawerVisible"
    color="cx-drawer-bg"
    class="sidebar"
    :width="width"
    :permanent="true"
  >
    <v-list nav>
      <v-list-item
        v-for="link in filteredLinks"
        :key="link.route"
        :to="link.route"
        class="d-flex justify-center"
      >
        <v-list-item-title class="d-flex justify-center">
          <v-icon :icon="link.icon" />
        </v-list-item-title>

        <v-list-item-subtitle class="d-flex text-center text-caption">
          {{ $t(link.title) }}
        </v-list-item-subtitle>
      </v-list-item>
      <v-divider />
    </v-list>
  </v-navigation-drawer>
</template>

<script>
import { mapState } from 'pinia'
import { useMainStore } from '@/stores/MainStore'

export default {
  name: 'IconNavigation',
  props: {
    links: {
      type: Array,
      default: () => []
    },
    width: {
      type: Number,
      default: 142
    }
  },
  data: () => ({}),
  computed: {
    ...mapState(useMainStore, ['drawerVisible', 'user']),

    filteredLinks() {
      return this.links.filter(
        (link) =>
          !link.permission || this.user.permissions.includes(link.permission)
      )
    }
  },
  methods: {}
}
</script>
