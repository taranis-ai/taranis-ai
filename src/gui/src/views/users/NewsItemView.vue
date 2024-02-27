<template>
  <v-container v-if="news_item" fluid style="min-height: 100vh">
    <card-news-item :news-item="news_item" :detail-view="true" />
  </v-container>
  <not-found-card v-else :item-id="news_item_id" item-type="News Item" />
</template>

<script>
import { ref, onMounted } from 'vue'
import { getNewsItem } from '@/api/assess'
import { useRoute } from 'vue-router'
import NotFoundCard from '@/components/common/NotFoundCard.vue'
import CardNewsItem from '@/components/assess/CardNewsItem.vue'

export default {
  name: 'NewsItemView',
  components: {
    CardNewsItem,
    NotFoundCard
  },
  setup() {
    const news_item = ref(null)
    const route = useRoute()
    const news_item_id = route.params.id

    onMounted(async () => {
      news_item.value = await loadNewsItem()
    })

    async function loadNewsItem() {
      if (news_item_id) {
        const response = await getNewsItem(news_item_id)
        return response.data
      }
    }

    return {
      news_item,
      news_item_id,
      loadNewsItem
    }
  }
}
</script>
