<template>
  <v-container fluid>
    <v-row justify="center" align="center">
      <v-col>
        <v-card>
          <v-card-title>
            {{ username }}
          </v-card-title>
          <v-card-subtitle> User Name </v-card-subtitle>
        </v-card>
      </v-col>
      <v-col>
        <v-card>
          <v-card-title>
            {{ organizationName }}
          </v-card-title>
          <v-card-subtitle> Organization </v-card-subtitle>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { useMainStore } from '@/stores/MainStore'
import { mapState } from 'pinia'

export default {
  name: 'UserView',
  data: () => ({
    expanded: false
  }),
  computed: {
    ...mapState(useMainStore, ['user']),
    username() {
      return this.user.name || ''
    },
    organizationName() {
      return this.user.organization_name || ''
    }
  }
}
</script>
