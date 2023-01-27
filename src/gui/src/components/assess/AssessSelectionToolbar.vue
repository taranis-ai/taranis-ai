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
          <v-dialog v-model="appendToStoryDialog" width="1024">
            <template v-slot:activator="{ on, attrs }">
              <v-btn
                :ripple="false"
                text
                class="text-lowercase selection-toolbar-btn mr-1 mt-1"
                v-bind="attrs"
                v-on="on"
              >
                <v-icon left>mdi-folder-open-outline</v-icon>
                append to story
              </v-btn>
            </template>

            <v-card>
              <h2>append to story</h2>
            </v-card>
          </v-dialog>

          <!------------------>
          <!-- create story -->
          <!------------------>

          <v-dialog v-model="createStoryDialog" width="1024">
            <template v-slot:activator="{ on, attrs }">
              <v-btn
                :ripple="false"
                text
                class="text-lowercase selection-toolbar-btn mr-1 mt-1"
                v-bind="attrs"
                v-on="on"
              >
                <v-icon left>mdi-folder-plus-outline</v-icon>
                create story
              </v-btn>
            </template>

            <v-card>
              <h2>create story</h2>
            </v-card>
          </v-dialog>

          <v-btn
            v-for="button in actionButtons"
            :key="button.label"
            :ripple="false"
            text
            class="text-lowercase selection-toolbar-btn mr-1 mt-1"
          >
            <v-icon left>{{ button.icon }}</v-icon>
            {{ button.label }}
          </v-btn>
        </v-col>

        <!-- <v-spacer></v-spacer> -->

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
        label: 'delete items',
        icon: '$awakeDelete'
      }
    ],
    appendToStoryDialog: false,
    createStoryDialog: false
  }),
  methods: {},
  computed: {},
  mounted() {}
}
</script>
