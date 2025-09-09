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
      <sentiment-info
        :sentiment-category="sentiment_category"
        :sentiment-score="sentiment_score"
        :compact-view="compactView"
      />
      <cybersecurity-status-info
        :cybersecurity-status="cybersecurity_status"
        :cybersecurity-score="cybersecurity_score"
        :compact-view="compactView"
      />
    </tbody>
  </table>
</template>

<script>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import ArticleInfo from '@/components/assess/card/ArticleInfo.vue'
import AuthorInfo from '@/components/assess/card/AuthorInfo.vue'
import SentimentInfo from '@/components/assess/card/SentimentInfo.vue'
import CybersecurityStatusInfo from '@/components/assess/card/CybersecurityStatusInfo.vue'
import { storeToRefs } from 'pinia'
import { useFilterStore } from '@/stores/FilterStore'

export default {
  name: 'NewsMetaInfo',
  components: {
    ArticleInfo,
    AuthorInfo,
    SentimentInfo,
    CybersecurityStatusInfo
  },
  props: {
    newsItem: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const { d } = useI18n()
    const { compactView } = storeToRefs(useFilterStore())

    const published_date = computed(() => {
      return props.newsItem?.published
        ? d(new Date(props.newsItem.published), 'long')
        : null
    })

    const collected_date = computed(() => {
      return props.newsItem?.collected
        ? d(new Date(props.newsItem.collected), 'long')
        : null
    })

    const sentiment_category = computed(() => {
      return props.newsItem?.attributes?.find(
        (attr) => attr.key === 'sentiment_category'
      )?.value
    })

    const sentiment_score = computed(() => {
      const score = props.newsItem?.attributes?.find(
        (attr) => attr.key === 'sentiment_score'
      )?.value
      return score !== undefined ? parseFloat(score) : NaN
    })

    const cybersecurity_status = computed(() => {
      const attrs = props.newsItem?.attributes ?? []

      const human = attrs.find((a) => a.key === 'cybersecurity_human')?.value
      const bot = attrs.find((a) => a.key === 'cybersecurity_bot')?.value
      const chosen = human ?? bot

      if (chosen === undefined || chosen === null || chosen === '') return null
      const v = String(chosen).trim().toLowerCase()

      // normalize a few possible forms
      if (v === 'yes' || v === 'true' || v === '1') return 'yes'
      if (v === 'no' || v === 'false' || v === '0') return 'no'

      return null
    })

    const cybersecurity_score = computed(() => {
      const attrs = props.newsItem?.attributes ?? []

      const hasHuman = attrs.some((a) => a.key === 'cybersecurity_human')
      const scoreKey = hasHuman
        ? 'cybersecurity_human_score'
        : 'cybersecurity_bot_score'
      const raw = attrs.find((a) => a.key === scoreKey)?.value
      if (raw === undefined || raw === null || raw === '') return undefined
      const n = typeof raw === 'number' ? raw : parseFloat(raw)
      return Number.isFinite(n) ? n : undefined
    })

    return {
      published_date,
      collected_date,
      compactView,
      sentiment_category,
      sentiment_score,
      cybersecurity_status,
      cybersecurity_score
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
