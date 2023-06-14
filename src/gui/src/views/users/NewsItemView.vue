<template>
  <v-container v-if="news_item" fluid style="min-height: 100vh">
    <card-news-item :news-item="news_item" :detail-view="true" />
  </v-container>
</template>

<script>
import { getNewsItem } from '@/api/assess'
import CardNewsItem from '@/components/assess/CardNewsItem.vue'

export default {
  name: 'NewsItemView',
  components: {
    CardNewsItem
  },
  data: () => ({
    news_item: {}
  }),
  async created() {
    this.news_item = await this.loadNewsItem()
  },
  methods: {
    async loadNewsItem() {
      if (this.$route.params.id) {
        return await getNewsItem(this.$route.params.id).then((response) => {
          return response.data
        })
      }
    }
  }
}
</script>
