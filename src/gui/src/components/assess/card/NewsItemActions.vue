<template>
  <v-col
    cols="12"
    sm="12"
    lg="6"
    class="d-flex flex-row flex-grow-1 order-lg-2 order-sm-3 justify-space-evenly"
  >
    <v-btn
      v-if="!detailView"
      class="item-action-btn"
      text="Open"
      variant="tonal"
      prepend-icon="mdi-text-box-search-outline"
      :to="'/newsitem/' + newsItem.id"
      title="View News Item"
      @click.stop
    />

    <v-btn
      v-if="!detailView"
      class="item-action-btn"
      :text="news_item_summary_text"
      variant="tonal"
      :prepend-icon="openSummary ? 'mdi-chevron-up' : 'mdi-chevron-down'"
      @click.stop="openCard"
    />

    <v-btn
      v-if="story && story.news_items.length > 1"
      text="Remove"
      class="item-action-btn"
      variant="tonal"
      prepend-icon="mdi-close-circle-outline"
      @click.stop="removeFromStory()"
    />

    <v-btn
      v-if="allow_edit"
      text="edit"
      size="small"
      class="item-action-btn"
      variant="tonal"
      prepend-icon="mdi-pencil"
      :to="`/newsitem/${newsItem.id}/edit`"
    />

    <v-btn
      v-if="story && story.in_reports_count < 1"
      size="small"
      class="item-action-btn"
      variant="tonal"
      prepend-icon="mdi-delete-outline"
      text="Delete"
      @click.stop="deleteDialog = true"
    />

    <v-dialog v-model="deleteDialog" width="auto">
      <popup-delete-item
        :title="newsItem.news_item_data.title"
        @delete-item="deleteItem()"
        @close="deleteDialog = false"
      />
    </v-dialog>
  </v-col>
</template>

<script>
import PopupDeleteItem from '@/components/popups/PopupDeleteItem.vue'
import { notifySuccess, notifyFailure } from '@/utils/helpers.js'
import {
  deleteNewsItem,
  importantNewsItemAggregate,
  readNewsItemAggregate,
  unGroupNewsItems
} from '@/api/assess'
import { ref, computed } from 'vue'

export default {
  name: 'CardNewsItem',
  components: {
    PopupDeleteItem
  },
  props: {
    newsItem: {
      type: Object,
      required: true
    },
    story: {
      type: Object,
      required: false,
      default: null
    },
    detailView: Boolean
  },
  emits: ['deleteItem', 'refresh', 'openCard'],
  setup(props, { emit }) {
    const viewDetails = ref(false)
    const openSummary = ref(props.detailView)
    const deleteDialog = ref(false)

    const news_item_summary_text = computed(() =>
      openSummary.value ? 'Collapse' : 'Expand'
    )

    const openCard = () => {
      openSummary.value = !openSummary.value
      emit('openCard')
    }

    const allow_edit = computed(() => {
      return Boolean(props.newsItem?.news_item_data?.source == 'manual')
    })

    const markAsRead = () => {
      readNewsItemAggregate(props.newsItem.id)
    }

    const markAsImportant = () => {
      importantNewsItemAggregate(props.newsItem.id)
    }

    const deleteItem = () => {
      console.debug('deleteItem', props.newsItem.id)
      deleteNewsItem(props.newsItem.id)
      emit('deleteItem', props.newsItem.id)
    }

    const removeFromStory = () => {
      unGroupNewsItems([props.newsItem.id])
        .then(() => {
          notifySuccess('News Item removed from Story')
          emit('refresh')
        })
        .catch(() => {
          notifyFailure('Failed to remove News Item from Story')
        })
    }

    return {
      viewDetails,
      allow_edit,
      openSummary,
      deleteDialog,
      news_item_summary_text,
      openCard,
      markAsRead,
      markAsImportant,
      deleteItem,
      removeFromStory
    }
  }
}
</script>
