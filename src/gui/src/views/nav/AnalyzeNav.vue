<template>
  <icon-navigation
    v-if="links.length > 0"
    :links="links"
    icon="mdi-google-circles-communities"
    :width="80"
  />
</template>

<script>
import IconNavigation from '@/components/common/IconNavigation'
import { mapActions, mapGetters } from 'vuex'

export default {
  name: 'AnalyzeNav',
  components: {
    IconNavigation
  },
  data: () => ({
    groups: [],
    links: []
  }),
  methods: {
    ...mapGetters('analyze', ['getReportItemGroups']),
    ...mapActions('analyze', ['loadReportItemGroups'])
  },
  mounted() {
    this.links = [
      {
        icon: 'mdi-home-circle-outline',
        title: this.$t('nav_menu.local'),
        route: '/analyze/local'
      }
    ]

    this.loadReportItemGroups()
      .then(() => {
        this.groups = this.getReportItemGroups()
        if (this.groups.length < 1) {
          console.debug('NO GROUPS')
          return
        }

        this.links = [
          ...this.links,
          ...this.groups.map((group) => ({
            icon: 'mdi-arrow-down-bold-circle-outline',
            title: group,
            route: `/analyze/group/${group.replace(/ /g, '-')}`
          }))
        ]
      })
      .catch(() => {})
  }
}
</script>
