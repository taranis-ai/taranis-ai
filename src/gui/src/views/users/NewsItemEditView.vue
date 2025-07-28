<template>
  <NewsItemEdit v-if="news_item" :news-item-prop="news_item" />
  <not-found-card v-else :item-id="storyId" item-type="Story" />
</template>

<script>
import NewsItemEdit from '@/components/assess/NewsItemEdit.vue'
import NotFoundCard from '@/components/common/NotFoundCard.vue'

import { ref, onBeforeMount } from 'vue'
import { getNewsItem } from '@/api/assess'

export default {
  name: 'NewsItemEditView',
  components: {
    NewsItemEdit,
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

    onBeforeMount(async () => {
      const response = await getNewsItem(props.itemId)
      news_item.value = response.data
    })

    return {
      news_item
    }
  }
}
</script>
