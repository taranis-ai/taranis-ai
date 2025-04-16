<template>
  <div
    v-if="active"
    class="ml-auto mr-auto"
    style="width: fit-content"
    :data-testid="`story-actions-div-${story.id}`"
  >
    <v-btn
      v-if="!reportView && !detailView"
      v-ripple="false"
      variant="tonal"
      :color="openSummary ? 'primary' : '#919191'"
      class="item-action-btn"
      density="compact"
      @click.stop="openCard"
      data-testid="show details"
    >
      <v-tooltip
        activator="parent"
        :text="openSummary ? 'hide details' : 'show details'"
      />
      <v-icon :icon="openSummary ? 'mdi-chevron-up' : 'mdi-chevron-down'" />
    </v-btn>
    <v-btn
      v-if="!detailView"
      v-ripple="false"
      variant="tonal"
      class="item-action-btn"
      density="compact"
      color="#919191"
      :to="`/story/${story.id}`"
      tag="button"
      @click.stop
      data-testid="open detail view"
    >
      <v-tooltip activator="parent" text="open detail view" />
      <v-icon icon="mdi-magnify" />
    </v-btn>

    <v-tooltip v-if="openSummary || reportView" text="edit story">
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
          data-testid="edit story"
        />
      </template>
    </v-tooltip>

    <v-btn
      v-if="!reportView && (!compactView || openSummary)"
      v-ripple="false"
      variant="tonal"
      class="item-action-btn"
      density="compact"
      color="#919191"
      icon="mdi-google-circles-communities"
      @click.stop="sharingToReportDialog = true"
      data-testid="add to report"
    >
      <v-tooltip activator="parent" text="add to report" />
      <v-icon icon="mdi-google-circles-communities" />
    </v-btn>

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
          data-testid="remove from report"
        />
      </template>
    </v-tooltip>

    <v-tooltip
      v-if="!reportView && (!compactView || openSummary)"
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
          @click="markAsRead()"
          data-testid="mark as read"
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
            data-testid="mark as important"
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
            data-testid="send via mail"
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
            data-testid="ungroup"
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
            data-testid="open news item"
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
            data-testid="edit newsitem"
          />
        </template>
      </v-tooltip>
      <v-tooltip text="create news item and attach to this story">
        <template #activator="{ props }">
          <v-btn
            v-ripple="false"
            color="#919191"
            variant="tonal"
            class="item-action-btn"
            density="compact"
            v-bind="props"
            icon="mdi-pencil-outline"
            :to="`/enter/${story.id}`"
            data-testid="create and attach news item"
          />
        </template>
      </v-tooltip>
      <v-tooltip v-if="hasConnectorPermissions" text="share story to connector">
        <template #activator="{ props }">
          <v-btn
            v-ripple="false"
            color="#919191"
            variant="tonal"
            class="item-action-btn"
            density="compact"
            v-bind="props"
            icon="mdi-monitor-share"
            @click.stop="shareToConnectorDialog = true"
            data-testid="share story to connector"
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
            data-testid="delete story"
          />
        </template>
      </v-tooltip>
    </div>

    <v-menu
      v-if="!reportView && !openSummary"
      location="bottom"
      offset-y
      :data-testid="`story-actions-menu-${story.id}`"
    >
      <template #activator="{ props }">
        <v-btn
          v-ripple="false"
          density="compact"
          class="item-action-btn"
          variant="tonal"
          v-bind="props"
          color="#919191"
          icon="mdi-dots-horizontal"
          data-testid="show story-actions-menu"
        />
      </template>

      <v-list density="compact" width="56px">
        <v-list-item v-if="compactView" :to="'/story/' + story.id">
          <v-tooltip
            activator="parent"
            text="open detail view"
            location="start"
          />
          <v-icon icon="mdi-magnify" data-testid="open detail view" />
        </v-list-item>
        <v-list-item
          v-if="compactView && !reportView"
          @click.stop="sharingToReportDialog = true"
        >
          <v-tooltip activator="parent" text="add to report" location="start" />
          <v-icon
            icon="mdi-google-circles-communities"
            data-testid="add to report"
          />
        </v-list-item>
        <v-list-item
          v-if="detailView || compactView"
          :prepend-icon="
            !story.read ? 'mdi-eye-outline' : 'mdi-eye-off-outline'
          "
          class="hidden-xl-only"
          @click.stop="markAsRead()"
          data-testid="mark as read"
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
            data-testid="mark as important"
          />
        </v-list-item>

        <v-list-item @click.stop="shareViaMail">
          <v-tooltip activator="parent" location="start" text="send via mail" />
          <v-icon icon="mdi-email-outline" title="send via mail" />
        </v-list-item>
        <v-list-item
          v-if="!reportView && news_item_length > 1"
          @click.stop="ungroup()"
        >
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
        <v-list-item :to="`/story/${story.id}/edit`">
          <v-tooltip activator="parent" text="edit story" location="start" />
          <v-icon icon="mdi-book-edit-outline" title="edit story" />
        </v-list-item>

        <v-list-item
          v-if="allow_edit"
          :to="`/newsitem/${story.news_items[0].id}/edit`"
        >
          <v-icon icon="mdi-pencil-outline" />
          <v-tooltip
            activator="parent"
            location="start"
            text="edit news item"
          />
        </v-list-item>
        <v-list-item :to="`/enter/${story.id}`">
          <v-icon icon="mdi-pencil-outline" />
          <v-tooltip
            activator="parent"
            location="start"
            text="create news item and attach to this story"
          />
        </v-list-item>
        <v-list-item
          v-if="hasConnectorPermissions"
          @click.stop="shareToConnectorDialog = true"
        >
          <v-icon icon="mdi-monitor-share" />
          <v-tooltip
            activator="parent"
            location="start"
            text="share story to connector"
          />
        </v-list-item>
        <v-list-item @click.stop="deleteDialog = true">
          <v-icon icon="mdi-delete-outline" />
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
    <v-dialog v-model="sharingToReportDialog" width="auto">
      <popup-share-to-report
        :item-ids="[story.id]"
        @close="sharingToReportDialog = false"
      />
    </v-dialog>
    <v-dialog
      v-if="hasConnectorPermissions"
      v-model="shareToConnectorDialog"
      width="auto"
    >
      <popup-share-to-connector
        :item-ids="[story.id]"
        @close="shareToConnectorDialog = false"
      />
    </v-dialog>
  </div>
</template>

<script>
import PopupDeleteItem from '@/components/popups/PopupDeleteItem.vue'
import PopupShareToReport from '@/components/popups/PopupShareToReport.vue'
import PopupShareToConnector from '@/components/popups/PopupShareToConnector.vue'
import { ref, computed, onDeactivated, onActivated } from 'vue'
import { useAssessStore } from '@/stores/AssessStore'
import { useFilterStore } from '@/stores/FilterStore'
import { useUserStore } from '@/stores/UserStore'
import Permissions from '@/services/auth/permissions'
import { storeToRefs } from 'pinia'

export default {
  name: 'StoryActions',
  components: {
    PopupDeleteItem,
    PopupShareToReport,
    PopupShareToConnector
  },
  props: {
    story: {
      type: Object,
      required: true
    },
    detailView: { type: Boolean, default: false },
    reportView: { type: Boolean, default: false },
    openSummary: { type: Boolean, default: false }
  },
  emits: ['remove-from-report', 'open-details'],
  setup(props, { emit }) {
    // This variable is an ugly hack to still show tooltips after the view is changed
    // This happens since the StoryActions are wrapped into a <keep-alive> component
    const active = ref(true)

    const viewDetails = ref(false)
    const sharingToReportDialog = ref(false)
    const shareToConnectorDialog = ref(false)
    const deleteDialog = ref(false)
    const assessStore = useAssessStore()
    const { newsItemSelection } = storeToRefs(assessStore)
    const userStore = useUserStore()
    const selected = computed(() =>
      assessStore.storySelection.includes(props.story.id)
    )

    const { compactView } = storeToRefs(useFilterStore())

    const allow_edit = computed(() => {
      return Boolean(
        !props.reportView &&
          props.story.news_items.length === 1 &&
          props.story.news_items[0].source == 'manual'
      )
    })

    const news_item_length = computed(() =>
      props.story.news_items ? props.story.news_items.length : 0
    )

    const hasConnectorPermissions = userStore.hasPermission(
      Permissions.CONNECTOR_USER_ACCESS
    )

    function openCard() {
      emit('open-details')
    }

    function markAsRead() {
      assessStore.markStoryAsRead(props.story.id, !props.detailView)
    }

    function markAsImportant() {
      assessStore.markStoryAsImportant(props.story.id, !props.detailView)
    }

    function deleteNewsItem() {
      assessStore.removeStoryByID(props.story.id)
    }

    function shareViaMail() {
      const subject = encodeURIComponent(props.story.title)
      const body = encodeURIComponent(props.story.description)
      window.location.href = `mailto:?subject=${subject}&body=${body}`
    }

    function ungroup() {
      assessStore.ungroupStories([props.story.id])
    }

    function moveSelection() {
      // assessStore.moveSelectionToStory(props.story.id, newsItemSelection.value)
      console.debug('move selection to story', newsItemSelection.value)
    }

    onDeactivated(() => {
      deleteDialog.value = false
      sharingToReportDialog.value = false
      shareToConnectorDialog.value = false
      active.value = false
    })

    onActivated(() => {
      active.value = true
    })

    return {
      active,
      viewDetails,
      selected,
      allow_edit,
      compactView,
      sharingToReportDialog,
      shareToConnectorDialog,
      deleteDialog,
      news_item_length,
      newsItemSelection,
      openCard,
      ungroup,
      shareViaMail,
      markAsRead,
      markAsImportant,
      deleteNewsItem,
      moveSelection,
      hasConnectorPermissions
    }
  }
}
</script>

<style lang="scss" scoped>
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
