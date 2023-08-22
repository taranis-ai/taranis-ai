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
    @click="detailView ? null : { click: toggleSelection }"
  >
    <v-row>
      <v-col
        cols="12"
        sm="12"
        lg="6"
        class="d-flex flex-grow-1 mt-3 px-5 py-3 order-first"
        align-self="center"
      >
        <!-- <v-icon v-if="story_in_report" class="mr-2 my-auto"> mdi-share </v-icon> -->
        <h2 class="news-item-title">
          {{ title }}
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
          :to="'/newsitem/' + newsItem.id"
          title="View News Item"
          @click.stop
        >
          <span> Open </span>
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
          @click.stop="openCard"
        >
          <span> {{ news_item_summary_text }} </span>
        </v-btn>

        <v-btn
          v-ripple="false"
          size="small"
          class="item-action-btn"
          variant="tonal"
          append-icon="mdi-card-remove"
          @click.stop="removeFromStory()"
        >
          <span>Remove</span>
        </v-btn>

        <v-dialog v-model="deleteDialog" width="auto">
          <popup-delete-item
            :news-item="newsItem"
            @delete-item="deleteNewsItem()"
            @close="deleteDialog = false"
          />
        </v-dialog>
        <v-dialog v-model="sharingDialog" width="auto">
          <popup-share-items
            :item-ids="[newsItem.id]"
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
                !newsItem.read ? 'mdi-eye-outline' : 'mdi-eye-off-outline'
              "
              class="hidden-xl-only"
              title="mark as read"
              @click.stop="markAsRead()"
            />
            <v-list-item
              :prepend-icon="
                !newsItem.important
                  ? 'mdi-star-check-outline'
                  : 'mdi-star-check'
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
      <v-col
        cols="12"
        sm="12"
        lg="6"
        class="px-5 order-lg-3 order-md-2"
        align-self="stretch"
      >
        <summarized-content
          :open="openSummary"
          :is_summarized="false"
          :content="description"
        />
      </v-col>
      <v-col class="px-5 pt-2 pb-3 order-4" cols="12" sm="12" lg="6">
        <news-meta-info :news-item="newsItem" />
      </v-col>
    </v-row>
  </v-card>
</template>

<script>
import PopupDeleteItem from '@/components/popups/PopupDeleteItem.vue'
import SummarizedContent from '@/components/assess/card/SummarizedContent.vue'
import NewsMetaInfo from '@/components/assess/card/NewsMetaInfo.vue'
import PopupShareItems from '@/components/popups/PopupShareItems.vue'
import { notifySuccess, notifyFailure } from '@/utils/helpers.js'
import {
  deleteNewsItemAggregate,
  importantNewsItemAggregate,
  readNewsItemAggregate,
  unGroupAction
} from '@/api/assess'
import { ref, computed } from 'vue'

export default {
  name: 'CardNewsItem',
  components: {
    NewsMetaInfo,
    PopupDeleteItem,
    PopupShareItems,
    SummarizedContent
  },
  props: {
    newsItem: {
      type: Object,
      required: true
    },
    selected: Boolean,
    detailView: Boolean
  },
  emits: ['selectItem', 'deleteItem', 'refresh'],
  setup(props, { emit }) {
    const viewDetails = ref(false)
    const openSummary = ref(props.detailView)
    const sharingDialog = ref(false)
    const deleteDialog = ref(false)

    const news_item_summary_text = computed(() =>
      openSummary.value ? 'Collapse' : 'Expand'
    )

    const description = computed(
      () =>
        props.newsItem.news_item_data?.content ||
        props.newsItem.news_item_data?.review
    )

    const openCard = () => {
      openSummary.value = !openSummary.value
    }

    const title = computed(() => props.newsItem.news_item_data?.title)

    const toggleSelection = () => {
      emit('selectItem', props.newsItem.id)
    }

    const markAsRead = () => {
      readNewsItemAggregate(props.newsItem.id)
    }

    const markAsImportant = () => {
      importantNewsItemAggregate(props.newsItem.id)
    }

    const deleteNewsItem = () => {
      deleteNewsItemAggregate(props.newsItem.id)
      emit('deleteItem', props.newsItem.id)
    }

    const removeFromStory = () => {
      unGroupAction([props.newsItem.id])
        .then(() => {
          notifySuccess('News Item removed from Story')

          emit('refresh')
        })
        .catch(() => {
          notifyFailure('Failed to remove News Item from Story')
        })
    }

    return {
      title,
      viewDetails,
      openSummary,
      sharingDialog,
      deleteDialog,
      news_item_summary_text,
      description,
      openCard,
      toggleSelection,
      markAsRead,
      markAsImportant,
      deleteNewsItem,
      removeFromStory
    }
  }
}
</script>

<style scoped>
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
</style>
