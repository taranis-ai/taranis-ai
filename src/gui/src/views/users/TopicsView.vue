<template>
  <ViewLayout>
    <template v-slot:panel> </template>
    <template v-slot:content>
      <TopicsContent />
    </template>
  </ViewLayout>
</template>

<script>
import ViewLayout from '@/components/layouts/ViewLayout'
import TopicsContent from '@/components/topics/TopicsContent'
import { mapActions } from 'vuex'

export default {
  name: 'TopicsView',
  components: {
    ViewLayout,
    TopicsContent
  },
  methods: {
    ...mapActions('dashboard', ['unselectAllTopics']),
    ...mapActions('assess', ['deselectAllNewsItems']),
    ...mapActions('filter', ['resetNewsItemsFilter', 'resetTopicsFilter'])
  },
  mounted () {
    this.unselectAllTopics()
    this.resetTopicsFilter()
    this.deselectAllNewsItems()
    this.resetNewsItemsFilter()
  }
}
</script>
