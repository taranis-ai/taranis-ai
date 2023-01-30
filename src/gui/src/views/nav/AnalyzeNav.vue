<template>
  <Navigation
    v-if="links.length > 0"
    :links = "links"
    :icon  = "'mdi-google-circles-communities'"
    :width = "80"
  />
</template>

<script>
import Navigation from '../../components/common/Navigation'
import { mapActions, mapGetters } from 'vuex'

export default {
  name: 'AnalyzeNav',
  components: {
    Navigation
  },
  data: () => ({
    groups: [],
    links: []
  }),
  methods: {
    ...mapGetters('analyze', ['getReportItemGroups']),
    ...mapActions('analyze', ['loadReportItemGroups'])
  },
  mounted () {
    this.links = [{
      icon: 'mdi-home-circle-outline',
      title: this.$t('nav_menu.local'),
      route: '/analyze/local'
    }]

    this.loadReportItemGroups().then(() => {
      this.groups = this.getReportItemGroups()

      this.links = [...this.links, ...this.groups.map(group => ({
        icon: 'mdi-arrow-down-bold-circle-outline',
        title: group,
        route: `/analyze/group/${group.replace(/ /g, '-')}`
      }))]
    })
  }
}
</script>
