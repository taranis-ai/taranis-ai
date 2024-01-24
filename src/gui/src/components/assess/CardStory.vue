<template>
  <v-card
    v-if="showStory"
    :ripple="false"
    elevation="0"
    :rounded="false"
    class="no-gutters align-self-stretch mb-1 mt-2 mx-2 story-card"
    :class="card_class"
    @click="toggleSelection"
  >
    <v-row class="pl-2">
      <v-col
        :cols="content_cols"
        class="d-flex flex-grow-1 mt-1 px-5 py-0 order-first"
        align-self="center"
      >
        <v-icon v-if="story_in_report" class="mr-2 my-auto" icon="mdi-share" />
        <h2
          v-dompurify-html="highlighted_title"
          :class="news_item_title_class"
        />
      </v-col>

      <story-actions
        :story="story"
        :detail-view="detailView"
        :report-view="reportView"
        :action-cols="meta_cols"
        @open-details="openCard()"
        @refresh="emitRefresh()"
        @remove-from-report="$emit('remove-from-report')"
      />

      <!-- DESCRIPTION -->
      <v-col
        :cols="content_cols"
        class="px-5 pb-5 pt-0 order-3"
        align-self="stretch"
      >
        <summarized-content
          :open="openSummary"
          :is-summarized="is_summarized"
          :content="getDescription"
        />
      </v-col>
      <!-- META INFO -->
      <v-col class="px-5 pt-1 pb-1 order-4" :cols="meta_cols">
        <story-meta-info
          :story="story"
          :detail-view="openSummary"
          :report-view="reportView"
        />
      </v-col>
    </v-row>
  </v-card>
  <v-row
    v-if="openSummary && story.news_items.length > 1"
    dense
    class="ma-0 mx-2 py-0 px-2"
  >
    <div class="news-item-container w-100">
      <card-news-item
        v-for="item in story.news_items"
        :key="item.id"
        :news-item="item"
        :detail-view="detailView"
        :story="story"
        class="mt-2 mx-5 my-3"
        @refresh="emitRefresh()"
      />
    </div>
  </v-row>
</template>

<script>
import StoryMetaInfo from '@/components/assess/card/StoryMetaInfo.vue'
import StoryActions from '@/components/assess/card/StoryActions.vue'
import SummarizedContent from '@/components/assess/card/SummarizedContent.vue'
import CardNewsItem from '@/components/assess/CardNewsItem.vue'
import { ref, computed } from 'vue'
import { useAssessStore } from '@/stores/AssessStore'
import { useFilterStore } from '@/stores/FilterStore'
import { highlight_text } from '@/utils/helpers'
import { unGroupStories } from '@/api/assess'
import { storeToRefs } from 'pinia'

export default {
  name: 'CardStory',
  components: {
    CardNewsItem,
    StoryActions,
    StoryMetaInfo,
    SummarizedContent
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
        return 6
      }
      if (props.reportView || compactView.value) {
        return 10
      }
      return 8
    })

    const meta_cols = computed(() => {
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
        important: props.story.important,
        relevant: props.story.relevance
      }
    })

    const openCard = () => {
      openSummary.value = !openSummary.value
    }

    const toggleSelection = () => {
      assessStore.selectStory(props.story.id)
    }

    const markAsRead = () => {
      assessStore.readNewsItemAggregate(props.story.id)
    }

    const markAsImportant = () => {
      assessStore.importantNewsItemAggregate(props.story.id)
    }

    const emitRefresh = () => {
      emit('refresh')
    }

    const getDescription = computed(() => {
      return openSummary.value
        ? props.story.description ||
            props.story.news_items[0].news_item_data.content
        : props.story.summary ||
            props.story.description ||
            props.story.news_items[0].news_item_data.content
    })

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
      emitRefresh
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
  &:hover {
    transition: border-color 180ms;
    border-color: color-mix(in srgb, rgb(var(--v-theme-primary)) 50%, #ffffff);
  }
  &.selected {
    background-color: color-mix(
      in srgb,
      rgb(var(--v-theme-primary)) 5%,
      #ffffff
    );
    border-color: rgb(var(--v-theme-primary));
    margin: -2px;
  }
}

.news-item-container {
  background-color: #f0f0f0;
  border: 2px dotted rgb(var(--v-theme-primary));
  background-color: color-mix(
    in srgb,
    rgb(var(--v-theme-primary)) 15%,
    #eaeaea
  );
  border-radius: 4px;
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
.read::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background-color: blue;
  z-index: 1;
}

.important::after {
  content: '';
  position: absolute;
  left: 4px;
  top: 0;
  bottom: 0;
  width: 4px;
  background-color: red;
  z-index: 1;
}

.relevant {
  border-left: 4px solid green;
}
</style>
