<template>
  <v-app-bar
    app
    clipped
    bottom
    flat
    dense
    dark
    color="primary"
    class="selection-toolbar"
  >
    <v-container class="py-1">
      <v-row>
        <v-col class="py-0">
          <v-btn
            v-for="button in actionButtons"
            :key="button.label"
            :ripple="false"
            @click.stop="actionClicked(button.action)"
            text
            class="text-lowercase selection-toolbar-btn mr-1 mt-1"
          >
            <v-icon left>{{ button.icon }}</v-icon>
            {{ button.label }}
          </v-btn>
        </v-col>

        <v-col cols="1" class="py-1 d-flex">
          <span class="mr-2 my-auto selection-indicator">
            selected: <strong>{{ selection.length }}</strong>
          </span>
        </v-col>
      </v-row>
      <v-dialog :value="sharingDialog" width="auto">
        <popup-share-items
          :item_ids="selection"
          @close="sharingDialog = false"
        />
      </v-dialog>
    </v-container>
  </v-app-bar>
</template>

<script>
import { deleteNewsItemAggregate, groupAction } from '@/api/assess'
import PopupShareItems from '@/components/popups/PopupShareItems'

import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { mapActions } from 'vuex'

export default {
  name: 'AssessSelectionToolbar',
  components: {
    PopupShareItems
  },
  props: {
    selection: []
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
      },
      {
        label: 'delete items',
        icon: 'mdi-delete-outline',
        action: 'deleteItems'
      }
    ],
    sharingDialog: false
  }),
  methods: {
    ...mapActions('assess', ['clearNewsItemSelection', 'updateNewsItems']),

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
      } else if (action === 'deleteItems') {
        deleteNewsItemAggregate(this.selection)
          .then(() => {
            notifySuccess('Items deleted')
            this.clearNewsItemSelection()
            this.updateNewsItems()
          })
          .catch((err) => {
            notifyFailure('Failed to delete items')
            console.log(err)
          })
      }
    }
  },
  computed: {},
  mounted() {}
}
</script>
