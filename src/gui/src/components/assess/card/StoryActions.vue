<template>
  <v-col
    :cols="actionCols"
    class="d-flex flex-row flex-grow-1 order-lg-2 pb-0 justify-space-evenly"
  >
    <v-btn
      v-if="!detailView"
      v-ripple="false"
      size="small"
      class="item-action-btn"
      variant="tonal"
      prepend-icon="mdi-open-in-app"
      :to="'/story/' + story.id"
      @click.stop
    >
      <v-tooltip activator="parent" location="start">
        open detail view
      </v-tooltip>
      <span v-if="!compactView">open</span>
    </v-btn>

    <v-btn
      v-if="!reportView"
      v-ripple="false"
      size="small"
      class="item-action-btn"
      variant="tonal"
      prepend-icon="mdi-google-circles-communities"
      @click.stop="sharingDialog = true"
    >
      <v-tooltip activator="parent" location="start"> add to Report </v-tooltip>
      <span v-if="!compactView">Report</span>
    </v-btn>

    <v-btn
      v-if="reportView"
      v-ripple="false"
      size="small"
      class="item-action-btn"
      variant="tonal"
      prepend-icon="mdi-trash-can"
      @click.stop="$emit('remove-from-report')"
    >
      <v-tooltip activator="parent" location="start">
        remove from report
      </v-tooltip>
      <span>Remove</span>
    </v-btn>

    <v-btn
      v-if="!detailView"
      v-ripple="false"
      size="small"
      class="item-action-btn expand-btn"
      :class="{ 'expanded-card': openSummary }"
      variant="tonal"
      :prepend-icon="openSummary ? 'mdi-chevron-up' : 'mdi-chevron-down'"
      :style="{ minWidth: minButtonWidth }"
      @click.stop="openCard"
    >
      <v-tooltip activator="parent" location="start"> show details </v-tooltip>

      <span>{{ news_item_summary_text }} </span>
      <span v-if="news_item_length > 1" class="primary--text">
        &nbsp;[{{ news_item_length }}]
      </span>
    </v-btn>

    <v-btn
      v-if="!detailView && !reportView && !compactView"
      v-ripple="false"
      size="small"
      class="item-action-btn"
      variant="tonal"
      :prepend-icon="!story.read ? 'mdi-eye-outline' : 'mdi-eye-off-outline'"
      @click.stop="markAsRead()"
    >
      <v-tooltip activator="parent" location="start">
        mark story as {{ !story.read ? 'read' : 'unread' }}
      </v-tooltip>
      <span>{{ !story.read ? 'read' : 'unread' }}</span>
    </v-btn>

    <votes v-if="detailView" :story="story" />

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

    <v-menu v-if="!reportView" bottom offset-y>
      <template #activator="{ props }">
        <v-btn
          v-ripple="false"
          size="small"
          class="item-action-btn expandable"
          variant="tonal"
          v-bind="props"
          icon="mdi-dots-vertical"
        />
      </template>

      <v-list class="extraActionsList" dense>
        <v-list-item
          v-if="detailView || reportView"
          :prepend-icon="
            !story.read ? 'mdi-eye-outline' : 'mdi-eye-off-outline'
          "
          class="hidden-xl-only"
          title="mark as read"
          @click.stop="markAsRead()"
        />
        <v-list-item v-if="!detailView" style="justify-content: center">
          <votes :story="story" />
        </v-list-item>
        <v-list-item
          :prepend-icon="
            !story.important ? 'mdi-star-check-outline' : 'mdi-star-check'
          "
          :title="
            !story.important ? 'mark as important' : 'unmark as important'
          "
          @click.stop="markAsImportant()"
        />
        <v-list-item
          title="send via mail"
          prepend-icon="mdi-email-outline"
          @click.stop="shareViaMail"
        />
        <v-list-item
          v-if="!reportView && news_item_length > 1"
          title="ungroup"
          prepend-icon="mdi-ungroup"
          @click.stop="ungroup()"
        >
          <v-tooltip activator="parent" location="start">
            remove all news items from this story
          </v-tooltip>
        </v-list-item>
        <v-list-item
          v-if="!reportView && news_item_length === 1"
          title="open news item"
          prepend-icon="mdi-open-in-app"
          :to="'/newsitem/' + story.news_items[0].id"
        />
        <v-list-item
          v-if="!reportView && newsItemSelection.length > 0"
          title="move selection"
          prepend-icon="mdi-folder-move"
          @click.stop="moveSelection()"
        />
        <v-list-item
          v-if="allow_edit"
          title="edit"
          prepend-icon="mdi-pencil"
          :to="`/newsitem/${story.news_items[0].id}/edit`"
        />
        <v-list-item
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
import votes from '@/components/assess/card/votes.vue'
import { ref, computed } from 'vue'
import { useAssessStore } from '@/stores/AssessStore'
import { useUserStore } from '@/stores/UserStore'
import { useFilterStore } from '@/stores/FilterStore'
import { unGroupStories } from '@/api/assess'
import { storeToRefs } from 'pinia'

export default {
  name: 'StoryActions',
  components: {
    votes,
    PopupDeleteItem,
    PopupShareItems
  },
  props: {
    story: {
      type: Object,
      required: true
    },
    detailView: { type: Boolean, default: false },
    reportView: { type: Boolean, default: false },
    actionCols: { type: Number, default: 4 }
  },
  emits: ['refresh', 'remove-from-report', 'open-details'],
  setup(props, { emit }) {
    const viewDetails = ref(false)
    const openSummary = ref(props.detailView)
    const sharingDialog = ref(false)
    const deleteDialog = ref(false)
    const assessStore = useAssessStore()
    const userStore = useUserStore()

    const read_only_user = computed(() => userStore.read_only_user)

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
  flex: 1;
  & .v-btn__append {
    margin-left: 0.5rem;
  }
  & .v-btn__prepend {
    margin-right: 0.5rem;
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
