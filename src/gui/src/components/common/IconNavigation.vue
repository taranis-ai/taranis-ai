<template>
  <v-navigation-drawer
    v-model="drawerVisible"
    color="cx-drawer-bg"
    class="sidebar"
    :width="300"
    :permanent="true"
  >
    <v-list nav class="ma-2 config-menu">
      <div v-for="link in filteredLinks" :key="link.route">
        <v-list-item
          :to="link.route"
          class="d-flex mb-1"
          active-class="bg-primary"
          density="compact"
        >
          <v-icon
            v-if="link.deprecated"
            color="yellow-accent-4"
            icon="mdi-alert-outline"
            class="mr-5"
          />
          <v-icon :icon="link.icon" class="mr-3" />
          {{ $t(link.title) }}
        </v-list-item>

        <v-divider v-if="link.divider" />
      </div>
    </v-list>
  </v-navigation-drawer>
</template>

<script>
import { computed } from 'vue'
import { useMainStore } from '@/stores/MainStore'
import { useUserStore } from '@/stores/UserStore'
import { storeToRefs } from 'pinia'

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
    const userStore = useUserStore()
    const { drawerVisible } = storeToRefs(useMainStore())

    const filteredLinks = computed(() => {
      return props.links.filter(
        (link) =>
          !link.permission || userStore.permissions.includes(link.permission)
      )
    })

    return {
      drawerVisible,
      filteredLinks
    }
  }
}
</script>

<style scoped lang="scss">
.config-menu i {
  color: rgb(var(--v-theme-primary));
}
.config-menu .bg-primary i {
  color: white;
}
</style>
