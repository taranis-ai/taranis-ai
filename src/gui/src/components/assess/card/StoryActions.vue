<template>
  <div class="ml-auto mr-auto" style="width: fit-content">
    <v-tooltip
      v-if="!detailView"
      :text="openSummary ? 'hide details' : 'show details'"
    >
      <template v-if="!reportView" #activator="{ props }">
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

    <v-tooltip v-if="!detailView && !compactView" text="open detail view">
      <template #activator="{ props }">
        <v-btn
          v-ripple="false"
          variant="tonal"
          class="item-action-btn"
          density="compact"
          color="#919191"
          icon="mdi-magnify"
          v-bind="props"
          :to="'/story/' + story.id"
          tag="button"
          @click.stop
        />
      </template>
    </v-tooltip>

    <v-tooltip v-if="!reportView" text="add to report">
      <template #activator="{ props }">
        <v-btn
          v-ripple="false"
          variant="tonal"
          class="item-action-btn"
          density="compact"
          color="#919191"
          icon="mdi-google-circles-communities"
          v-bind="props"
          @click.stop="sharingDialog = true"
        />
      </template>
    </v-tooltip>

    <v-tooltip v-if="reportView" text="remove from report">
      <template #activator="{ props }">
        <v-btn
          v-ripple="false"
          variant="tonal"
          class="item-action-btn"
          density="compact"
          color="#919191"
          icon="mdi-trash-can"
          v-bind="props"
          @click.stop="$emit('remove-from-report')"
        />
      </template>
    </v-tooltip>

    <v-tooltip
      v-if="!reportView"
      :text="story.read ? 'mark as unread' : 'mark as read'"
    >
      <template #activator="{ props }">
        <v-btn
          v-ripple="false"
          :color="story.read ? 'primary' : '#919191'"
          variant="tonal"
          class="item-action-btn"
          density="compact"
          :icon="story.read ? 'mdi-eye-check-outline' : 'mdi-eye-off-outline'"
          v-bind="props"
          @click.stop="markAsRead()"
        />
      </template>
    </v-tooltip>

    <div v-if="openSummary">
      <v-tooltip
        :text="story.important ? 'uncheck important' : 'mark as important'"
      >
        <template #activator="{ props }">
          <v-btn
            v-ripple="false"
            :color="story.important ? 'primary' : '#919191'"
            variant="tonal"
            class="item-action-btn"
            density="compact"
            v-bind="props"
            :icon="
              !story.important
                ? 'mdi-star-off-outline'
                : 'mdi-star-check-outline'
            "
            @click.stop="markAsImportant()"
          />
        </template>
      </v-tooltip>
      <v-tooltip text="send via mail">
        <template #activator="{ props }">
          <v-btn
            v-ripple="false"
            color="#919191"
            variant="tonal"
            class="item-action-btn"
            density="compact"
            v-bind="props"
            icon="mdi-email-outline"
            @click.stop="shareViaMail"
          />
        </template>
      </v-tooltip>
      <v-tooltip
        v-if="news_item_length > 1"
        text="remove all news items from this story"
      >
        <template #activator="{ props }">
          <v-btn
            v-ripple="false"
            color="#919191"
            variant="tonal"
            class="item-action-btn"
            density="compact"
            v-bind="props"
            icon="mdi-ungroup"
            @click.stop="ungroup()"
          />
        </template>
      </v-tooltip>
      <v-tooltip v-if="news_item_length === 1" text="open news item">
        <template #activator="{ props }">
          <v-btn
            v-ripple="false"
            color="#919191"
            variant="tonal"
            class="item-action-btn"
            density="compact"
            v-bind="props"
            icon="mdi-open-in-app"
            :to="'/newsitem/' + story.news_items[0].id"
          />
        </template>
      </v-tooltip>
      <v-tooltip v-if="allow_edit" text="edit newsitem">
        <template #activator="{ props }">
          <v-btn
            v-ripple="false"
            color="#919191"
            variant="tonal"
            class="item-action-btn"
            density="compact"
            v-bind="props"
            icon="mdi-pencil-outline"
            :to="`/newsitem/${story.news_items[0].id}/edit`"
          />
        </template>
      </v-tooltip>
      <v-tooltip v-if="detailView" text="edit story">
        <template #activator="{ props }">
          <v-btn
            v-ripple="false"
            color="#919191"
            variant="tonal"
            class="item-action-btn"
            density="compact"
            v-bind="props"
            icon="mdi-book-edit-outline"
            :to="`/story/${story.id}/edit`"
          />
        </template>
      </v-tooltip>
      <v-tooltip text="delete">
        <template #activator="{ props }">
          <v-btn
            v-ripple="false"
            color="#919191"
            variant="tonal"
            class="item-action-btn"
            density="compact"
            v-bind="props"
            icon="mdi-delete-outline"
            @click.stop="deleteDialog = true"
          />
        </template>
      </v-tooltip>
    </div>

    <v-menu v-if="!reportView && !openSummary" location="bottom" offset-y>
      <template #activator="{ props }">
        <v-btn
          v-ripple="false"
          density="compact"
          class="item-action-btn"
          variant="tonal"
          v-bind="props"
          color="#919191"
          icon="mdi-dots-horizontal"
        />
      </template>

      <v-list dense>
        <v-list-item
          v-if="detailView"
          :prepend-icon="
            !story.read ? 'mdi-eye-outline' : 'mdi-eye-off-outline'
          "
          class="hidden-xl-only"
          title="mark as read"
          @click.stop="markAsRead()"
        />
        <v-list-item @click.stop="markAsImportant()">
          <v-tooltip
            activator="parent"
            location="start"
            :text="story.important ? 'uncheck important' : 'mark as important'"
          />
          <v-icon
            :icon="
              !story.important ? 'mdi-star-check-outline' : 'mdi-star-check'
            "
          />
        </v-list-item>
        <v-list-item v-if="compactView" :to="'/story/' + story.id">
          <v-tooltip
            activator="parent"
            text="open detail view"
            location="start"
          />
          <v-icon icon="mdi-magnify" />
        </v-list-item>

        <v-list-item :to="`/story/${story.id}/edit`">
          <v-tooltip activator="parent" text="edit story" location="start" />
          <v-icon icon="mdi-book-edit-outline" />
        </v-list-item>

        <v-list-item @click.stop="shareViaMail">
          <v-tooltip activator="parent" location="start" text="send via mail" />
          <v-icon icon="mdi-email-outline" title="send via mail" />
        </v-list-item>
        <v-list-item
          v-if="!reportView && news_item_length > 1"
          @click.stop="ungroup()"
        >
          <v-tooltip
            activator="parent"
            location="start"
            text="remove all news items"
          />
          <v-icon icon="mdi-ungroup" title="ungroup" />
        </v-list-item>
        <v-list-item
          v-if="!reportView && news_item_length === 1"
          :to="'/newsitem/' + story.news_items[0].id"
        >
          <v-icon icon="mdi-open-in-app" title="open news item" />
          <v-tooltip
            activator="parent"
            location="start"
            text="open news item"
          />
        </v-list-item>
        <v-list-item
          v-if="!reportView && newsItemSelection.length > 0"
          @click.stop="moveSelection()"
        >
          <v-icon icon="mdi-folder-move" title="move selection to story" />
          <v-tooltip
            activator="parent"
            location="start"
            text="move selection to story"
          />
        </v-list-item>
        <v-list-item
          v-if="allow_edit"
          :to="`/newsitem/${story.news_items[0].id}/edit`"
        >
          <v-icon icon="mdi-pencil-outline" title="edit" />
        </v-list-item>
        <v-list-item @click.stop="deleteDialog = true">
          <v-icon icon="mdi-delete-outline" title="delete" />
          <v-tooltip activator="parent" location="start" text="delete" />
        </v-list-item>
      </v-list>
    </v-menu>

    <!-- DIALOGS -->

    <v-dialog v-model="deleteDialog" width="auto">
      <popup-delete-item
        :title="story.title"
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
  </div>
</template>

<script>
import PopupDeleteItem from '@/components/popups/PopupDeleteItem.vue'
import PopupShareItems from '@/components/popups/PopupShareItems.vue'
import { ref, computed } from 'vue'
import { useAssessStore } from '@/stores/AssessStore'
import { useFilterStore } from '@/stores/FilterStore'
import { unGroupStories } from '@/api/assess'
import { storeToRefs } from 'pinia'

export default {
  name: 'StoryActions',
  components: {
    PopupDeleteItem,
    PopupShareItems
  },
  props: {
    story: {
      type: Object,
      required: true
    },
    detailView: { type: Boolean, default: false },
    reportView: { type: Boolean, default: false }
  },
  emits: ['refresh', 'remove-from-report', 'open-details'],
  setup(props, { emit }) {
    const viewDetails = ref(false)
    const openSummary = ref(props.detailView)
    const sharingDialog = ref(false)
    const deleteDialog = ref(false)
    const assessStore = useAssessStore()
    const { newsItemSelection } = storeToRefs(assessStore)
    const selected = computed(() =>
      assessStore.storySelection.includes(props.story.id)
    )

    const { compactView } = storeToRefs(useFilterStore())

    const item_important = computed(() =>
      'important' in props.story ? props.story.important : false
    )

    const allow_edit = computed(() => {
      return Boolean(
        !props.reportView &&
          props.story.news_items.length === 1 &&
          props.story.news_items[0].news_item_data.source == 'manual'
      )
    })

    const news_item_length = computed(() =>
      props.story.news_items ? props.story.news_items.length : 0
    )
    const minButtonWidth = computed(() => {
      if (compactView.value) {
        return '0px'
      }
      const longestText = `${
        news_item_length.value > 1 ? '(' + news_item_length.value + ')' : ''
      }`
      return longestText.length + 11 + 'ch'
    })

    const news_item_summary_text = computed(() =>
      compactView.value ? '' : openSummary.value ? 'Collapse' : 'Expand'
    )

    const openCard = () => {
      openSummary.value = !openSummary.value
      emit('open-details')
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

    const deleteNewsItem = () => {
      assessStore.removeStoryByID(props.story.id)
    }

    const emitRefresh = () => {
      emit('refresh')
    }

    function shareViaMail() {
      const subject = encodeURIComponent(props.story.title)
      const body = encodeURIComponent(props.story.description)
      window.location.href = `mailto:?subject=${subject}&body=${body}`
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
      allow_edit,
      compactView,
      sharingDialog,
      deleteDialog,
      item_important,
      news_item_length,
      minButtonWidth,
      newsItemSelection,
      news_item_summary_text,
      openCard,
      ungroup,
      toggleSelection,
      shareViaMail,
      markAsRead,
      markAsImportant,
      deleteNewsItem,
      moveSelection,
      emitRefresh
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
