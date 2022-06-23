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
          <!--------------------->
          <!-- append to topic -->
          <!--------------------->

          <v-dialog v-model="appendToTopicDialog" width="1024">
            <template v-slot:activator="{ on, attrs }">
              <v-btn
                :ripple="false"
                text
                class="text-lowercase selection-toolbar-btn mr-1 mt-1"
                v-bind="attrs"
                v-on="on"
              >
                <v-icon left>mdi-folder-open-outline</v-icon>
                append to topic
              </v-btn>
            </template>

            <v-card>
              <h2>append to topic</h2>
            </v-card>
          </v-dialog>

          <!------------------>
          <!-- create topic -->
          <!------------------>

          <v-dialog v-model="createTopicDialog" width="1024">
            <template v-slot:activator="{ on, attrs }">
              <v-btn
                :ripple="false"
                text
                class="text-lowercase selection-toolbar-btn mr-1 mt-1"
                v-bind="attrs"
                v-on="on"
              >
                <v-icon left>mdi-folder-plus-outline</v-icon>
                create topic
              </v-btn>
            </template>

            <v-card>
              <h2>create topic</h2>
            </v-card>
          </v-dialog>

          <!------------------>
          <!-- share -->
          <!------------------>

          <v-dialog v-model="shareDialog" width="1024">
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

            <popup-share-items
              v-model="shareDialog"
              :selection="selection"
            />
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
// import PopupShareItems from 'vuex'
import PopupShareItems from '@/components/popups/PopupShareItems'

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
        label: 'create report',
        icon: '$awakeReport'
      },
      {
        label: 'remove from topic',
        icon: '$awakeClose'
      },
      {
        label: 'delete items',
        icon: '$awakeDelete'
      }
    ],
    shareDialog: false,
    appendToTopicDialog: false,
    createTopicDialog: false
  }),
  methods: {

    
  },
  computed: {},
  mounted () {}
}
</script>
