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
          <!------------------>
          <!-- Merge Topics -->
          <!------------------>

          <v-dialog v-model="mergeDialog" width="1024">
            <template v-slot:activator="{ on, attrs }">
              <v-btn
                :ripple="false"
                text
                class="text-lowercase selection-toolbar-btn mr-1 mt-1"
                v-bind="attrs"
                v-on="on"
              >
                <v-icon left>$awakeMerge</v-icon>
                merge topics
              </v-btn>
            </template>

            <popup-merge-topics
              :dialog="mergeDialog"
              :selection="selection"
              @close="mergeDialog = false"
            />
          </v-dialog>

          <!------------------------>
          <!-- Create Sharing Set -->
          <!------------------------>

          <v-dialog v-model="shareDialog" width="600">
            <template v-slot:activator="{ on, attrs }">
              <v-btn
                :ripple="false"
                text
                class="text-lowercase selection-toolbar-btn mr-1 mt-1"
                v-bind="attrs"
                v-on="on"
              >
                <v-icon left>$awakeShareOutline</v-icon>
                share
              </v-btn>
            </template>

            <v-card>
              <v-card-title>
                <h2
                  class="
                    font-weight-bold
                    headline
                    dark-grey--text
                    text-capitalize
                  "
                >
                  Create Sharing-Set
                </h2>
              </v-card-title>

              <v-card-text>
                Items of Sharingset: <strong>{{ selection }}</strong>
              </v-card-text>

              <v-divider></v-divider>

              <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn
                  color="awake-red-color darken-1"
                  outlined
                  @click="shareDialog = false"
                  class="text-lowercase"
                >
                  <v-icon left class="red-icon">$awakeClose</v-icon>
                  abort
                </v-btn>
                <v-btn
                  color="primary"
                  dark
                  depressed
                  @click="shareDialog = false"
                  class="text-lowercase selection-toolbar-btn"
                >
                  <v-icon left>$awakeShare</v-icon>
                  share
                </v-btn>
              </v-card-actions>
            </v-card>
          </v-dialog>

          <!------------------>
          <!-- Pin Selected -->
          <!------------------>

          <v-btn
            :ripple="false"
            text
            class="text-lowercase selection-toolbar-btn mr-1 mt-1"
            @click="pinSelected"
          >
            <v-icon left>$awakePin</v-icon>
            pin selected
          </v-btn>

          <!--------------------->
          <!-- Delete Selected -->
          <!--------------------->

          <v-btn
            :ripple="false"
            text
            class="text-lowercase selection-toolbar-btn mr-1 mt-1"
            @click="pinSelected"
          >
            <v-icon left>$awakeDelete</v-icon>
            delete selected
          </v-btn>

          <!------------------>
          <!-- Unselect All -->
          <!------------------>

          <v-btn
            :ripple="false"
            text
            class="text-lowercase selection-toolbar-btn mr-1 mt-1"
            @click="unselectAll"
          >
            <v-icon left>$awakeClose</v-icon>
            unselect all
          </v-btn>
        </v-col>

        <!--------------------->
        <!-- Selection Count -->
        <!--------------------->

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
import { mapActions } from 'vuex'
import PopupMergeTopics from '@/components/popups/PopupMergeTopics'

export default {
  name: 'DashboardSelectionToolbar',
  components: {
    PopupMergeTopics
  },
  props: {
    selection: []
  },
  data: () => ({
    mergeDialog: false,
    shareDialog: false
  }),
  methods: {
    ...mapActions('dashboard', ['pinTopic', 'unselectAllTopics']),

    pinSelected: function () {
      this.selection.forEach((id) => {
        this.pinTopic(id)
      })
    },

    unselectAll: function () {
      this.unselectAllTopics()
    }
  },
  computed: {},
  mounted () {}
}
</script>
