<template>
  <ViewLayout>
    <template v-slot:panel> </template>
    <template v-slot:content>
    </template>
  </ViewLayout>
</template>

<script>
import ViewLayout from '@/components/layouts/ViewLayout'
import { mapActions } from 'vuex'

export default {
  name: 'DashboardView',
  components: {
    ViewLayout
  },
  methods: {
    ...mapActions('dashboard', ['unselectAllStories']),
    ...mapActions('assess', ['deselectAllNewsItems']),
    ...mapActions('filter', ['resetNewsItemsFilter']),
    ...mapActions(['setDrawer'])
  },
  mounted () {
    this.unselectAllStories()
    this.deselectAllNewsItems()
    this.resetNewsItemsFilter()
  },
  activated () {
    console.log('activated DashboardView')
    this.setDrawer(false)
  },
  deactivated () {
    console.log('deactivated DashboardView')
    this.setDrawer(true)
  }
}
</script>
