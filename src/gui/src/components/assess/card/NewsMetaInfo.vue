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
        <v-row>
          <v-col style="max-width: 110px" class="py-0">
            <strong>{{ $t('assess.source') }}:</strong>
          </v-col>
          <v-col class="py-0" @click.stop>
            <a :href="source?.link" target="_blank">
              {{ source?.name }}
            </a>
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
import { useI18n } from 'vue-i18n'

export default {
  name: 'NewsMetaInfo',
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
        ? d(new Date(props.newsItem.news_item_data.collected), 'long')
        : null
    })

    return {
      published_date,
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
