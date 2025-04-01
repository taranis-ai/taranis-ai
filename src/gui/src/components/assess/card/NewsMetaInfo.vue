<template>
  <table class="newsitem-meta-info">
    <tbody>
      <tr>
        <td v-if="!compactView" class="py-0 news-item-title">
          <strong v-if="published_date">{{ $t('assess.published') }}:</strong>
          <strong v-else>{{ $t('assess.collected') }}:</strong>
        </td>
        <td v-if="published_date" class="py-0">
          {{ published_date }}
        </td>
        <td v-else class="py-0">
          {{ collected_date }}
        </td>
      </tr>
      <article-info :news-item="newsItem" />
      <author-info :news-item="newsItem" />
      <sentiment-info :news-item="newsItem" />
    </tbody>
  </table>
</template>

<script>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import ArticleInfo from '@/components/assess/card/ArticleInfo.vue'
import AuthorInfo from '@/components/assess/card/AuthorInfo.vue'
import SentimentInfo from '@/components/assess/card/SentimentInfo.vue'
import { storeToRefs } from 'pinia'
import { useFilterStore } from '@/stores/FilterStore'

export default {
  name: 'NewsMetaInfo',
  components: {
    ArticleInfo,
    AuthorInfo,
    SentimentInfo
  },
  props: {
    newsItem: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const { d } = useI18n()

    const published_date = computed(() => {
      return props.newsItem?.published
        ? d(new Date(props.newsItem.published), 'long')
        : null
    })

    const { compactView } = storeToRefs(useFilterStore())

    const author = computed(() => {
      return props.newsItem?.author
    })

    const collected_date = computed(() => {
      return props.newsItem?.collected
        ? d(new Date(props.newsItem.collected), 'long')
        : null
    })

    return {
      published_date,
      author,
      collected_date,
      compactView
    }
  }
}
</script>

<style scoped>
.newsitem-meta-info {
  word-wrap: anywhere;
  width: 100%;
}

.newsitem-meta-info tr td {
  vertical-align: top;
}
.newsitem-meta-info tr td:first-child {
  padding-right: 10px;
}
</style>
