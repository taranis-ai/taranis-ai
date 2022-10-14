<template>
    <v-container fluid>
      <v-row justify="center" align="center">
        <v-col>
          {{ username }}
        </v-col>
        <v-col>
          {{ organizationName }}
        </v-col>
      </v-row>
    </v-container>
</template>

<script>
export default {
  name: 'UserView',
  data: () => ({
  }),
  computed: {
    username () {
      return this.$store.getters.getUserName
    },
    organizationName () {
      return this.$store.getters.getOrganizationName
    }
  },
  methods: {

  }
}
</script>
