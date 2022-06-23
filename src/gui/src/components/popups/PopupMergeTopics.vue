<template>
  <v-card>
    <v-form ref="form" v-model="valid">
      <v-container>
        <v-row>
          <v-col cols="12">
            <h2 class="popup-title pb-2">Merge Topics</h2>
            The following topics were selected for merging:
          </v-col>
        </v-row>
        <v-row no-gutters>
          <v-col>
            <v-container fluid style="padding: 18px 5px">
              <v-row>
                <v-col
                  v-for="topicId in selection"
                  :key="topicId"
                  class="d-flex pa-1"
                  align-self="start"
                >
                  <v-card
                    elevation="0"
                    tile
                    height="100%"
                    class="merge-topic-details"
                  >
                    <v-row justify="start" no-gutters class="flex-grow-0">
                      <v-col>
                        <h4 class="merge-topics-details-title my-2">
                          {{ getTopicDetails(topicId).title }}
                        </h4>
                      </v-col>
                    </v-row>

                    <v-spacer></v-spacer>
                    <v-divider></v-divider>

                    <v-row
                      justify="end"
                      no-gutters
                      class="flex-grow-0 my-2 merge-topics-details-meta"
                    >
                      <v-col
                        cols="12"
                        v-if="getTopicDetails(topicId).isSharingSet"
                      >
                        <v-icon left x-small class="mr-1 flipped-icon"
                          >$awakeShare</v-icon
                        >
                        Shared Set
                      </v-col>
                      <v-col cols="12" v-else>
                        <v-icon left x-small class="mr-1 flipped-icon"
                          >mdi-folder-outline</v-icon
                        >
                        Local Topic
                      </v-col>

                      <v-col cols="12">
                        <v-icon left x-small class="mr-1"
                          >mdi-file-outline</v-icon
                        >
                        {{ getTopicDetails(topicId).items.total }}/
                        <strong>{{
                          getTopicDetails(topicId).items.new
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
            <h4 class="merge-topics-details-title">Merge Options</h4>
          </v-col>
        </v-row>
        <v-row>
          <!----------->
          <!-- Title -->
          <!----------->

          <v-col class="py-2">
            <text-field v-model="mergeTitle" label="Topic Title" />
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
            class="py-0 merge-topics-details-meta grey--text text--darken-2"
          >
            <div class="mt-5 mr-2 text-right">
              <v-icon left x-small class="mr-1 grey--text text--darken-2"
                >mdi-message-outline</v-icon
              >
              {{ topicPrototype.comments.total }}/
              <strong>{{ topicPrototype.comments.new }}</strong>
            </div>
          </v-col>

          <!----------------->
          <!-- Merge Votes -->
          <!----------------->

          <v-col cols="8" class="py-0">
            <switch-field v-model="mergeVotes" label="merge up-/downvotes" />
          </v-col>
          <v-col cols="4" class="py-0 merge-topics-details-meta">
            <div class="mt-5 mr-2 text-right grey--text text--darken-2">
              <v-icon left x-small class="mr-1 grey--text text--darken-2"
                >mdi-arrow-up-circle-outline</v-icon
              >
              {{ topicPrototype.votes.up }}
              <v-icon left x-small class="mr-1 ml-2 grey--text text--darken-2"
                >mdi-arrow-down-circle-outline</v-icon
              >
              {{ topicPrototype.votes.down }}
            </div>
          </v-col>

          <!--------------------->
          <!-- Delete original -->
          <!--------------------->

          <v-col cols="12" class="py-0">
            <switch-field v-model="deleteOld" label="delete selected topics" />
          </v-col>
        </v-row>
      </v-container>

      <v-divider></v-divider>

      <v-card-actions class="mt-3">
        <v-spacer></v-spacer>

        <button-outlined
          label="cancel"
          icon="$awakeClose"
          color="awake-red-color"
          extraClass="mr-2"
          @click="$emit('close')"
        />

        <button-solid
          label="merge topics"
          icon="$awakeMerge"
          color="primary"
          @click="mergeSelectedTopics()"
        />
      </v-card-actions>
    </v-form>
  </v-card>
</template>

<script>
import { mapActions, mapGetters } from 'vuex'
import { xorConcat } from '@/utils/helpers'
import { faker } from '@faker-js/faker'

import buttonSolid from '@/components/_subcomponents/buttonSolid'
import buttonOutlined from '@/components/_subcomponents/buttonOutlined'
import textField from '@/components/_subcomponents/textField'
import switchField from '@/components/_subcomponents/switchField'

export default {
  name: 'PopupMergeTopics',
  components: {
    buttonSolid,
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
      'pinTopic',
      'unselectAllTopics',
      'removeTopicById',
      'createNewTopic'
    ]),
    ...mapActions('assess', [
      'deselectNewsItem',
      'deselectAllNewsItems',
      'assignSharingSet',
      'changeMergeAttr'
    ]),
    ...mapGetters('dashboard', ['getTopicById']),

    getTopicDetails (id) {
      return this.getTopicById()(parseInt(id))
    },

    mergeSelectedTopics () {
      // Add Form Validation

      const oldTopics = [...this.selection]

      const mergedTopic = this.topicPrototype
      mergedTopic.title = this.mergeTitle
      mergedTopic.summary = this.mergeSummary
        ? this.mergeSummary
        : 'this is an AI created summary ... ' + faker.lorem.paragraph(10) // should be replaced by NLP algorithm
      mergedTopic.id = Math.floor(Math.random() * (1000 - 800 + 1)) + 800

      // reset selection
      this.unselectAllTopics()

      // remove old topics
      if (this.deleteOld) {
        this.selection.forEach((id) => this.removeTopicById(id))
      }

      this.createNewTopic(mergedTopic)
      this.changeMergeAttr({ src: oldTopics, dest: mergedTopic.id })

      // Close Popup
      this.$emit('close')
    }
  },
  computed: {
    topicPrototype () {
      const newTopic = {
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
        relatedTopics: [],
        keywords: []
      }

      this.selection.forEach((id) => {
        const selectedTopic = this.getTopicById()(id)
        newTopic.items.total += selectedTopic.items.total
        newTopic.items.new += selectedTopic.items.new

        newTopic.tags = xorConcat(newTopic.tags, selectedTopic.tags)

        newTopic.comments.total += this.mergeDiscussion
          ? selectedTopic.comments.total
          : 0
        newTopic.comments.new += this.mergeDiscussion
          ? selectedTopic.comments.new
          : 0

        newTopic.votes.up += this.mergeVotes ? selectedTopic.votes.up : 0
        newTopic.votes.down += this.mergeVotes ? selectedTopic.votes.down : 0
      })

      return newTopic
    }
  }
}
</script>
