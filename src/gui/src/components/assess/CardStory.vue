<template>
  <v-card
    :ripple="false"
    flat
    :rounded="false"
    class="no-gutters align-self-stretch mb-1 mt-1 mx-2 story-card"
    :class="card_class"
    @click="toggleSelection"
  >
    <v-container
      fluid
      style="min-height: 100px"
      class="pa-0 pl-2"
      :data-testid="`story-card-${story.id}`"
    >
      <v-row class="pl-2">
        <v-col class="d-flex">
          <v-row class="py-1 px-1">
            <v-col
              :cols="meta_cols"
              class="meta-info-col"
              :class="smAndDown ? 'no-border' : ''"
            >
              <story-meta-info
                :story="story"
                :detail-view="openSummary"
                :report-view="reportView"
              />
              <WeekChart
                v-if="openSummary && !reportView && !detailView"
                class="mt-5"
                :chart-height="180"
                :story="story"
              />
            </v-col>
            <v-col
              v-if="
                !openSummary &&
                showWeekChart &&
                !reportView &&
                !detailView &&
                !mdAndDown
              "
              cols="2"
            >
              <WeekChart
                :chart-height="detailView ? 300 : 100"
                :story="story"
              />
            </v-col>
            <v-col>
              <div class="d-flex">
                <h2
                  v-dompurify-html="highlighted_title"
                  class="mb-1 mt-0"
                  :class="{
                    news_item_title_class: true,
                    story: news_item_length > 1
                  }"
                />

                <a
                  v-if="news_item_length > 1"
                  class="ml-3 mb-1 d-flex justify-center align-center"
                  style="font-size: 1rem"
                  :href="'/story/' + story.id"
                  target="_blank"
                  :style="{ color: colorBasedOnLength }"
                >
                  <v-icon
                    class="float-left mr-1"
                    size="x-small"
                    :color="colorBasedOnLength"
                    icon="mdi-file-multiple-outline"
                  />
                  ({{ news_item_length }})
                </a>
              </div>

              <summarized-content
                :compact="compactView"
                :open="openSummary"
                :is-summarized="is_summarized"
                :content="getDescription"
              />
            </v-col>
          </v-row>
        </v-col>
        <v-col class="action-bar mr-1">
          <story-actions
            :story="story"
            :detail-view="detailView"
            :report-view="reportView"
            :action-cols="meta_cols"
            :open-summary="openSummary"
            @open-details="openCard()"
            @refresh="emitRefresh()"
            @remove-from-report="$emit('remove-from-report')"
            @click.stop
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
import StoryActions from '@/components/assess/card/StoryActions.vue'
import SummarizedContent from '@/components/assess/card/SummarizedContent.vue'
import CardNewsItem from '@/components/assess/CardNewsItem.vue'
import { ref, computed } from 'vue'
import { useAssessStore } from '@/stores/AssessStore'
import { useFilterStore } from '@/stores/FilterStore'
import { highlight_text } from '@/utils/helpers'
import { storeToRefs } from 'pinia'
import ChartWrapper from '@/components/assess/card/ChartWrapper.vue'
import { useDisplay } from 'vuetify'
import { useMainStore } from '@/stores/MainStore'

export default {
  name: 'CardStory',
  components: {
    CardNewsItem,
    StoryActions,
    StoryMetaInfo,
    SummarizedContent,
    WeekChart: ChartWrapper
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
    const { mdAndDown, smAndDown, xxl } = useDisplay()

    const { newsItemSelection } = storeToRefs(assessStore)
    const selected = computed(() =>
      assessStore.storySelection.includes(props.story.id)
    )

    const { showWeekChart, compactView } = storeToRefs(useFilterStore())
    const { drawerVisible } = storeToRefs(useMainStore())

    const item_important = computed(() =>
      'important' in props.story ? props.story.important : false
    )

    const content_cols = computed(() => {
      const navSub = drawerVisible.value ? 1 : 0
      if (smAndDown.value) {
        return 12
      }
      if (compactView.value || xxl.value) {
        return 10
      }
      if (props.reportView) {
        return 6
      }
      return 10 - navSub
    })

    const meta_cols = computed(() => {
      if (smAndDown.value) {
        return 12
      }
      if (showWeekChart.value && !openSummary.value) {
        return 12 - content_cols.value
      }
      if (showWeekChart.value && openSummary.value) {
        return 2
      }
      if (compactView.value && !mdAndDown.value) {
        return 1
      }
      return 12 - content_cols.value
    })

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
      const defaultContent = news_items[0]?.content

      return summary || description || defaultContent
    })

    const colorBasedOnLength = computed(() => {
      // Color codes are needed for consistent icon/number color shades
      if (news_item_length.value < 5) {
        return '#388E3C'
      } else if (news_item_length.value < 10) {
        return '#F57F17'
      } else {
        return '#BF360C'
      }
    })

    function openCard() {
      openSummary.value = !openSummary.value
    }

    function toggleSelection() {
      if (props.reportView) {
        return
      }
      assessStore.selectStory(props.story.id)
    }

    function emitRefresh() {
      emit('refresh')
    }

    return {
      viewDetails,
      openSummary,
      selected,
      meta_cols,
      card_class,
      compactView,
      item_important,
      news_item_length,
      news_item_title_class,
      highlighted_title,
      minButtonWidth,
      is_summarized,
      newsItemSelection,
      getDescription,
      colorBasedOnLength,
      showWeekChart,
      openCard,
      toggleSelection,
      emitRefresh,
      mdAndDown,
      smAndDown
    }
  }
}
</script>

<style lang="scss" scoped>
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
    & .action-bar {
      background-color: color-mix(
        in srgb,
        rgb(var(--v-theme-primary)) 10%,
        #ebebeb
      );
    }
  }
}

.meta-info-col {
  min-width: 240px !important;
  &.no-border {
    border-right: 0;
  }
}

.news-item-container {
  background-color: color-mix(in srgb, rgb(var(--v-theme-primary)) 40%, white);
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
</style>
