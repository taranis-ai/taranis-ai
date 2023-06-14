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
            {{ $d(published_date, 'long') }}
          </v-col>
          <v-col v-else class="py-0">
            {{ $d(collected_date, 'long') }}
          </v-col>
        </v-row>
        <v-row>
          <v-col style="max-width: 110px" class="py-0">
            <strong>{{ $t('assess.source') }}:</strong>
          </v-col>
          <v-col class="py-0">
            {{ source?.name }}
          </v-col>
        </v-row>
        <v-row>
          <v-col style="max-width: 110px" class="py-0">
            <strong>{{ $t('assess.author') }}:</strong>
          </v-col>
          <v-col class="py-0">
            {{ author }}
          </v-col>
        </v-row>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { getCleanHostname } from '@/utils/helpers.js'
import { computed } from 'vue'

export default {
  name: 'NewsMetaInfo',
  props: {
    newsItem: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const published_date = computed(() => {
      return props.newsItem.news_item_data.published
        ? new Date(props.newsItem.news_item_data.published)
        : null
    })

    const published_date_outdated = computed(() => {
      const pub_date = published_date.value
      if (!pub_date) {
        return false
      }
      const oneWeekAgo = new Date()
      oneWeekAgo.setDate(oneWeekAgo.getDate() - 7)
      return oneWeekAgo > pub_date
    })

    const author = computed(() => {
      return props.newsItem.news_item_data?.author
    })

    const source = computed(() => {
      return props.newsItem.news_item_data
        ? {
            name: getCleanHostname(props.newsItem.news_item_data.source),
            link: props.newsItem.news_item_data.link,
            type: props.newsItem.news_item_data.osint_source_id
          }
        : null
    })

    const collected_date = computed(() => {
      return props.newsItem.news_item_data?.collected
        ? new Date(props.newsItem.news_item_data.collected)
        : null
    })

    return {
      published_date,
      published_date_outdated,
      author,
      source,
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
