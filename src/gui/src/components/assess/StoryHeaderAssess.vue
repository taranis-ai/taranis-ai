<template>
  <div class="story-header-container">
    <v-container class="mx-3 pa-5 pb-5">
      <v-row class="card-padding my-4" no-gutters>
        <v-col class="headline card-alignment mb-4" cols="12" sm="12" md="7">
          <h3 class="pl-3">Story</h3>
          <h1 class="pl-3 text-capitalize">
            {{ story.title }}
          </h1>
        </v-col>
      </v-row>
      <v-row class="card-padding mt-5" no-gutters>
        <v-col cols="12" sm="12" md="7" class="card-alignment">
          <v-container column class="pt-0" style="height: 100%">
            <v-row no-gutters style="height: 100%">
              <v-col class="d-flex flex-column pt-2" style="height: 100%">
                <v-row class="flex-grow-0">
                  <v-col
                    cols="12"
                    class="mx-0 px-0 d-flex justify-start flex-wrap pt-1 pb-4"
                  >
                    <p class="story-summary">
                      {{ story.summary }}
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
                        '#d6d29d',
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
                    <!-- Edit Stories -->
                    <!------------------>

                    <v-dialog v-model="editDialog" width="600">
                      <template v-slot:activator="{ on, attrs }">
                        <v-btn
                          depressed
                          class="text-lowercase story-header-btn mr-2 mt-1"
                          v-bind="attrs"
                          v-on="on"
                        >
                          <v-icon left>mdi-file-edit</v-icon>
                          edit
                        </v-btn>
                      </template>

                      <popup-edit-story
                        :dialog="editDialog"
                        :story="story"
                        @close="editDialog = false"
                        v-on:update:title="story.title = $event"
                      />
                    </v-dialog>

                    <v-btn
                      depressed
                      class="text-lowercase story-header-btn mr-2 mt-1"
                    >
                      <v-icon left>mdi-message-outline</v-icon>
                      comments
                    </v-btn>
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
            <v-row class="story-header-meta-infos">
              <v-col class="story-header-meta-infos-label">
                <strong>Last activity:</strong>
              </v-col>
              <v-col> {{ $d(getLastActivity(), 'long') }} </v-col>
            </v-row>
            <v-row class="story-header-meta-infos">
              <v-col class="story-header-meta-infos-label">
                <strong>Total/new items:</strong>
              </v-col>
              <v-col>
                <v-icon left small>mdi-file-outline</v-icon>
                {{ story.items.total }} / <strong>{{ story.items.new }}</strong>
              </v-col>
            </v-row>
            <v-row class="story-header-meta-infos">
              <v-col class="story-header-meta-infos-label">
                <strong>Comments:</strong>
              </v-col>
              <v-col>
                <v-icon left small>mdi-message-outline</v-icon>
                {{ story.comments.total }} /
                <strong>{{ story.comments.new }}</strong>
              </v-col>
            </v-row>
            <v-row class="story-header-meta-infos">
              <v-col class="story-header-meta-infos-label">
                <strong>Story upvotes:</strong>
              </v-col>
              <v-col>
                <v-icon left small color="awake-green-color"
                  >mdi-arrow-up-circle-outline</v-icon
                >
                {{ story.votes.up }}
              </v-col>
            </v-row>
            <v-row class="story-header-meta-infos">
              <v-col class="story-header-meta-infos-label">
                <strong>Story downvotes:</strong>
              </v-col>
              <v-col>
                <v-icon left small color="awake-red-color"
                  >mdi-arrow-down-circle-outline</v-icon
                >
                {{ story.votes.down }}
              </v-col>
            </v-row>

            <v-row class="story-header-meta-infos">
              <v-col class="story-header-meta-infos-label">
                <strong>Sharing Sets:</strong>
              </v-col>
              <v-col>
                <span class="text-capitalize">{{
                  getMetaData().sharingSets
                }}</span>
              </v-col>
            </v-row>
            <v-row class="story-header-meta-infos">
              <v-col class="story-header-meta-infos-label">
                <strong>Shared Items:</strong>
              </v-col>
              <v-col>
                <v-icon left small class="icon-color-grey"
                  >mdi-share-outline</v-icon
                >
                <span>{{ getMetaData().numberSharedItems }}</span>
              </v-col>
            </v-row>
            <v-row class="story-header-meta-infos">
              <v-col class="story-header-meta-infos-label">
                <strong>Restricted Items:</strong>
              </v-col>
              <v-col>
                <v-icon left small>mdi-lock-outline</v-icon>
                <span>{{ getMetaData().numberRestrictedItems }}</span>
              </v-col>
            </v-row>
            <v-row class="story-header-meta-infos">
              <v-col class="story-header-meta-infos-label">
                <strong>Keywords:</strong>
              </v-col>
              <v-col>
                <span class="text-capitalize">{{ getKeywords() }}</span>
              </v-col>
            </v-row>
            <v-row class="story-header-meta-infos">
              <v-col class="story-header-meta-infos-label">
                <strong>Related Stories:</strong>
              </v-col>
              <v-col>
                <span class="text-capitalize">{{
                  getMetaData().relatedStories
                }}</span>
              </v-col>
            </v-row>

            <v-row class="story-header-meta-infos">
              <v-col class="story-header-meta-infos-label d-flex align-center">
                <strong>Tags:</strong>
              </v-col>
              <v-col>
                <tag-norm
                  v-for="tag in story.tags"
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
import TagNorm from '@/components/common/tags/TagNorm'
import { CalendarHeatmap } from 'vue-calendar-heatmap'
import { mapGetters } from 'vuex'
import PopupEditStory from '@/components/popups/PopupEditStory'

// import { mapState } from 'vuex'

export default {
  name: 'StoryHeaderAssess',
  components: {
    TagNorm,
    CalendarHeatmap,
    PopupEditStory
  },
  data: () => ({
    editDialog: false,
    story: this.storyprop
  }),
  props: {
    storyprop: {}
  },
  methods: {
    ...mapGetters('dashboard', ['getStoryTitleById']),
    ...mapGetters('assess', ['getNewsItemsByStoryId']),

    getLastActivity () {
      return new Date(this.story.lastActivity)
    },
    getKeywords () {
      return this.story.keywords.join(', ')
    },
    getMetaData () {
      const heatmapCounter = {}
      let numberSharedItems = 0
      let numberRestrictedItems = 0
      const newsItems = this.getNewsItemsByStoryId()(this.story.id)
      const metaSharingSetsList = []
      const metaRelatedStoryList = []

      newsItems.forEach((element) => {
        const date = new Date(element.published)
        heatmapCounter[date] = heatmapCounter[date] || 0
        heatmapCounter[date]++

        if (element.shared) numberSharedItems++

        if (element.restricted) numberRestrictedItems++

        if (element.sharingSets.length) {
          element.sharingSets.forEach((sharingSetId) => {
            const newSharingset = this.getStoryTitleById()(sharingSetId)
            if (metaSharingSetsList.indexOf(newSharingset) === -1) {
              metaSharingSetsList.push(newSharingset)
            }
          })
        }
      })

      this.story.relatedStories.forEach((relatedStoryId) => {
        const newRelatedStory = this.getStoryTitleById()(relatedStoryId)
        if (metaRelatedStoryList.indexOf(newRelatedStory) === -1) {
          metaRelatedStoryList.push(newRelatedStory)
        }
      })

      return {
        heatmapData: Object.entries(heatmapCounter).map((e) => ({
          date: [e[0]],
          count: e[1]
        })),
        numberSharedItems: numberSharedItems,
        numberRestrictedItems: numberRestrictedItems,
        sharingSets: metaSharingSetsList.length
          ? metaSharingSetsList.join(', ')
          : '-',
        relatedStories: metaRelatedStoryList.length
          ? metaRelatedStoryList.join(', ')
          : '-'
      }
    },
    getHeatmapEndDate () {
      return new Date()
    }
  }
}
</script>
