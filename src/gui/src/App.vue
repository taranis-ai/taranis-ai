<template>
  <v-app class="grey lighten-2">
    <MainMenu/>

    <router-view name="nav"></router-view>

    <v-main>
      <router-view />
    </v-main>

    <Notification/>
  </v-app>
</template>

<script>
import MainMenu from './components/MainMenu'
import AuthMixin from './services/auth/auth_mixin'
import Notification from './components/common/Notification'
import { mapActions, mapGetters } from 'vuex'

export default {
  name: 'App',
  components: {
    MainMenu,
    Notification
  },
  computed: { },
  mixins: [AuthMixin],
  methods: {
    ...mapActions('dashboard', ['updateStories']),
    ...mapActions('users', ['updateUsers']),
    ...mapActions('assess', ['updateNewsItems']),
    ...mapActions('settings', ['loadUserProfile']),
    ...mapGetters('settings', ['getProfileDarkTheme']),

    connectSSE () { // TODO: unsubscribe
      if (process.env.VUE_APP_TARANIS_NG_CORE_SSE === undefined) {
        return
      }
      this.$sse(
        `${process.env.VUE_APP_TARANIS_NG_CORE_SSE}?jwt=${this.$store.getters.getJWT}`,
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
        this.$store.dispatch('setAuthURLs')
        this.loadUserProfile().then(() => {
          this.$vuetify.theme.dark = this.getProfileDarkTheme()
        })
        this.connectSSE()
      } else {
        if (this.$store.getters.getJWT) {
          this.$store.dispatch('logout')
        }
      }
    }
    // setInterval(
    //   function () {
    //     if (this.isAuthenticated()) {
    //       if (this.needTokenRefresh() === true) {
    //         this.$store.dispatch('refresh').then(() => {
    //           this.reconnectSSE()
    //         })
    //       }
    //     } else {
    //       if (this.$store.getters.getJWT) {
    //         this.$store.dispatch('logout')
    //       }
    //     }
    //   }.bind(this),
    //   5000
    // )
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
