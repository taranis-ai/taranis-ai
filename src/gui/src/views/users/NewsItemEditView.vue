<template>
  <NewsItemEdit v-if="news_item" :news-item-prop="news_item" />
</template>

<script>
import NewsItemEdit from '@/components/assess/NewsItemEdit.vue'
import { ref, onBeforeMount } from 'vue'
import { getNewsItem } from '@/api/assess'

export default {
  name: 'NewsItemEditView',
  components: {
    NewsItemEdit
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
      news_item.value.id = response.data.id
    })

    return {
      news_item
    }
  }
}
</script>
