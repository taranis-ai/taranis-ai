<template>
  <v-app-bar
    app
    clipped
    bottom
    flat
    dense
    dark
    style="
      bottom: 0px !important;
      top: auto !important;
      height: auto !important;
    "
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

        <v-col
          cols="1"
          class="py-1 d-flex justify-content-center"
          style="min-width: fit-content"
        >
          <span class="mr-2 my-auto selection-indicator">
            selected: <strong>{{ selection.length }}</strong>
          </span>
        </v-col>
      </v-row>
    </v-container>
  </v-app-bar>
</template>

<script>
import {
  deleteNewsItemAggregate,
  groupAction
} from '@/api/assess'

import { notifySuccess, notifyFailure } from '@/utils/helpers'

export default {
  name: 'AssessSelectionToolbar',
  components: { },
  emits: ['refresh'],
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
        icon: 'mdi-delete-circle',
        action: 'deleteItems'
      }
    ],
    appendToStoryDialog: false,
    createStoryDialog: false
  }),
  methods: {
    actionClicked(action) {
      if (action === 'merge') {
        groupAction(this.selection)
          .then(() => {
            notifySuccess('Items merged')
            this.$emit('refresh')
          })
          .catch(err => {
            notifyFailure('Failed to merge items')
            console.log(err)
          })
      } else if (action === 'addToReport') {
        notifySuccess('Not Yet Implemented')
      } else if (action === 'deleteItems') {
        deleteNewsItemAggregate(this.selection)
          .then(() => {
            notifySuccess('Items deleted')
            this.$emit('refresh')
          })
          .catch(err => {
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
