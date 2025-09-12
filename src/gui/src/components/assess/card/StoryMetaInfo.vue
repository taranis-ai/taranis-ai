<template>
  <table class="story-meta-info" :class="compactView ? 'compact-view' : ''">
    <tbody>
      <tr>
        <td v-if="!compactView">
          <strong>{{ t('assess.published') }}:</strong>
        </td>
        <td class="text-no-wrap">
          <span
            v-if="getPublishedDate.length > 1"
            :class="published_date_outdated ? 'text-error' : ''"
          >
            {{ getPublishedDate[0] }}<br />
            {{ getPublishedDate[1] }}
          </span>
          <span v-else :class="published_date_outdated ? 'text-error' : ''">
            {{ getPublishedDate[0] }}
          </span>
          <v-icon
            v-if="published_date_outdated"
            class="ml-1"
            size="small"
            color="error"
            icon="mdi-alert-outline"
          />
        </td>
        <td v-if="story_in_reports > 0" class="shared-icons-container">
          <v-icon
            v-for="n in story_in_reports"
            :key="n"
            :style="getSharingIcon(n)"
            icon="mdi-share"
          />
        </td>
      </tr>

      <tr v-if="!compactView && story.tags && !reportView">
        <td>
          <strong> Tags: </strong>
        </td>
        <td>
          <tag-list
            :tags="filteredTags"
            :truncate="!detailView"
            :color="detailView"
            :editable="detailView"
            @edit="editTags"
          />
        </td>
        <td>
          <relevance-indicator :relevance="story.relevance" />
        </td>
      </tr>

      <tr v-if="detailView">
        <td v-if="!compactView"><strong>Vote:</strong></td>
        <td>
          <v-list-item class="px-0">
            <story-votes :story="story" />
          </v-list-item>
        </td>
      </tr>

      <article-info
        :news-item="story.news_items[0]"
        :compact-view="compactView"
      />
      <author-info
        v-if="detailView && story.news_items.length === 1"
        :news-item="story.news_items[0]"
      />
      <tr v-if="detailView">
        <td class="py-0">
          <sentiment-info
            v-if="
              story_sentiment_category && story_sentiment_category !== 'none'
            "
            :sentiment-category="story_sentiment_category"
            :reduced-view="true"
            :compact-view="compactView"
          />
          <cybersecurity-status-info
            v-if="
              story_cybersecurity_status &&
              ['yes', 'no', 'mixed'].includes(story_cybersecurity_status)
            "
            :cybersecurity-status="story_cybersecurity_status"
            :reduced-view="true"
            :compact-view="compactView"
          />
        </td>
      </tr>
      <v-dialog v-model="showTagDialog" width="auto">
        <popup-edit-tags
          :tags="story.tags"
          :story-id="story.id"
          @close="showTagDialog = false"
        />
      </v-dialog>
    </tbody>
  </table>
</template>

<script>
import TagList from '@/components/assess/card/TagList.vue'
import { useFilterStore } from '@/stores/FilterStore'
import { useMainStore } from '@/stores/MainStore'
import { useI18n } from 'vue-i18n'
import { computed, ref } from 'vue'
import { useDisplay } from 'vuetify'
import { storeToRefs } from 'pinia'
import { getAssessSharingIcon } from '@/utils/helpers'
import ArticleInfo from '@/components/assess/card/ArticleInfo.vue'
import AuthorInfo from '@/components/assess/card/AuthorInfo.vue'
import PopupEditTags from '@/components/popups/PopupEditTags.vue'
import StoryVotes from '@/components/assess/card/StoryVotes.vue'
import RelevanceIndicator from '@/components/assess/card/RelevanceIndicator.vue'
import SentimentInfo from '@/components/assess/card/SentimentInfo.vue'
import CybersecurityStatusInfo from '@/components/assess/card/CybersecurityStatusInfo.vue'

export default {
  name: 'StoryMetaInfo',
  components: {
    PopupEditTags,
    ArticleInfo,
    AuthorInfo,
    StoryVotes,
    TagList,
    RelevanceIndicator,
    SentimentInfo,
    CybersecurityStatusInfo
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
    const { name: displayName } = useDisplay()
    const { showWeekChart, compactView } = storeToRefs(useFilterStore())
    const { drawerVisible } = storeToRefs(useMainStore())

    const showTagDialog = ref(false)

    const published_dates = computed(() => {
      const pub_dates = props.story.news_items
        ? props.story.news_items.map((item) => item.published).sort()
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
      let limit = 2 // Default value
      switch (displayName.value) {
        case 'lg':
          limit = 3
          break
        case 'xl':
          limit = 4
          break
        case 'xxl':
          limit = 5
          break
        default:
          limit = 2
      }
      if (drawerVisible.value) {
        limit -= 1
      }
      return limit
    })

    const filteredTags = computed(() => {
      return [...new Set(props.story.tags.slice(0, tagLimit.value))]
    })

    const story_in_reports = computed(() => {
      return props.story ? props.story.in_reports_count : 0
    })

    const getPublishedDate = computed(() => {
      const pubDateNew = new Date(published_dates.value[0])
      const pubDateNewStr = d(pubDateNew, 'long', 'sv-SE')
      const pubDateOld = new Date(published_dates.value[1])
      const pubDateOldStr = d(pubDateOld, 'long', 'sv-SE')
      if (pubDateNew && pubDateOld) {
        return pubDateNewStr === pubDateOldStr
          ? [pubDateNewStr]
          : [pubDateOldStr, pubDateNewStr]
      }
      return ['']
    })

    const story_sentiment_category = computed(() => {
      const items = props.story?.news_items ?? []
      if (!Array.isArray(items) || items.length === 0) return 'none'

      let pos = 0,
        neg = 0,
        neu = 0

      for (const item of items) {
        const cat = item?.attributes?.find(
          (a) => a.key === 'sentiment_category'
        )?.value
        switch ((cat || '').toString().toLowerCase()) {
          case 'positive':
            pos++
            break
          case 'negative':
            neg++
            break
          case 'neutral':
            neu++
            break
          default:
            break
        }
      }

      if (pos === 0 && neg === 0 && neu === 0) return 'none'

      const maxCount = Math.max(pos, neg, neu)
      const leaders = []
      if (pos === maxCount) leaders.push('positive')
      if (neg === maxCount) leaders.push('negative')
      if (neu === maxCount) leaders.push('neutral')
      return leaders.length === 1 ? leaders[0] : 'mixed'
    })

    const getItemCybersecurityStatus = (item) => {
      const attrs = item?.attributes ?? []
      const human = attrs.find((a) => a.key === 'cybersecurity_human')?.value
      const bot = attrs.find((a) => a.key === 'cybersecurity_bot')?.value
      const chosen = human ?? bot
      const v = (chosen ?? '').toString().trim().toLowerCase()

      if (v === 'yes' || v === 'true' || v === '1') return 'yes'
      if (v === 'no' || v === 'false' || v === '0') return 'no'

      return 'none'
    }

    const story_cybersecurity_status = computed(() => {
      const items = props.story?.news_items ?? []
      const set = new Set(items.map(getItemCybersecurityStatus))

      if (set.has('none') && set.size > 1) return 'incomplete'
      if (set.has('yes') && set.has('no') && set.size === 2) return 'mixed'
      if (set.size === 1) {
        if (set.has('yes')) return 'yes'
        if (set.has('no')) return 'no'
        if (set.has('none')) return 'none'
      }
      return 'none'
    })

    function editTags() {
      console.log('edit tags')
      showTagDialog.value = true
    }

    function getSharingIcon(index) {
      return getAssessSharingIcon(index, story_in_reports.value)
    }

    return {
      compactView,
      showWeekChart,
      showTagDialog,
      published_dates,
      published_date_outdated,
      story_in_reports,
      getPublishedDate,
      story_sentiment_category,
      story_cybersecurity_status,
      filteredTags,
      editTags,
      getSharingIcon,
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

.story-meta-info tr td {
  vertical-align: top;
  width: 100%;
}

.story-meta-info:not(.compact-view) tr td:nth-child(1) {
  width: 30px;
  padding-right: 5px;
}

.story-meta-info:not(.compact-view) tr td:nth-child(3) {
  width: 30px;
  text-align: center;
}

.shared-icons-container {
  width: 30%;
  text-align: right;
  padding-right: 20px;
}
</style>
