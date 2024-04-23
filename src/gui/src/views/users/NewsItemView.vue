<template>
  <v-container v-if="news_item" fluid>
    <card-news-item :news-item="news_item" :detail-view="true" />
  </v-container>
  <not-found-card v-else :item-id="itemId" item-type="News Item" />
</template>

<script>
import { ref, onMounted } from 'vue'
import { getNewsItem } from '@/api/assess'
import NotFoundCard from '@/components/common/NotFoundCard.vue'
import CardNewsItem from '@/components/assess/CardNewsItem.vue'

export default {
  name: 'NewsItemView',
  components: {
    CardNewsItem,
    NotFoundCard
  },
  props: {
    itemId: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const news_item = ref(null)
    onMounted(async () => {
      news_item.value = await loadNewsItem()
    })

    async function loadNewsItem() {
      if (props.itemId) {
        const response = await getNewsItem(props.itemId)
        return response.data
      }
    }

    return {
      news_item,
      loadNewsItem
    }
  }
}
</script>
