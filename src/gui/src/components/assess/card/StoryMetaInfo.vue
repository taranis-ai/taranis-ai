<template>
  <v-container column class="pa-0 py-0">
    <v-row no-gutters>
      <v-col>
        <!-- left column -->
        <v-row>
          <v-col style="max-width: 110px" class="py-0">
            <strong>{{ t('assess.published') }}:</strong>
          </v-col>
          <v-col class="py-0">
            <span :class="published_date_outdated ? 'error--text' : ''">
              {{ getPublishedDate }}
            </span>
            <v-icon
              v-if="published_date_outdated"
              class="ml-1"
              size="small"
              color="error"
              icon="mdi-alert"
            />
          </v-col>
        </v-row>
        <v-row v-if="story.tags && !reportView">
          <v-col style="max-width: 110px" class="py-0">
            <strong>Tags:</strong>
          </v-col>
          <v-col class="py-0">
            <tag-list
              :tags="story.tags"
              :truncate="!detailView"
              :limit="tagLimit"
              :color="detailView"
            />
          </v-col>
        </v-row>
        <v-row>
          <v-col style="max-width: 110px" class="py-0">
            <strong>Relevance:</strong>
          </v-col>
          <v-col class="py-0">
            {{ story.relevance }}
          </v-col>
        </v-row>
      </v-col>
      <v-col
        :cols="detailView ? 10 : 6"
        :class="detailView ? 'detailView' : ''"
      >
        <week-chart
          v-if="!published_date_outdated && lgAndUp && !reportView"
          :chart-height="detailView ? 300 : 250"
          :chart-width="detailView ? 800 : 600"
          :story="story"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import TagList from '@/components/assess/card/TagList.vue'
import WeekChart from '@/components/assess/card/WeekChart.vue'
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'
import { useDisplay } from 'vuetify'

export default {
  name: 'StoryMetaInfo',
  components: {
    TagList,
    WeekChart
  },
  props: {
    story: {
      type: Object,
      required: true
    },
    detailView: {
      type: Boolean,
      default: false
    },
    reportView: { type: Boolean, default: false }
  },
  emits: ['selectItem', 'deleteItem'],
  setup(props) {
    const { d, t } = useI18n()
    const { xlAndUp, lgAndUp, mdAndUp, name } = useDisplay()

    const published_dates = computed(() => {
      const pub_dates = props.story.news_items
        ? props.story.news_items
            .map((item) => item.news_item_data.published)
            .sort()
        : []

      if (pub_dates.length === 0) {
        console.warn('No published dates found for story', props.story.title)
        return [null, null]
      }

      return [pub_dates[pub_dates.length - 1], pub_dates[0]]
    })

    const published_date_outdated = computed(() => {
      const pub_date = new Date(published_dates.value[0])
      if (!pub_date) {
        return false
      }
      const oneWeekAgo = new Date()
      oneWeekAgo.setDate(oneWeekAgo.getDate() - 6)
      return oneWeekAgo > pub_date
    })

    const tagLimit = computed(() => {
      if (props.detailView) {
        return 20
      }
      return xlAndUp.value ? 6 : 2
    })

    const getPublishedDate = computed(() => {
      const pubDateNew = new Date(published_dates.value[0])
      const pubDateNewStr = d(pubDateNew, 'short')
      const pubDateOld = new Date(published_dates.value[1])
      const pubDateOldStr = d(pubDateOld, 'short')
      if (pubDateNew && pubDateOld) {
        return pubDateNewStr === pubDateOldStr
          ? pubDateNewStr
          : `${pubDateOldStr} - ${pubDateNewStr}`
      }
      return ''
    })

    return {
      published_dates,
      published_date_outdated,
      getPublishedDate,
      lgAndUp,
      mdAndUp,
      tagLimit,
      name,
      t
    }
  }
}
</script>

<style scoped>
.detailView {
  margin-left: 120px;
  margin-right: 30px;
  padding-right: 30px;
  margin-top: 30px;
}
</style>
