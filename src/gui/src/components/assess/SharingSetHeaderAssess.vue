<template>
  <div class="sharingset-header-container">
    <v-container class="mx-3 pa-5 pb-5">
      <v-row class="card-padding my-4" no-gutters>
        <v-col class="headline card-alignment mb-4" cols="12" sm="12" md="7">
          <h3 class="pl-3">Sharing Set</h3>

          <h1 class="pl-3 text-capitalize">
            {{ topic.title }}
          </h1>
        </v-col>
      </v-row>
      <v-row class="card-padding mt-5" no-gutters>
        <v-col cols="12" sm="12" md="7" class="pr-5 card-alignment">
          <v-container column class="pt-0" style="height: 100%">
            <v-row no-gutters style="height: 100%">
              <v-col class="d-flex flex-column pt-2" style="height: 100%">
                <v-row class="flex-grow-0">
                  <v-col
                    cols="12"
                    class="mx-0 px-0 d-flex justify-start flex-wrap pt-1 pb-4"
                  >
                    <p class="topic-summary">
                      {{ topic.summary }}
                    </p>
                  </v-col>
                </v-row>

                <v-row class="flex-grow-0">
                  <v-col
                    cols="12"
                    class="
                      mx-0
                      px-0
                      d-flex
                      justify-start
                      flex-wrap
                      pt-1
                      pb-0
                      dark-grey--text
                    "
                  >
                    <h3>Activity over time</h3>
                  </v-col>
                </v-row>
                <v-row class="flex-grow-0">
                  <v-col
                    cols="12"
                    class="mx-0 px-0 d-flex justify-start flex-wrap pt-1 pb-4"
                  >
                    <calendar-heatmap
                      class="calendar-heatmap"
                      :values="getMetaData().heatmapData"
                      :endDate="getHeatmapEndDate()"
                      tooltip-unit="published items"
                      :range-color="[
                        'rgb(185, 210, 227)',
                        '#e9c645',
                        '#db993f',
                        '#bc482b',
                        '#8f0429',
                      ]"
                    />
                  </v-col>
                </v-row>

                <v-spacer></v-spacer>

                <v-row
                  no-gutter
                  wrap
                  align="center"
                  justify="end"
                  class="flex-grow-0 mt-0"
                >
                  <v-col
                    cols="12"
                    class="mx-0 px-0 d-flex justify-start flex-wrap py-1"
                  >
                    <!------------------>
                    <!-- Edit Topics -->
                    <!------------------>

                    <v-dialog v-model="editDialog" width="600">
                      <template v-slot:activator="{ on, attrs }">
                        <v-btn
                          depressed
                          class="text-lowercase topic-header-btn mr-2 mt-1"
                          v-bind="attrs"
                          v-on="on"
                        >
                          <v-icon left>$awakeEdit</v-icon>
                          edit
                        </v-btn>
                      </template>

                      <popup-edit-topic
                        :dialog="editDialog"
                        :topic="topic"
                        @close="editDialog = false"
                        v-on:update:title="topic.title = $event"
                      />
                    </v-dialog>

                    <v-btn
                      depressed
                      class="text-lowercase topic-header-btn mr-2 mt-1"
                    >
                      <v-icon left>mdi-message-outline</v-icon>
                      comments
                    </v-btn>

                    <v-dialog v-model="shareDialog" width="600">
                      <template v-slot:activator="{ on, attrs }">
                        <v-btn
                          depressed
                          class="text-lowercase topic-header-btn mr-2 mt-1"
                          v-bind="attrs"
                          v-on="on"
                        >
                          <v-icon left>$awakeShareOutline</v-icon>
                          share with
                        </v-btn>
                      </template>

                      <popup-share-sharing-set
                        v-model:dialog="shareDialog"
                        :sharingSet="topic"
                        :currentRecipientList="getSharedWith()"
                        :hasRestrictedItems="
                          getMetaData().numberRestrictedItems > 0
                        "
                      />
                    </v-dialog>
                  </v-col>
                </v-row>
              </v-col>
            </v-row>
          </v-container>
        </v-col>

        <v-divider vertical class="d-none d-sm-flex"></v-divider>
        <v-divider class="d-flex d-sm-none"></v-divider>

        <v-col
          cols="12"
          sm="12"
          md="5"
          class="d-flex flex-column"
          align-self="start"
          style="height: 100%"
        >
          <v-container column class="py-0" style="height: 100%">
            <v-row class="topic-header-meta-infos">
              <v-col class="topic-header-meta-infos-label">
                <strong>Status:</strong>
              </v-col>
              <v-col>
                <tag-mini
                  :label="getSharingState().label"
                  :color="getSharingState().color"
                />
              </v-col>
            </v-row>
            <v-row class="topic-header-meta-infos">
              <v-col class="topic-header-meta-infos-label">
                <strong>Direction:</strong>
              </v-col>
              <v-col>
                <span v-if="topic.sharingDirection === 'outgoing'">
                  <v-icon small left class="icon-color-grey"
                    >$awakeShareOutline</v-icon
                  >
                  outgoing
                </span>

                <span v-else>
                  <v-icon small left class="flipped-icon icon-color-grey"
                    >$awakeShare</v-icon
                  >
                  incoming
                </span>
              </v-col>
            </v-row>
            <v-row class="topic-header-meta-infos">
              <v-col class="topic-header-meta-infos-label">
                <strong>Shared by:</strong>
              </v-col>
              <v-col>
                {{ topic.sharedBy }}
              </v-col>
            </v-row>
            <v-row class="topic-header-meta-infos">
              <v-col class="topic-header-meta-infos-label">
                <strong>Shared with:</strong>
              </v-col>
              <v-col>
                {{ getSharedWith() }}
              </v-col>
            </v-row>
            <v-row class="topic-header-meta-infos">
              <v-col class="topic-header-meta-infos-label">
                <strong>Last activity:</strong>
              </v-col>
              <v-col> {{ getLastActivity() }} </v-col>
            </v-row>
            <v-row class="topic-header-meta-infos">
              <v-col class="topic-header-meta-infos-label">
                <strong>Total/new items:</strong>
              </v-col>
              <v-col>
                <v-icon left small>mdi-file-outline</v-icon>
                {{ topic.items.total }} / <strong>{{ topic.items.new }}</strong>
              </v-col>
            </v-row>
            <v-row class="topic-header-meta-infos">
              <v-col class="topic-header-meta-infos-label">
                <strong>Comments:</strong>
              </v-col>
              <v-col>
                <v-icon left small>mdi-message-outline</v-icon>
                {{ topic.comments.total }} /
                <strong>{{ topic.comments.new }}</strong>
              </v-col>
            </v-row>

            <v-row class="topic-header-meta-infos">
              <v-col class="topic-header-meta-infos-label">
                <strong>Shared Items:</strong>
              </v-col>
              <v-col>
                <v-icon left small class="icon-color-grey"
                  >$awakeShareOutline</v-icon
                >
                <span>{{ getMetaData().numberSharedItems }}</span>
              </v-col>
            </v-row>
            <v-row class="topic-header-meta-infos">
              <v-col class="topic-header-meta-infos-label">
                <strong>Restricted Items:</strong>
              </v-col>
              <v-col>
                <v-icon left small>mdi-lock-outline</v-icon>
                <span>{{ getMetaData().numberRestrictedItems }}</span>
              </v-col>
            </v-row>
            <v-row class="topic-header-meta-infos">
              <v-col class="topic-header-meta-infos-label">
                <strong>Keywords:</strong>
              </v-col>
              <v-col>
                <span class="text-capitalize">{{ getKeywords() }}</span>
              </v-col>
            </v-row>

            <v-row class="topic-header-meta-infos">
              <v-col class="topic-header-meta-infos-label d-flex align-center">
                <strong>Tags:</strong>
              </v-col>
              <v-col>
                <tag-norm
                  v-for="tag in topic.tags"
                  :key="tag.label"
                  :tag="tag"
                />
              </v-col>
            </v-row>
          </v-container>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script>
import moment from 'moment'

import TagMini from '@/components/common/tags/TagMini'
import TagNorm from '@/components/common/tags/TagNorm'
import { CalendarHeatmap } from 'vue-calendar-heatmap'
import { mapGetters } from 'vuex'
import PopupEditTopic from '@/components/popups/PopupEditTopic'
import PopupShareSharingSet from '@/components/popups/PopupShareSharingSet'

// import { mapState } from 'vuex'

export default {
  name: 'SharingSetHeaderAssess',
  components: {
    TagMini,
    TagNorm,
    CalendarHeatmap,
    PopupEditTopic,
    PopupShareSharingSet
  },
  data: () => ({
    editDialog: false,
    shareDialog: false
  }),
  props: {
    topic: {}
  },
  methods: {
    ...mapGetters('dashboard', ['getTopicById', 'getTopicTitleById']),
    ...mapGetters('assess', ['getNewsItemsByTopicId']),
    ...mapGetters('users', ['getUsernameById']),

    getSharingState () {
      switch (this.topic.sharingState) {
        case 'shared':
          return { label: 'shared', color: 'awake-green-color' }
        case 'pending':
          return { label: 'pending', color: 'awake-yellow-color' }
        default:
          return { label: 'not shared yet', color: 'awake-red-color' }
      }
    },
    getLastActivity () {
      return moment(this.topic.lastActivity).format('DD/MM/YYYY hh:mm:ss')
    },
    getRelatedTopics () {
      return this.topic.relatedTopics.join(', ')
    },
    getKeywords () {
      return this.topic.keywords.join(', ')
    },
    getSharedWith () {
      return this.topic.sharedWith.length
        ? this.topic.sharedWith
          .map((recipientId) => this.getUsernameById()(recipientId.id))
          .join(', ')
        : '-'
    },
    getMetaData () {
      const heatmapCounter = {}
      let numberSharedItems = 0
      let numberRestrictedItems = 0
      const newsItems = this.getNewsItemsByTopicId()(this.topic.id)

      newsItems.forEach((element) => {
        const date = moment(element.published).format('YYYY/MM/DD')
        heatmapCounter[date] = heatmapCounter[date] || 0
        heatmapCounter[date]++

        if (element.shared) numberSharedItems++

        if (element.restricted) numberRestrictedItems++
      })

      return {
        heatmapData: Object.entries(heatmapCounter).map((e) => ({
          date: [e[0]],
          count: e[1]
        })),
        numberSharedItems: numberSharedItems,
        numberRestrictedItems: numberRestrictedItems
      }
    },
    getHeatmapEndDate () {
      return moment(new Date()).format('YYYY/MM/DD')
    }
  }
}
</script>
