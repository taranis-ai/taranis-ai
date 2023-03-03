<template>
  <div>
    {{ published_dates }}
  </div>
</template>

<script>
import { getNewsItemsAggregates } from '@/api/assess'

export default {
  name: 'TrendingCard',
  props: {
    cluster: { type: String }
  },
  data: function () {
    return {
      stories: {},
      published_dates: [],
      size: 0
    }
  },
  mounted() {
    const filter = { tags: this.cluster }
    getNewsItemsAggregates(filter).then((response) => {
      this.stories = response.data.items
      this.size = response.data.total_count
      this.published_dates = this.stories.flatMap(({ news_items }) =>
        news_items.map(({ news_item_data }) => news_item_data.published)
      )
    })
  }
}
</script>
