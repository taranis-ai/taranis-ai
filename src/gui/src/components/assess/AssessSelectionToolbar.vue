<template>
  <v-bottom-navigation density="compact" bg-color="primary">
    <v-btn
      v-for="button in actionButtons"
      :key="button.label"
      :ripple="false"
      size="small"
      class="text-lowercase"
      @click.stop="actionClicked(button.action)"
    >
      <v-icon :icon="button.icon" />
      {{ button.label }}
    </v-btn>
    <v-spacer />
    <span class="my-auto mr-5">
      selected: <strong>{{ selection.length }}</strong>
    </span>
    <v-dialog v-model="sharingDialog" width="auto">
      <popup-share-items :item-ids="selection" @close="sharingDialog = false" />
    </v-dialog>
  </v-bottom-navigation>
</template>

<script>
import { groupAction } from '@/api/assess'
import PopupShareItems from '@/components/popups/PopupShareItems.vue'
import { useAssessStore } from '@/stores/AssessStore'

import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { mapActions } from 'pinia'

export default {
  name: 'AssessSelectionToolbar',
  components: {
    PopupShareItems
  },
  props: {
    selection: {
      type: Array,
      default: () => []
    }
  },
  data: () => ({
    actionButtons: [
      {
        label: 'merge',
        icon: 'mdi-merge',
        action: 'merge'
      },
      {
        label: 'add to report',
        icon: 'mdi-google-circles-communities',
        action: 'addToReport'
      }
    ],
    sharingDialog: false
  }),
  methods: {
    ...mapActions(useAssessStore, [
      'clearNewsItemSelection',
      'updateNewsItems'
    ]),

    actionClicked(action) {
      if (action === 'merge') {
        groupAction(this.selection)
          .then(() => {
            notifySuccess('Items merged')
            this.clearNewsItemSelection()
            this.updateNewsItems()
          })
          .catch((err) => {
            notifyFailure('Failed to merge items')
            console.log(err)
          })
      } else if (action === 'addToReport') {
        this.sharingDialog = true
      }
    }
  }
}
</script>
