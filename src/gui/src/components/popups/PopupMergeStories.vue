<template>
  <v-card>
    <v-form ref="form" v-model="valid">
      <v-container>
        <v-row>
          <v-col cols="12">
            <h2 class="popup-title pb-2">Merge Stories</h2>
            The following stories were selected for merging:
          </v-col>
        </v-row>
        <v-row no-gutters>
          <v-col>
            <v-container fluid style="padding: 18px 5px">
              <v-row>
                <v-col
                  v-for="storyId in selection"
                  :key="storyId"
                  class="d-flex pa-1"
                  align-self="start"
                >
                  <v-card
                    elevation="0"
                    tile
                    height="100%"
                    class="merge-story-details"
                  >
                    <v-row justify="start" no-gutters class="flex-grow-0">
                      <v-col>
                        <h4 class="merge-stories-details-title my-2">
                          {{ getStoryDetails(storyId).title }}
                        </h4>
                      </v-col>
                    </v-row>

                    <v-spacer></v-spacer>
                    <v-divider></v-divider>

                    <v-row
                      justify="end"
                      no-gutters
                      class="flex-grow-0 my-2 merge-stories-details-meta"
                    >
                      <v-col
                        cols="12"
                        v-if="getStoryDetails(storyId).isSharingSet"
                      >
                        <v-icon left x-small class="mr-1 flipped-icon"
                          >mdi-share</v-icon
                        >
                        Shared Set
                      </v-col>
                      <v-col cols="12" v-else>
                        <v-icon left x-small class="mr-1 flipped-icon"
                          >mdi-folder-outline</v-icon
                        >
                        Local Story
                      </v-col>

                      <v-col cols="12">
                        <v-icon left x-small class="mr-1"
                          >mdi-file-outline</v-icon
                        >
                        {{ getStoryDetails(storyId).items.total }}/
                        <strong>{{
                          getStoryDetails(storyId).items.new
                        }}</strong>
                      </v-col>
                    </v-row>
                  </v-card>
                </v-col>
              </v-row>
            </v-container>
          </v-col>
        </v-row>
      </v-container>

      <v-container class="pb-5 mb-5">
        <v-row>
          <v-col class="py-1">
            <h4 class="merge-stories-details-title">Merge Options</h4>
          </v-col>
        </v-row>
        <v-row>
          <!----------->
          <!-- Title -->
          <!----------->

          <v-col class="py-2">
            <text-field v-model="mergeTitle" label="Story Title" />
          </v-col>
        </v-row>
        <v-row class="mt-2">
          <!------------->
          <!-- Summary -->
          <!------------->

          <v-col cols="12" class="py-0">
            <switch-field
              v-model="generateSummary"
              label="auto-generate summary"
            />
          </v-col>
          <v-expand-transition appear v-if="!generateSummary">
            <v-col cols="12" class="py-0 pt-2">
              <v-textarea
                v-model="mergeSummary"
                label="Summary"
                hide-details
                outlined
              ></v-textarea>
            </v-col>
          </v-expand-transition>

          <!--------------------->
          <!-- Keep discussion -->
          <!--------------------->

          <v-col cols="8" class="py-0">
            <switch-field v-model="mergeDiscussion" label="keep discussion" />
          </v-col>
          <v-col
            cols="4"
            class="py-0 merge-stories-details-meta grey--text text--darken-2"
          >
            <div class="mt-5 mr-2 text-right">
              <v-icon left x-small class="mr-1 grey--text text--darken-2"
                >mdi-message-outline</v-icon
              >
              {{ storyPrototype.comments.total }}/
              <strong>{{ storyPrototype.comments.new }}</strong>
            </div>
          </v-col>

          <!----------------->
          <!-- Merge Votes -->
          <!----------------->

          <v-col cols="8" class="py-0">
            <switch-field v-model="mergeVotes" label="merge up-/downvotes" />
          </v-col>
          <v-col cols="4" class="py-0 merge-stories-details-meta">
            <div class="mt-5 mr-2 text-right grey--text text--darken-2">
              <v-icon left x-small class="mr-1 grey--text text--darken-2"
                >mdi-arrow-up-circle-outline</v-icon
              >
              {{ storyPrototype.votes.up }}
              <v-icon left x-small class="mr-1 ml-2 grey--text text--darken-2"
                >mdi-arrow-down-circle-outline</v-icon
              >
              {{ storyPrototype.votes.down }}
            </div>
          </v-col>

          <!--------------------->
          <!-- Delete original -->
          <!--------------------->

          <v-col cols="12" class="py-0">
            <switch-field v-model="deleteOld" label="delete selected stories" />
          </v-col>
        </v-row>
      </v-container>

      <v-divider></v-divider>

      <v-card-actions class="mt-3">
        <v-spacer></v-spacer>

        <button-outlined
          label="cancel"
          icon="mdi-close"
          color="awake-red-color"
          extraClass="mr-2"
          @click="$emit('close')"
        />

        <button-outlined
          label="merge stories"
          icon="mdi-merge"
          color="primary"
          @click="mergeSelectedStories()"
        />
      </v-card-actions>
    </v-form>
  </v-card>
</template>

<script>
import { mapActions, mapGetters } from 'vuex'
import { xorConcat } from '@/utils/helpers'

import buttonOutlined from '@/components/_subcomponents/buttonOutlined'
import textField from '@/components/_subcomponents/textField'
import switchField from '@/components/_subcomponents/switchField'

export default {
  name: 'PopupMergeStories',
  components: {
    buttonOutlined,
    textField,
    switchField
  },
  props: {
    dialog: Boolean,
    selection: []
  },
  data: () => ({
    valid: true,
    generateSummary: true,
    mergeDiscussion: true,
    mergeVotes: true,
    deleteOld: true,
    mergeTitle: '',
    mergeSummary: ''
  }),
  methods: {
    ...mapActions('dashboard', [
      'pinStory',
      'unselectAllStories',
      'removeStoryById',
      'createStory'
    ]),
    ...mapActions('assess', [
      'deselectNewsItem',
      'deselectAllNewsItems',
      'assignSharingSet',
      'changeMergeAttr'
    ]),
    ...mapGetters('dashboard', ['getStoryById']),

    getStoryDetails (id) {
      return this.getStoryById()(parseInt(id))
    },

    mergeSelectedStories () {
      // Add Form Validation

      const oldStories = [...this.selection]

      const mergedStory = this.storyPrototype
      mergedStory.title = this.mergeTitle
      mergedStory.summary = this.mergeSummary
        ? this.mergeSummary
        : 'this is an AI created summary ... ' // should be replaced by NLP algorithm
      mergedStory.id = Math.floor(Math.random() * (1000 - 800 + 1)) + 800

      // reset selection
      this.unselectAllStories()

      // remove old stories
      if (this.deleteOld) {
        this.selection.forEach((id) => this.removeStoryById(id))
      }

      this.createStory(mergedStory)
      this.changeMergeAttr({ src: oldStories, dest: mergedStory.id })

      // Close Popup
      this.$emit('close')
    }
  },
  computed: {
    storyPrototype () {
      const newStory = {
        id: null,
        relevanceScore: 100,
        title: '',
        tags: [],
        ai: false,
        originator: '',
        hot: false,
        pinned: true,
        lastActivity: null,
        summary: '',
        items: {
          total: 0,
          new: 0
        },
        comments: {
          total: 0,
          new: 0
        },
        votes: {
          up: 0,
          down: 0
        },
        selected: false,
        hasSharedItems: false,
        isSharingSet: false,
        sharingSets: [],
        relatedStories: [],
        keywords: []
      }

      this.selection.forEach((id) => {
        const selectedStory = this.getStoryById()(id)
        newStory.items.total += selectedStory.items.total
        newStory.items.new += selectedStory.items.new

        newStory.tags = xorConcat(newStory.tags, selectedStory.tags)

        newStory.comments.total += this.mergeDiscussion
          ? selectedStory.comments.total
          : 0
        newStory.comments.new += this.mergeDiscussion
          ? selectedStory.comments.new
          : 0

        newStory.votes.up += this.mergeVotes ? selectedStory.votes.up : 0
        newStory.votes.down += this.mergeVotes ? selectedStory.votes.down : 0
      })

      return newStory
    }
  }
}
</script>
