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
export default {
  name: 'AssessSelectionToolbar',
  components: { },
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
      console.log('action clicked: ', action)
      this.$emit('actionClicked', action)
    }
  },
  computed: {},
  mounted() {}
}
</script>
