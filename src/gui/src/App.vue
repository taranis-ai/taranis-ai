<template>
  <v-app class="grey lighten-2">
    <!-- class="taranis" -->

    <MainMenu v-if="isAuthenticated()" />

    <v-navigation-drawer
      clipped
      v-model="visible"
      width="300px"
      app
      color="cx-drawer-bg"
      v-if="isAuthenticated()"
      class="sidebar"
      style="max-height: 100% !important; height: calc(100vh - 48px) !important"
    >
      <router-view name="nav"></router-view>
    </v-navigation-drawer>

    <v-main>
      <router-view />
    </v-main>

    <Notification v-if="isAuthenticated()" />
  </v-app>
</template>

<script>
import MainMenu from './components/MainMenu'
import AuthMixin from './services/auth/auth_mixin'
import Notification from './components/common/Notification'
import { mapState, mapGetters, mapActions } from 'vuex'

export default {
  name: 'App',
  components: {
    MainMenu,
    Notification
  },
  data: () => ({
    visible: null
  }),
  mixins: [AuthMixin],
  methods: {
    ...mapActions('dashboard', ['updateTopics']),
    ...mapActions('users', ['updateUsers']),
    ...mapActions('assess', ['updateNewsItems',]),

    connectSSE () { // TODO: unsubscribe
      this.$sse(
        (typeof process.env.VUE_APP_TARANIS_NG_CORE_SSE === 'undefined'
          ? '$VUE_APP_TARANIS_NG_CORE_SSE'
          : process.env.VUE_APP_TARANIS_NG_CORE_SSE) +
          '?jwt=' +
          this.$store.getters.getJWT,
        { format: 'json' }
      ).then((sse) => {
        sse.subscribe('news-items-updated', (data) => {
          this.$root.$emit('news-items-updated', data)
        })
        sse.subscribe('report-items-updated', (data) => {
          this.$root.$emit('report-items-updated', data)
        })
        sse.subscribe('report-item-updated', (data) => {
          this.$root.$emit('report-item-updated', data)
        })
        sse.subscribe('report-item-locked', (data) => {
          this.$root.$emit('report-item-locked', data)
        })
        sse.subscribe('report-item-unlocked', (data) => {
          this.$root.$emit('report-item-unlocked', data)
        })
      })
    },

    reconnectSSE () {
      if (this.sseConnection !== null) {
        this.sseConnection.close()
        this.sseConnection = null
      }
      this.connectSSE()
    }
  },
  updated () {
    this.$root.$emit('app-updated')

  },
  mounted () {
    if (this.$cookies.isKey('jwt')) {
      this.$store.dispatch('setToken', this.$cookies.get('jwt')).then(() => {
        this.$cookies.remove('jwt')
        this.connectSSE()
      })
    }

    if (localStorage.ACCESS_TOKEN) {
      if (this.isAuthenticated()) {
        this.$store.dispatch('getUserProfile').then(() => {
          this.$vuetify.theme.dark = this.$store.getters.getProfileDarkTheme
        })
        this.connectSSE()
      } else {
        if (this.$store.getters.getJWT) {
          this.logout()
        }
      }
    }

    setInterval(
      function () {
        if (this.isAuthenticated()) {
          if (this.needTokenRefresh() === true) {
            this.$store.dispatch('refresh').then(() => {
              this.reconnectSSE()
            })
          }
        } else {
          if (this.$store.getters.getJWT) {
            this.logout()
          }
        }
      }.bind(this),
      5000
    )

    this.$root.$on('nav-clicked', () => {
      this.visible = !this.visible
    })
  },
  created () {

  }
}
</script>

<style src="./assets/common.css"></style>
<style src="./assets/centralize.css"></style>

<style lang="scss">
@import '@/styles/variables.scss';
@import '@/styles/awake.scss';
</style>