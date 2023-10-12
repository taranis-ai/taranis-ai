<template>
  <v-bottom-navigation density="compact">
    <v-row no-gutters>
      <v-col
        v-if="storySelection.length > 0"
        :cols="startCols"
        class="story-toolbar toolbar-start"
      >
        <v-btn
          v-for="button in storyButtons"
          :key="button.label"
          :ripple="false"
          size="small"
          @click.stop="actionClicked(button.action)"
        >
          <template #prepend>
            <v-icon :icon="button.icon" size="small" class="mr-2" />
          </template>
          {{ button.label }}
        </v-btn>
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
          v-for="button in newsItemButtons"
          :key="button.label"
          :ripple="false"
          size="small"
          @click.stop="actionClicked(button.action)"
        >
          <template #prepend>
            <v-icon :icon="button.icon" size="small" class="mr-2" />
          </template>
          {{ button.label }}
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
import { groupAction, unGroupNewsItems, unGroupStories } from '@/api/assess'
import PopupShareItems from '@/components/popups/PopupShareItems.vue'
import { useAssessStore } from '@/stores/AssessStore'

import { notifySuccess, notifyFailure } from '@/utils/helpers'
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

    const storyButtons = computed(() => {
      const buttons = [
        {
          label: 'add to report',
          icon: 'mdi-google-circles-communities',
          action: 'addToReport'
        }
      ]

      if (storySelection.value.length > 1) {
        return [
          ...buttons,
          {
            label: 'merge',
            icon: 'mdi-merge',
            action: 'merge'
          }
        ]
      }
      return buttons
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

    const newsItemButtons = computed(() => {
      const buttons = [
        {
          label: 'remove',
          icon: 'mdi-close-circle-outline',
          action: 'remove'
        }
      ]
      return buttons
    })

    const actionClicked = (action) => {
      if (action === 'merge') {
        groupAction(storySelection.value)
          .then(() => {
            notifySuccess('Items merged')
            assessStore.clearSelection()
            assessStore.updateNewsItems()
          })
          .catch((err) => {
            notifyFailure('Failed to merge items')
            console.log(err)
          })
      } else if (action === 'addToReport') {
        sharingDialog.value = true
      } else if (action === 'remove') {
        unGroupNewsItems(newsItemSelection.value)
      } else if (action === 'unGroup') {
        unGroupStories(storySelection.value)
      }
    }

    const deselect = () => {
      assessStore.clearSelection()
    }

    return {
      sharingDialog,
      storySelection,
      storyButtons,
      newsItemButtons,
      newsItemSelection,
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
