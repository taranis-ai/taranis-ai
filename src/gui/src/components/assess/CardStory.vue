<template>
  <v-card
    v-if="showStory"
    :ripple="false"
    flat
    :rounded="false"
    class="no-gutters align-self-stretch mb-1 mt-1 mx-2 story-card"
    :class="card_class"
    @click="toggleSelection"
  >
    <v-container fluid style="min-height: 112px" class="pa-0 pl-2">
      <v-row class="pl-2">
        <v-col class="d-flex">
          <v-row class="py-1 px-1">
            <v-col cols="12" :lg="content_cols">
              <v-container class="d-flex pa-0">
                <v-icon
                  v-if="story_in_report"
                  class="mr-1 mt-1"
                  icon="mdi-share"
                />
                <h2
                  v-dompurify-html="highlighted_title"
                  class="mb-1 mt-0"
                  :class="{
                    news_item_title_class: true,
                    story: news_item_length > 1
                  }"
                />

                <h2
                  v-if="news_item_length > 1"
                  class="ml-3 mb-1 d-flex justify-center align-center text-primary"
                  style="font-size: 1rem"
                >
                  <v-icon
                    class="float-left mr-1"
                    size="x-small"
                    color="primary"
                  >
                    mdi-file-multiple-outline
                  </v-icon>
                  ({{ news_item_length }})
                </h2>
              </v-container>

              <summarized-content
                :open="openSummary"
                :is-summarized="is_summarized"
                :content="getDescription"
              />
            </v-col>

            <v-col cols="12" class="meta-info-col" :lg="meta_cols">
              <story-meta-info
                :story="story"
                :detail-view="openSummary"
                :report-view="reportView"
              />
              <week-chart
                v-if="showWeekChart && openSummary"
                class="mt-5"
                :chart-height="180"
                :story="story"
              />
            </v-col>
            <v-col v-if="showWeekChart && !openSummary" cols="12" lg="2">
              <week-chart
                :chart-height="detailView ? 300 : 100"
                :chart-width="detailView ? 800 : 100"
                :story="story"
              />
            </v-col>
          </v-row>
        </v-col>
        <v-col class="action-bar mr-2">
          <story-actions-vertical
            :story="story"
            :detail-view="detailView"
            :report-view="reportView"
            :action-cols="meta_cols"
            @open-details="openCard()"
            @refresh="emitRefresh()"
            @remove-from-report="$emit('remove-from-report')"
          />
        </v-col>
      </v-row>
    </v-container>
  </v-card>
  <v-row
    v-if="openSummary && story.news_items.length > 1"
    dense
    class="ma-0 py-0 px-2"
  >
    <div class="news-item-container w-100 pb-2 mb-4">
      <card-news-item
        v-for="item in story.news_items"
        :key="item.id"
        :news-item="item"
        :detail-view="detailView"
        :open-view="openSummary"
        :story="story"
        @refresh="emitRefresh()"
      />
    </div>
  </v-row>
</template>

<script>
import StoryMetaInfo from '@/components/assess/card/StoryMetaInfo.vue'
import StoryActionsVertical from '@/components/assess/card/StoryActionsVertical.vue'
import SummarizedContent from '@/components/assess/card/SummarizedContent.vue'
import CardNewsItem from '@/components/assess/CardNewsItem.vue'
import { ref, computed } from 'vue'
import { useAssessStore } from '@/stores/AssessStore'
import { useFilterStore } from '@/stores/FilterStore'
import { highlight_text } from '@/utils/helpers'
import { unGroupStories } from '@/api/assess'
import { storeToRefs } from 'pinia'
import WeekChart from '@/components/assess/card/WeekChart.vue'

export default {
  name: 'CardStory',
  components: {
    CardNewsItem,
    StoryActionsVertical,
    StoryMetaInfo,
    SummarizedContent,
    WeekChart
  },
  props: {
    story: {
      type: Object,
      required: true
    },
    detailView: { type: Boolean, default: false },
    reportView: { type: Boolean, default: false }
  },
  emits: ['refresh', 'remove-from-report'],
  setup(props, { emit }) {
    const viewDetails = ref(false)
    const openSummary = ref(props.detailView)
    const assessStore = useAssessStore()

    const { newsItemSelection } = storeToRefs(assessStore)
    const selected = computed(() =>
      assessStore.storySelection.includes(props.story.id)
    )

    const { showWeekChart, compactView } = storeToRefs(useFilterStore())

    const showStory = computed(() => {
      return (
        props.story.news_items.length > 0 &&
        'news_item_data' in props.story.news_items[0]
      )
    })

    const item_important = computed(() =>
      'important' in props.story ? props.story.important : false
    )

    const content_cols = computed(() => {
      if (props.detailView) {
        return 8
      }
      if (showWeekChart.value) {
        if (compactView.value) {
          if (openSummary.value) {
            return 10
          }
          return 8
        }
        if (openSummary.value) {
          return 9
        }
        return 7
      }
      if (props.reportView || compactView.value) {
        return 10
      }
      return 8
    })

    const meta_cols = computed(() => {
      if (showWeekChart.value && !openSummary.value) {
        return 12 - content_cols.value - 2
      }
      return 12 - content_cols.value
    })

    const story_in_report = computed(() => props.story.in_reports_count > 0)
    const news_item_length = computed(() =>
      props.story.news_items ? props.story.news_items.length : 0
    )
    const news_item_title_class = computed(() => {
      return openSummary.value || props.detailView
        ? 'news-item-title-no-clip'
        : 'news-item-title'
    })
    const minButtonWidth = computed(() => {
      const longestText = `${
        news_item_length.value > 1 ? '(' + news_item_length.value + ')' : ''
      }`
      return longestText.length + 11 + 'ch'
    })

    const story_in_reports = computed(() => {
      return props.story ? props.story.in_reports_count : 0
    })

    const is_summarized = computed(() => {
      return props.story.summary !== undefined && props.story.summary !== ''
    })

    const highlighted_title = computed(() => {
      return highlight_text(props.story.title)
    })

    const card_class = computed(() => {
      return {
        selected: selected.value,
        read: props.story.read,
        unread: !props.story.read,
        important: props.story.important,
        relevant: props.story.relevance
      }
    })

    const getDescription = computed(() => {
      const { description, summary, news_items } = props.story
      const defaultContent = news_items[0].news_item_data.content

      return openSummary.value
        ? defaultContent
        : summary || description || defaultContent
    })

    function openCard() {
      openSummary.value = !openSummary.value
    }

    function toggleSelection() {
      assessStore.selectStory(props.story.id)
    }

    function markAsRead() {
      assessStore.readNewsItemAggregate(props.story.id)
    }

    function markAsImportant() {
      assessStore.importantNewsItemAggregate(props.story.id)
    }

    function emitRefresh() {
      emit('refresh')
    }

    function ungroup() {
      unGroupStories([props.story.id]).then(() => {
        emit('refresh')
      })
    }

    function moveSelection() {
      // assessStore.moveSelectionToStory(props.story.id, newsItemSelection.value)
      console.debug('move selection to story', newsItemSelection.value)
    }

    return {
      viewDetails,
      openSummary,
      selected,
      content_cols,
      meta_cols,
      showStory,
      card_class,
      item_important,
      story_in_report,
      news_item_length,
      news_item_title_class,
      highlighted_title,
      minButtonWidth,
      story_in_reports,
      is_summarized,
      newsItemSelection,
      getDescription,
      openCard,
      ungroup,
      toggleSelection,
      markAsRead,
      markAsImportant,
      moveSelection,
      emitRefresh,
      showWeekChart
    }
  }
}
</script>

<style lang="scss">
.v-card__overlay {
  background-color: white !important;
}

.story-card {
  border: 2px solid white;
  transition: 180ms;
  box-shadow: 1px 2px 9px 0px rgba(0, 0, 0, 0.15);
  &.selected {
    border-color: rgb(var(--v-theme-primary));
    margin: -2px;
    background-color: color-mix(
      in srgb,
      rgb(var(--v-theme-primary)) 10%,
      #ffffff
    );
  }
}

.news-item-container {
  background-color: color-mix(in srgb, rgb(var(--v-theme-primary)) 40%, white);
}

.news-item-title {
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  line-clamp: 1;
  -webkit-box-orient: vertical;
  max-height: calc(1.5em * 2);
  line-height: 1.3;
}
.news-item-title-no-clip {
  max-height: calc(1.5em * 2);
  line-height: 1.3;
}

.unread::after {
  content: '';
  position: absolute;
  left: 0px;
  top: 0;
  bottom: 0;
  width: 7px;
  background-color: rgb(var(--v-theme-primary)) !important;
  z-index: 1;
}

.unread.important::after {
  content: '';
  position: absolute;
  left: 0px;
  top: 0;
  bottom: 0;
  width: 7px;

  background: rgb(116, 104, 232);
  background: linear-gradient(
    rgba(116, 104, 232, 1) 50%,
    rgba(233, 198, 69, 1) 50%
  );

  z-index: 2;
}

.important:not(.unread)::after {
  content: '';
  position: absolute;
  left: 0px;
  top: 0;
  bottom: 0;
  width: 7px;
  z-index: 2;
  background: #e9c645 !important;
}

.action-bar {
  max-width: 45px !important;
  background-color: #f3f3f3;
  padding-left: 0px;
  padding-right: 0px;
}

.meta-info-col {
  border-left: 1px solid #c0c0c0;
}
</style>
