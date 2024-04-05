<template>
  <v-bottom-navigation density="compact">
    <v-row no-gutters>
      <v-col
        v-if="storySelection.length > 0"
        :cols="startCols"
        class="story-toolbar toolbar-start"
      >
        <v-btn
          text="add to report"
          size="small"
          prepend-icon="mdi-google-circles-communities"
          @click.stop="actionClicked('addToReport')"
        />
        <v-btn
          v-if="storySelection.length > 1"
          text="merge"
          size="small"
          prepend-icon="mdi-merge"
          @click.stop="actionClicked('merge')"
        />
        <v-btn
          v-if="showUnGroup"
          text="ungroup"
          size="small"
          prepend-icon="mdi-ungroup"
          @click.stop="actionClicked('unGroup')"
        />
        <v-btn
          text="mark as read"
          size="small"
          :ripple="false"
          prepend-icon="mdi-eye-check-outline"
          @click.stop="actionClicked('markAsRead')"
        />
        <v-btn
          text="mark as important"
          size="small"
          :ripple="false"
          prepend-icon="mdi-star"
          @click.stop="actionClicked('markAsImportant')"
        />
      </v-col>
      <v-col
        v-if="storySelection.length > 0"
        :cols="startCols / 2"
        class="story-toolbar toolbar-end"
      >
        <v-btn size="small" @click.stop="deselect">
          <template #prepend>
            <v-icon icon="mdi-selection-remove" size="small" class="mr-2" />
          </template>
          deselect
        </v-btn>
        <span class="mx-4">
          Stories selected: <strong>{{ storySelection.length }}</strong>
        </span>
      </v-col>
      <v-col
        v-if="newsItemSelection.length > 0"
        :cols="startCols"
        class="news-item-toolbar toolbar-start"
      >
        <v-btn
          :ripple="false"
          size="small"
          prepend-icon="mdi-close-circle-outline"
          @click.stop="actionClicked('remove')"
        >
          remove
          <v-tooltip activator="parent" text="remove from story" />
        </v-btn>
      </v-col>
      <v-col
        v-if="newsItemSelection.length > 0"
        :cols="startCols / 2"
        class="news-item-toolbar toolbar-end"
      >
        <v-btn size="small" @click.stop="deselect">
          <template #prepend>
            <v-icon icon="mdi-selection-remove" size="small" class="mr-2" />
          </template>
          deselect
        </v-btn>
        <span class="mx-4">
          News Items selected: <strong>{{ newsItemSelection.length }}</strong>
        </span>
      </v-col>
    </v-row>
    <v-dialog v-model="sharingDialog" width="auto">
      <popup-share-items
        :item-ids="storySelection"
        @close="sharingDialog = false"
      />
    </v-dialog>
  </v-bottom-navigation>
</template>

<script>
import { unGroupNewsItems } from '@/api/assess'
import PopupShareItems from '@/components/popups/PopupShareItems.vue'
import { useAssessStore } from '@/stores/AssessStore'

import { storeToRefs } from 'pinia'
import { ref, computed } from 'vue'

export default {
  name: 'AssessSelectionToolbar',
  components: {
    PopupShareItems
  },
  setup() {
    const assessStore = useAssessStore()
    const { storySelection, newsItemSelection } = storeToRefs(assessStore)
    const sharingDialog = ref(false)

    const showUnGroup = computed(() => {
      if (storySelection.value.length !== 1) return false

      const story = assessStore.getStoryByID(storySelection.value[0])
      if (story === undefined || story.news_items.length < 2) return false

      return true
    })

    const startCols = computed(() => {
      if (
        storySelection.value.length > 0 &&
        newsItemSelection.value.length > 0
      ) {
        return 4
      }
      return 8
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
      } else if (action === 'markAsImportant') {
        assessStore.markSelectionAsImportant()
      }
    }

    const deselect = () => {
      assessStore.clearSelection()
    }

    return {
      sharingDialog,
      storySelection,
      newsItemSelection,
      showUnGroup,
      startCols,
      actionClicked,
      deselect
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
