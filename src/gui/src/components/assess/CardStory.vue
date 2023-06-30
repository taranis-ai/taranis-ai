<template>
  <v-card
    :ripple="false"
    elevation="3"
    :rounded="false"
    class="no-gutters align-self-stretch mb-3 mt-2"
    :class="[
      {
        selected: selected
      }
    ]"
    @click="toggleSelection"
  >
    <v-row>
      <v-col
        cols="12"
        sm="12"
        lg="6"
        class="d-flex flex-grow-1 mt-3 px-5 py-3 order-first"
        align-self="center"
      >
        <v-icon v-if="story_in_report" class="mr-2 my-auto"> mdi-share </v-icon>
        <h2 class="news-item-title">
          {{ story.title }}
        </h2>
      </v-col>

      <v-col
        cols="12"
        sm="12"
        lg="6"
        class="d-flex flex-row flex-grow-1 order-lg-2 order-sm-3 justify-space-evenly"
      >
        <v-btn
          v-if="!detailView"
          v-ripple="false"
          size="small"
          class="item-action-btn"
          variant="tonal"
          append-icon="mdi-text-box-search-outline"
          :to="'/story/' + story.id"
          title="View Story"
          @click.stop
        >
          <span>Details</span>
        </v-btn>

        <v-btn
          v-ripple="false"
          size="small"
          class="item-action-btn"
          variant="tonal"
          append-icon="mdi-google-circles-communities"
          title="Add to Report"
          @click.stop="sharingDialog = true"
        >
          <span>Add to Report</span>
        </v-btn>

        <v-btn
          v-if="!detailView"
          v-ripple="false"
          size="small"
          class="item-action-btn"
          variant="tonal"
          :append-icon="openSummary ? 'mdi-chevron-up' : 'mdi-chevron-down'"
          :style="{ minWidth: minButtonWidth }"
          @click.stop="openCard"
        >
          <span>{{ news_item_summary_text }}</span>
          <span v-if="news_item_length > 1" class="primary--text"
            >&nbsp;[{{ news_item_length }}]</span
          >
        </v-btn>

        <v-btn
          v-ripple="false"
          size="small"
          class="item-action-btn"
          variant="tonal"
          :append-icon="!story.read ? 'mdi-eye-outline' : 'mdi-eye-off-outline'"
          :title="!story.read ? 'mark as read' : 'unmark as read'"
          @click.stop="markAsRead()"
        >
          <span>{{ !story.read ? 'read' : 'unread' }}</span>
        </v-btn>

        <votes v-if="detailView" :story="story" />

        <v-dialog v-model="deleteDialog" width="auto">
          <popup-delete-item
            :news-item="story"
            @delete-item="deleteNewsItem()"
            @close="deleteDialog = false"
          />
        </v-dialog>
        <v-dialog v-model="sharingDialog" width="auto">
          <popup-share-items
            :item-ids="[story.id]"
            @close="sharingDialog = false"
          />
        </v-dialog>

        <v-menu bottom offset-y>
          <template #activator="{ props }">
            <v-btn
              v-ripple="false"
              size="small"
              class="item-action-btn expandable"
              variant="tonal"
              v-bind="props"
            >
              <v-icon>mdi-dots-vertical</v-icon>
            </v-btn>
          </template>

          <v-list class="extraActionsList" dense>
            <v-list-item
              :prepend-icon="
                !story.read ? 'mdi-eye-outline' : 'mdi-eye-off-outline'
              "
              class="hidden-xl-only"
              title="mark as read"
              @click.stop="markAsRead()"
            />
            <v-list-item
              :prepend-icon="
                !story.important ? 'mdi-star-check-outline' : 'mdi-star-check'
              "
              title="mark as important"
              @click.stop="markAsImportant()"
            />
            <v-list-item
              title="delete"
              prepend-icon="mdi-delete-outline"
              @click.stop="deleteDialog = true"
            />
          </v-list>
        </v-menu>
      </v-col>
      <!-- DESCRIPTION -->
      <v-col
        cols="12"
        sm="12"
        lg="6"
        class="px-5 order-lg-3 order-md-2"
        align-self="stretch"
      >
        <summarized-content
          :open="openSummary"
          :is-summarized="is_summarized"
          :content="getDescription"
        />
      </v-col>
      <!-- META INFO -->
      <v-col class="px-5 pt-2 pb-3 order-4" cols="12" sm="12" lg="6">
        <story-meta-info :story="story" :detail-view="openSummary" />
      </v-col>
    </v-row>
  </v-card>
  <v-row v-if="openSummary" dense class="ma-0 py-0 px-5">
    <v-col cols="11" offset="1">
      <card-news-item
        v-for="item in story.news_items"
        :key="item.id"
        :news-item="item"
        :detail-view="false"
        class="mt-3"
      />
    </v-col>
  </v-row>
</template>

<script>
import PopupDeleteItem from '@/components/popups/PopupDeleteItem.vue'
import PopupShareItems from '@/components/popups/PopupShareItems.vue'
import StoryMetaInfo from '@/components/assess/card/StoryMetaInfo.vue'
import votes from '@/components/assess/card/votes.vue'
import SummarizedContent from '@/components/assess/card/SummarizedContent.vue'
import CardNewsItem from '@/components/assess/CardNewsItem.vue'
import {
  deleteNewsItemAggregate,
  importantNewsItemAggregate,
  readNewsItemAggregate
} from '@/api/assess'
import { ref, computed } from 'vue'

export default {
  name: 'CardStory',
  components: {
    CardNewsItem,
    PopupDeleteItem,
    PopupShareItems,
    StoryMetaInfo,
    votes,
    SummarizedContent
  },
  props: {
    story: {
      type: Object,
      required: true
    },
    selected: { type: Boolean, default: false },
    detailView: { type: Boolean, default: false }
  },
  emits: ['selectItem', 'deleteItem'],
  setup(props, { emit }) {
    const viewDetails = ref(false)
    const openSummary = ref(props.detailView)
    const sharingDialog = ref(false)
    const deleteDialog = ref(false)

    const item_important = computed(() =>
      'important' in props.story ? props.story.important : false
    )

    const story_in_report = computed(() => props.story.in_reports_count > 0)
    const news_item_length = computed(() => props.story.news_items.length)
    const news_item_summary_text = computed(() =>
      openSummary.value ? 'Close' : 'Open'
    )
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

    const openCard = () => {
      openSummary.value = !openSummary.value
    }

    const toggleSelection = () => {
      emit('selectItem', props.story.id)
    }

    const markAsRead = () => {
      readNewsItemAggregate(props.story.id)
    }

    const markAsImportant = () => {
      importantNewsItemAggregate(props.story.id)
    }

    const deleteNewsItem = () => {
      deleteNewsItemAggregate(props.story.id)
      emit('deleteItem', props.story.id)
    }

    const showRelated = (event) => {
      console.log('not yet implemented')
      console.debug(event)
    }

    const getDescription = computed(() => {
      return openSummary.value
        ? news_item_length.value > 1
          ? props.story.description
          : props.story.news_items[0].news_item_data.content
        : props.story.summary || props.story.description
    })

    return {
      viewDetails,
      openSummary,
      sharingDialog,
      deleteDialog,
      item_important,
      story_in_report,
      news_item_length,
      news_item_summary_text,
      minButtonWidth,
      story_in_reports,
      is_summarized,
      getDescription,
      openCard,
      toggleSelection,
      markAsRead,
      markAsImportant,
      deleteNewsItem,
      showRelated
    }
  }
}
</script>