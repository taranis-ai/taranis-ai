<template>
  <div>
    <v-row class="news-item-meta-infos">
      <v-col class="news-item-meta-infos-label">
        <strong>{{ $t('assess.published') }}:</strong>
      </v-col>
      <v-col>
        <span :class="published_date_outdated ? 'red--text' : ''">
          {{ $d(getPublishedDate(), 'long') }}
        </span>
        <v-icon v-if="published_date_outdated" small color="red"
          >mdi-alert</v-icon
        >
      </v-col>
    </v-row>
    <v-row class="news-item-meta-infos">
      <v-col class="news-item-meta-infos-label">
        <strong>{{ $t('assess.collected') }}:</strong>
      </v-col>
      <v-col>
        {{ $d(getCollectedDate(), 'long') }}
      </v-col>
    </v-row>
    <v-row class="news-item-meta-infos">
      <v-col class="news-item-meta-infos-label">
        <strong>{{ $t('assess.source') }}:</strong>
      </v-col>
      <v-col>
        {{ getSource().name }} <br />
        <a
          :href="getSource().link"
          target="_blank"
          icon
          class="meta-link d-flex"
        >
          <v-icon left x-small color="primary">mdi-open-in-new</v-icon>
          <span class="label">{{ getSource().link }}</span>
        </a>
      </v-col>
    </v-row>
    <v-row class="news-item-meta-infos" v-if="getAuthor()">
      <v-col class="news-item-meta-infos-label">
        <strong>{{ $t('assess.author') }}:</strong>
      </v-col>
      <v-col>
        <span :class="[{ decorateSource: newsItem.decorateSource }]">
          {{ getAuthor() }}
          <v-icon right small v-if="newsItem.decorateSource" class="ml-0"
            >mdi-seal</v-icon
          >
        </span>
      </v-col>
    </v-row>
  </div>
</template>

<script>
import { isValidUrl } from '@/utils/helpers'

export default {
  name: 'metainfo',
  props: {
    newsItem: {
      type: Object,
      required: true
    }
  },
  computed: {
    published_date() {
      return this.newsItem.news_item_data.published || false
    },
    published_date_outdated() {
      const pub_date = this.published_date
      if (!pub_date) {
        return false
      }
      const oneWeekAgo = new Date()
      oneWeekAgo.setDate(oneWeekAgo.getDate() - 7)
      return oneWeekAgo > pub_date
    }
  },
  methods: {
    getAuthor() {
      return this.newsItem.news_item_data.author
    },
    getSource() {
      let source = this.newsItem.news_item_data.source
      if (isValidUrl(source)) {
        source = new URL(source).hostname.replace('www.', '')
      }

      // TODO: get Type (e.g. RSS, Web, Email, ...)

      return {
        name: source,
        link: this.newsItem.news_item_data.link,
        type: this.newsItem.news_item_data.osint_source_id
      }
    },

    getPublishedDate() {
      const published = this.published_date
      if (published) {
        return new Date(published)
      }
      return '** no published date **'
    },

    getCollectedDate() {
      return new Date(this.newsItem.news_item_data.collected)
    }
  }
}
</script>
