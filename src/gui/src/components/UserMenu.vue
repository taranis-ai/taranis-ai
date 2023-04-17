<template>
  <div class="user-menu cx-user-menu">
    <v-menu close-on-click close-on-content-click offset-y st>
      <template v-slot:activator="{ on }">
        <div class="user-menu-button pl-0 mr-0">
          <v-btn depressed icon tile v-on="on">
            <v-icon color="dark-grey" medium>mdi-account</v-icon>
          </v-btn>
        </div>
      </template>
      <v-list>
        <v-list-item @click="userview">
          <v-list-item-avatar class="">
            <v-icon>mdi-account</v-icon>
          </v-list-item-avatar>
          <v-list-item-content>
            <v-list-item-title>{{ username }}</v-list-item-title>
            <v-list-item-subtitle>{{ organizationName }}</v-list-item-subtitle>
          </v-list-item-content>
        </v-list-item>
        <v-divider></v-divider>

        <v-list-item @click="settings">
          <v-list-item-icon>
            <v-icon>mdi-cog-outline</v-icon>
          </v-list-item-icon>
          <v-list-item-content>
            <v-list-item-title>
              {{ $t('user_menu.settings') }}</v-list-item-title
            >
          </v-list-item-content>
        </v-list-item>

        <v-list-item @click="logout">
          <v-list-item-icon>
            <v-icon>mdi-logout</v-icon>
          </v-list-item-icon>
          <v-list-item-content>
            <v-list-item-title> {{ $t('user_menu.logout') }}</v-list-item-title>
          </v-list-item-content>
        </v-list-item>
      </v-list>
    </v-menu>
  </div>
</template>

<script>
export default {
  name: 'UserMenu',
  data: () => ({
    darkTheme: false
  }),
  computed: {
    username() {
      return this.$store.getters.getUserName
    },
    organizationName() {
      return this.$store.getters.getOrganizationName
    }
  },
  methods: {
    logout() {
      this.$store.dispatch('logout').then(() => {
        window.location.reload()
      })
    },
    settings() {
      this.$router.push({ path: '/user/settings' })
      // this.$root.$emit('show-user-settings')
    },
    userview() {
      this.$router.push({ path: '/user' })
    }
  }
}
</script>
