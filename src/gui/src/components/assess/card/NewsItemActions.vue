<template>
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
      prepend-icon="mdi-text-box-search-outline"
      :to="'/newsitem/' + newsItem.id"
      title="View News Item"
      @click.stop
    >
      <span> Open </span>
    </v-btn>

    <v-btn
      v-if="!detailView"
      v-ripple="false"
      size="small"
      class="item-action-btn"
      variant="tonal"
      :prepend-icon="openSummary ? 'mdi-chevron-up' : 'mdi-chevron-down'"
      @click.stop="openCard"
    >
      <span> {{ news_item_summary_text }} </span>
    </v-btn>

    <v-btn
      v-if="story && story.news_items.length > 1"
      v-ripple="false"
      size="small"
      class="item-action-btn"
      variant="tonal"
      prepend-icon="mdi-close-circle-outline"
      @click.stop="removeFromStory()"
    >
      <span>Remove</span>
    </v-btn>

    <v-btn
      v-if="allow_edit"
      v-ripple="false"
      text="edit"
      size="small"
      class="item-action-btn"
      variant="tonal"
      prepend-icon="mdi-pencil"
      :to="`/newsitem/${newsItem.id}/edit`"
    />

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

    <v-menu v-if="!detailView" bottom offset-y>
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
            !newsItem.important ? 'mdi-star-check-outline' : 'mdi-star-check'
          "
          title="mark as important"
          @click.stop="markAsImportant()"
        />
        <v-list-item
          v-if="story.in_reports_count < 1"
          title="delete"
          prepend-icon="mdi-delete-outline"
          @click.stop="deleteDialog = true"
        />
      </v-list>
    </v-menu>
  </v-col>
</template>

<script>
import PopupDeleteItem from '@/components/popups/PopupDeleteItem.vue'
import PopupShareItems from '@/components/popups/PopupShareItems.vue'
import { notifySuccess, notifyFailure } from '@/utils/helpers.js'
import {
  deleteNewsItemAggregate,
  importantNewsItemAggregate,
  readNewsItemAggregate,
  unGroupNewsItems
} from '@/api/assess'
import { ref, computed } from 'vue'

export default {
  name: 'CardNewsItem',
  components: {
    PopupDeleteItem,
    PopupShareItems
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
  emits: ['deleteItem', 'refresh'],
  setup(props, { emit }) {
    const viewDetails = ref(false)
    const openSummary = ref(props.detailView)
    const sharingDialog = ref(false)
    const deleteDialog = ref(false)

    const news_item_summary_text = computed(() =>
      openSummary.value ? 'Collapse' : 'Expand'
    )

    const openCard = () => {
      openSummary.value = !openSummary.value
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

    const deleteNewsItem = () => {
      deleteNewsItemAggregate(props.newsItem.id)
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
      sharingDialog,
      deleteDialog,
      news_item_summary_text,
      openCard,
      markAsRead,
      markAsImportant,
      deleteNewsItem,
      removeFromStory
    }
  }
}
</script>
