<template>
  <v-bottom-sheet
    v-model="activeSelection"
    persistent
    scroll-strategy="none"
    :retain-focus="false"
    :no-click-animation="true"
    :scrim="false"
  >
    <v-card v-if="storySelection.length > 0" class="story-toolbar">
      <v-card-text class="pa-3">
        <v-row no-gutters>
          <v-col class="toolbar-start">
            <v-btn
              text="add to report"
              variant="outlined"
              color="white"
              prepend-icon="mdi-google-circles-communities"
              @click.stop="actionClicked('addToReport')"
            >
              <v-tooltip
                activator="parent"
                text="[ctrl+shift+s]"
                location="top"
              />
              add to report
            </v-btn>
            <v-btn
              v-if="storySelection.length > 1"
              prepend-icon="mdi-merge"
              variant="outlined"
              class="ml-4"
              @click.stop="actionClicked('merge')"
            >
              <v-tooltip
                activator="parent"
                text="[ctrl+shift+g]"
                location="top"
              />
              merge
            </v-btn>
            <v-btn
              v-if="showUnGroup"
              variant="outlined"
              prepend-icon="mdi-ungroup"
              class="ml-4"
              @click.stop="actionClicked('unGroup')"
            >
              <v-tooltip
                activator="parent"
                text="[ctrl+shift+u]"
                location="top"
              />
              ungroup
            </v-btn>
            <v-btn
              variant="outlined"
              prepend-icon="mdi-eye-check-outline"
              class="ml-4"
              @click.stop="actionClicked('markAsRead')"
            >
              <v-tooltip
                activator="parent"
                text="[ctrl+Space]"
                location="top"
              />
              mark as read
            </v-btn>
            <v-btn
              variant="outlined"
              prepend-icon="mdi-star-outline"
              class="ml-4"
              @click.stop="actionClicked('markAsImportant')"
            >
              <v-tooltip activator="parent" text="[ctrl+i]" location="top" />
              mark as important
            </v-btn>
          </v-col>
          <v-col class="toolbar-end">
            <v-btn
              variant="text"
              prepend-icon="mdi-selection-remove"
              @click.stop="deselectStories"
            >
              <v-tooltip
                activator="parent"
                text="[ESC] deselect all stories"
                location="top"
              />
              deselect
            </v-btn>
            <span class="mx-8">
              Stories selected: <strong>{{ storySelection.length }}</strong>
            </span>
          </v-col>
        </v-row>
        <v-dialog v-model="sharingDialog" width="auto">
          <popup-share-to-report
            :item-ids="storySelection"
            @close="sharingDialog = false"
          />
        </v-dialog>
      </v-card-text>
    </v-card>
    <v-card v-if="newsItemSelection.length > 0" class="news-item-toolbar">
      <v-card-text>
        <v-row no-gutters>
          <v-col class="toolbar-start">
            <v-btn
              variant="outlined"
              prepend-icon="mdi-close-circle-outline"
              @click.stop="actionClicked('remove')"
            >
              remove
              <v-tooltip activator="parent" text="remove from story" />
            </v-btn>
          </v-col>
          <v-col class="toolbar-end">
            <v-btn
              variant="outlined"
              text="deselect"
              prepend-icon="mdi-selection-remove"
              @click.stop="deselectNews"
            >
              <v-tooltip
                activator="parent"
                text="[ESC] deselect all news items"
              />
              deselect
            </v-btn>
            <span class="mx-4">
              News Items selected:
              <strong>{{ newsItemSelection.length }}</strong>
            </span>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </v-bottom-sheet>
</template>

<script>
import { unGroupNewsItems } from '@/api/assess'
import PopupShareToReport from '@/components/popups/PopupShareToReport.vue'
import PopupShareToConnector from '../popups/PopupShareToConnector.vue'
import { useAssessStore } from '@/stores/AssessStore'

import { storeToRefs } from 'pinia'
import { ref, computed } from 'vue'

export default {
  name: 'AssessSelectionToolbar',
  components: {
    PopupShareToReport,
    PopupShareToConnector
  },
  setup() {
    const assessStore = useAssessStore()

    const { storySelection, activeSelection, newsItemSelection, stories } =
      storeToRefs(assessStore)
    const sharingDialog = ref(false)

    const showUnGroup = computed(() => {
      if (storySelection.value.length !== 1) return false

      const story = stories.value.items.filter(
        (item) => item?.id === storySelection.value[0]
      )[0]
      if (story === undefined || story.news_items.length < 2) return false

      return true
    })

    const actionClicked = (action) => {
      if (action === 'merge') {
        assessStore.groupStories()
      } else if (action === 'addToReport') {
        sharingDialog.value = true
      } else if (action === 'remove') {
        unGroupNewsItems(newsItemSelection.value)
      } else if (action === 'unGroup') {
        assessStore.ungroupStories()
      } else if (action === 'markAsRead') {
        assessStore.markSelectionAsRead()
        assessStore.clearSelection()
      } else if (action === 'markAsImportant') {
        assessStore.markSelectionAsImportant()
        assessStore.clearSelection()
      }
    }

    function deselectStories() {
      assessStore.clearStorySelection()
    }

    function deselectNews() {
      assessStore.clearNewsItemSelection()
    }

    return {
      sharingDialog,
      storySelection,
      newsItemSelection,
      activeSelection,
      showUnGroup,
      actionClicked,
      deselectStories,
      deselectNews
    }
  }
}
</script>

<style scoped>
.toolbar-start {
  display: flex;
  align-items: center;
  justify-content: start;
}
.toolbar-end {
  display: flex;
  align-items: center;
  justify-content: end;
}
.story-toolbar {
  background-color: color-mix(
    in srgb,
    rgb(var(--v-theme-primary)) 90%,
    #ffffff
  );
  color: white;
}
.news-item-toolbar {
  background-color: color-mix(
    in srgb,
    rgb(var(--v-theme-secondary)) 80%,
    #ffffff
  );
}
</style>
