<template>
    <Navigation
            :links="links"
            :icon="'mdi-location-enter'"
    />
</template>

<script>
import Navigation from '../../components/common/Navigation'
import AuthMixin from '@/services/auth/auth_mixin'
import Permissions from '@/services/auth/permissions'

export default {
  name: 'EnterNav',
  components: {
    Navigation
  },
  mixins: [AuthMixin],
  data: () => ({
    groups: [],
    links: []
  }),
  mounted () {
    if (this.checkPermission(Permissions.ASSESS_CREATE)) {
      this.$store.dispatch('getManualOSINTSources')
        .then(() => {
          this.groups = this.$store.getters.getManualOSINTSources
          for (let i = 0; i < this.groups.length; i++) {
            this.links.push({
              icon: 'mdi-animation-outline',
              title: this.groups[i].name,
              route: '/enter/source/' + this.groups[i].id
            })
          }

          if (!window.location.pathname.includes('/enter/') && this.links.length > 0) {
            this.$router.push(this.links[0].route)
          }
        })
    }
  }
}
</script>
