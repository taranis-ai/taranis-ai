<template>
  <v-navigation-drawer
    v-if="filteredLinks.length > 0 && drawerVisible"
    color="cx-drawer-bg"
    class="sidebar"
    :width="width"
    :permanent="true"
  >
    <v-list nav>
      <div v-for="link in filteredLinks" :key="link.route">
        <v-list-item :to="link.route" class="d-flex justify-center">
          <v-list-item-title class="d-flex justify-center">
            <v-icon
              v-if="link.deprecated"
              color="yellow-accent-4"
              icon="mdi-alert-outline"
            />
            <v-icon :icon="link.icon" />
          </v-list-item-title>

          <v-list-item-subtitle class="d-flex text-center text-caption">
            {{ $t(link.title) }}
          </v-list-item-subtitle>
        </v-list-item>
        <v-divider v-if="link.divider" />
      </div>
    </v-list>
  </v-navigation-drawer>
</template>

<script>
import { computed } from 'vue'
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
  setup(props) {
    const { drawerVisible, user } = useMainStore()

    const filteredLinks = computed(() => {
      return props.links.filter(
        (link) => !link.permission || user.permissions.includes(link.permission)
      )
    })

    return {
      drawerVisible,
      filteredLinks
    }
  }
}
</script>
