<template>
  <v-container fluid>
    <v-row justify="center" align="center">
      <v-col>
        <v-card :title="username" subtitle="User Name" />
      </v-col>
      <v-col>
        <v-card>
          <v-card-title>
            {{ name }}
          </v-card-title>
          <v-card-subtitle> Name </v-card-subtitle>
        </v-card>
      </v-col>
      <v-col>
        <v-card>
          <v-card-title>
            {{ role_list }}
          </v-card-title>
          <v-card-subtitle> Roles </v-card-subtitle>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { useUserStore } from '@/stores/UserStore'
import { storeToRefs } from 'pinia'

export default {
  name: 'UserView',
  setup() {
    const { name, username, roles } = storeToRefs(useUserStore())

    const role_list = roles.value.map((role) => role.name).join(', ')

    return {
      username,
      role_list,
      name
    }
  }
}
</script>
