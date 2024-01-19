<template>
  <NewsItemEdit :news-item-prop="news_item" />
</template>

<script>
import NewsItemEdit from '@/components/assess/NewsItemEdit.vue'
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAssessStore } from '@/stores/AssessStore'


export default {
  name: 'NewsItemEditView',
  components: {
    NewsItemEdit
  },
  setup() {
    const route = useRoute()
    const assessStore = useAssessStore()

    const news_item = computed(() => {
      return assessStore.newsItems.items.find(
        (item) => item.id == route.params.id
      )
    })

    return {
      news_item
    }
  }
}
</script>
