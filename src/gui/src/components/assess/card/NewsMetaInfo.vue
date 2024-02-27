<template>
  <v-container column class="pa-0 pb-1">
    <v-row v-if="newsItem">
      <v-col>
        <v-row>
          <v-col class="info-title py-0">
            <strong v-if="published_date">{{ $t('assess.published') }}:</strong>
            <strong v-else>{{ $t('assess.collected') }}:</strong>
          </v-col>
          <v-col v-if="published_date" class="py-0">
            {{ published_date }}
          </v-col>
          <v-col v-else class="py-0">
            {{ collected_date }}
          </v-col>
        </v-row>
        <article-info :news-item-data="newsItem.news_item_data" />
        <source-info :news-item-data="newsItem.news_item_data" />
        <author-info :news-item-data="newsItem.news_item_data" />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import ArticleInfo from '@/components/assess/card/ArticleInfo.vue'
import SourceInfo from '@/components/assess/card/SourceInfo.vue'
import AuthorInfo from '@/components/assess/card/AuthorInfo.vue'

export default {
  name: 'NewsMetaInfo',
  components: { ArticleInfo, SourceInfo, AuthorInfo },
  props: {
    newsItem: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const { d } = useI18n()

    const published_date = computed(() => {
      return props.newsItem.news_item_data?.published
        ? d(new Date(props.newsItem.news_item_data.published), 'long')
        : null
    })

    const author = computed(() => {
      return props.newsItem.news_item_data?.author
    })

    const collected_date = computed(() => {
      return props.newsItem.news_item_data?.collected
        ? d(new Date(props.newsItem.news_item_data.collected), 'long')
        : null
    })

    return {
      published_date,
      author,
      collected_date
    }
  }
}
</script>

<style scoped>
.info-title {
  max-width: 110px;
}
</style>
