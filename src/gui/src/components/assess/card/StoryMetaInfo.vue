<template>
  <v-container column class="pa-0 py-0">
    <v-row v-if="!compactView" no-gutters>
      <v-col>
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
        <v-row v-if="story.tags && story.tags.length > 0 && !reportView">
          <v-col style="max-width: 110px" class="py-0">
            <strong>
              Tags:
              <v-btn
                v-if="detailView"
                icon="mdi-pencil"
                size="x-small"
                @click.prevent="editTags()"
              />
            </strong>
          </v-col>
          <v-col class="py-0">
            <tag-list
              :tags="story.tags"
              :truncate="!detailView"
              :limit="tagLimit"
              :color="detailView"
              :wrap="showWeekChart || detailView"
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
        <article-info
          :news-item-data="story.news_items[0].news_item_data"
          :compact-view="compactView"
        />
        <source-info
          v-if="detailView && story.news_items.length < 2"
          :news-item-data="story.news_items[0].news_item_data"
        />
        <author-info
          v-if="detailView && story.news_items.length === 1"
          :news-item-data="story.news_items[0].news_item_data"
        />
      </v-col>
      <v-col
        :cols="detailView ? 10 : 6"
        :class="detailView ? 'detailView' : ''"
      >
        <week-chart
          v-if="
            !published_date_outdated &&
            !reportView &&
            !detailView &&
            showWeekChart
          "
          :chart-height="detailView ? 300 : 250"
          :chart-width="detailView ? 800 : 600"
          :story="story"
        />
      </v-col>
    </v-row>
    <div v-else class="ml-5">
      <v-row>
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
      </v-row>

      <v-row class="mt-5">
        <article-info
          :news-item-data="story.news_items[0].news_item_data"
          :compact-view="compactView"
        />
      </v-row>

      <v-row class="mt-5">
        <source-info
          v-if="detailView && story.news_items.length === 1"
          :news-item-data="story.news_items[0].news_item_data"
        />
      </v-row>
    </div>
    <v-dialog v-model="showTagDialog" width="auto">
      <popup-edit-tags :tags="story.tags" @close="showTagDialog = false" />
    </v-dialog>
  </v-container>
</template>

<script>
import TagList from '@/components/assess/card/TagList.vue'
import WeekChart from '@/components/assess/card/WeekChart.vue'
import { useFilterStore } from '@/stores/FilterStore'
import { useI18n } from 'vue-i18n'
import { computed, ref } from 'vue'
import { useDisplay } from 'vuetify'
import { storeToRefs } from 'pinia'
import ArticleInfo from '@/components/assess/card/ArticleInfo.vue'
import SourceInfo from '@/components/assess/card/SourceInfo.vue'
import AuthorInfo from '@/components/assess/card/AuthorInfo.vue'
import PopupEditTags from '@/components/popups/PopupEditTags.vue'

export default {
  name: 'StoryMetaInfo',
  components: {
    PopupEditTags,
    ArticleInfo,
    SourceInfo,
    AuthorInfo,
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
  setup(props) {
    const { d, t } = useI18n()
    const { xlAndUp } = useDisplay()
    const { showWeekChart, compactView } = storeToRefs(useFilterStore())

    const showTagDialog = ref(false)

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
      return xlAndUp.value ? 5 : 2
    })

    const getPublishedDate = computed(() => {
      const pubDateNew = new Date(published_dates.value[0])
      const pubDateNewStr = d(pubDateNew, 'long')
      const pubDateOld = new Date(published_dates.value[1])
      const pubDateOldStr = d(pubDateOld, 'long')
      if (pubDateNew && pubDateOld) {
        return pubDateNewStr === pubDateOldStr
          ? pubDateNewStr
          : `${pubDateOldStr} - ${pubDateNewStr}`
      }
      return ''
    })

    function editTags() {
      console.log('edit tags')
      showTagDialog.value = true
    }

    return {
      compactView,
      showWeekChart,
      showTagDialog,
      published_dates,
      published_date_outdated,
      getPublishedDate,
      tagLimit,
      editTags,
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
