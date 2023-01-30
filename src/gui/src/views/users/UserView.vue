<template>
  <v-container fluid>
    <v-row justify="center" align="center">
      <v-col>
        <v-card>
          <v-card-title>
            {{ user.name }}
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
export default {
  name: 'UserView',
  data: () => ({
    expanded: false
  }),
  computed: {
    user() {
      return this.$store.getters.getUser
    },
    organizationName() {
      return this.$store.getters.getOrganizationName
    }
  },
  methods: {}
}
</script>
