<template>
  <ViewLayout>
    <template v-slot:panel> </template>
    <template v-slot:content>
      <DashboardContent />
    </template>
  </ViewLayout>
</template>

<script>
import ViewLayout from '@/components/layouts/ViewLayout'
import DashboardContent from '@/components/dashboard/DashboardContent'
import { mapActions } from 'vuex'

export default {
  name: 'DashboardView',
  components: {
    ViewLayout,
    DashboardContent
  },
  methods: {
    ...mapActions('dashboard', ['unselectAllTopics']),
    ...mapActions('assess', ['deselectAllNewsItems']),
    ...mapActions('filter', ['resetNewsItemsFilter', 'resetTopicsFilter']),
  },
  mounted () {
    this.unselectAllTopics()
    this.resetTopicsFilter()
    this.deselectAllNewsItems()
    this.resetNewsItemsFilter()
  }
}
</script>
