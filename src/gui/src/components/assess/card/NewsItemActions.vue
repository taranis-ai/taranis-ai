<template>
  <div
    class="ml-auto mr-auto"
    style="width: fit-content"
    :data-testid="`story-actions-div-${newsItem.id}`"
  >
    <v-tooltip
      v-if="!detailView"
      :text="openSummary ? 'hide details' : 'show details'"
    >
      <template #activator="{ props }">
        <v-btn
          v-ripple="false"
          :variant="openSummary ? 'flat' : 'tonal'"
          :color="openSummary ? 'primary' : '#919191'"
          class="item-action-btn"
          density="compact"
          :icon="openSummary ? 'mdi-chevron-up' : 'mdi-chevron-down'"
          v-bind="props"
          @click.stop="openCard"
        />
      </template>
    </v-tooltip>

    <v-tooltip v-if="!detailView" text="open">
      <template #activator="{ props }">
        <v-btn
          v-ripple="false"
          variant="tonal"
          class="item-action-btn"
          density="compact"
          color="#919191"
          icon="mdi-magnify"
          v-bind="props"
          :to="'/newsitem/' + newsItem.id"
          tag="button"
          @click.stop
        />
      </template>
    </v-tooltip>

    <v-tooltip v-if="story && story.news_items.length > 1" text="remove">
      <template #activator="{ props }">
        <v-btn
          v-ripple="false"
          variant="tonal"
          class="item-action-btn"
          density="compact"
          color="#919191"
          icon="mdi-close-circle-outline"
          v-bind="props"
          tag="button"
          @click.stop="removeFromStory()"
        />
      </template>
    </v-tooltip>

    <v-tooltip v-if="allow_edit" text="edit">
      <template #activator="{ props }">
        <v-btn
          v-ripple="false"
          variant="tonal"
          class="item-action-btn"
          density="compact"
          color="#919191"
          icon="mdi-pencil-outline"
          v-bind="props"
          :to="`/newsitem/${newsItem.id}/edit`"
          tag="button"
        />
      </template>
    </v-tooltip>

    <v-tooltip v-if="story && story.in_reports_count < 1" text="delete">
      <template #activator="{ props }">
        <v-btn
          v-ripple="false"
          variant="tonal"
          class="item-action-btn"
          density="compact"
          color="#919191"
          icon="mdi-delete-outline"
          v-bind="props"
          tag="button"
          @click.stop="deleteDialog = true"
        />
      </template>
    </v-tooltip>

    <v-dialog v-model="deleteDialog" width="auto">
      <popup-delete-item
        :title="newsItem.title"
        @delete-item="deleteItem()"
        @close="deleteDialog = false"
      />
    </v-dialog>
  </div>
</template>

<script>
import PopupDeleteItem from '@/components/popups/PopupDeleteItem.vue'
import { notifySuccess, notifyFailure } from '@/utils/helpers.js'
import {
  deleteNewsItem,
  importantStory,
  readStory,
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
      return Boolean(props.newsItem?.source == 'manual')
    })

    const markAsRead = () => {
      readStory(props.newsItem.id)
    }

    const markAsImportant = () => {
      importantStory(props.newsItem.id)
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

<style lang="scss">
.item-action-btn {
  padding: 8px !important;
  margin: 1px !important;
  max-height: 24px;
  display: flex;

  & i {
    font-size: 1.15rem;
  }

  & .v-btn__overlay,
  & .v-btn__underlay {
    opacity: 0;
    transition: all 240ms;
  }
  &:hover .v-btn__overlay,
  &:hover .v-btn__underlay {
    opacity: 0;
  }
}
button.item-action-btn.expandable {
  min-width: 34px !important;
}

.expand-btn.expanded-card {
  background-color: rgb(var(--v-theme-primary));
  color: white;
}
</style>
