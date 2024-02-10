<template>
  <v-container fluid>
    <v-row justify="center" align="center">
      <v-col>
        <v-card :title="username" subtitle="User Name" />
      </v-col>
      <v-col>
        <v-card :title="organizationName" subtitle="Organization" />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { computed } from 'vue'
import { useMainStore } from '@/stores/MainStore'

export default {
  name: 'UserView',
  setup() {
    const mainStore = useMainStore()

    const username = computed(() => {
      return mainStore.user.name || ''
    })

    const organizationName = computed(() => {
      return mainStore.user.organization_name || ''
    })

    return {
      username,
      organizationName
    }
  }
}
</script>
