<template>
  <v-card
    tile
    elevation="4"
    outlined
    height="100%"
    :class="[
      'px-5',
      'py-4',
      'align-self-stretch',
      'story',
      'primary--text',
      {
        selected: selected,
        'pinned-story': story.pinned,
        'hot-story': story.hot,
        'corner-tag-ai': story.ai,
        'corner-tag-shared': story.isSharingSet,
        'sharing-set-story': story.isSharingSet,
        'sharing-set-story-shared': story.sharingState === 'shared',
      },
    ]"
    @click="toggleSelection"
  >
    <!-- Corner Tags -->
    <div v-if="story.ai && !story.isSharingSet" class="story-corner-tag">
      AI
    </div>
    <div
      v-if="story.isSharingSet && story.sharingDirection === 'outgoing'"
      class="story-corner-tag"
    >
      <v-icon x-small left v-if="story.sharingState === 'shared'"
        >mdi-share</v-icon
      >
      <v-icon x-small left v-else>mdi-share-outline</v-icon>
    </div>
    <div
      v-if="story.isSharingSet && story.sharingDirection === 'incoming'"
      class="story-corner-tag"
    >
      <v-icon
        x-small
        left
        class="flipped-icon"
        v-if="story.sharingState === 'shared'"
        >mdi-share</v-icon
      >
      <v-icon x-small left class="flipped-icon" v-else
        >mdi-share-outline</v-icon
      >
    </div>

    <v-container column style="height: 100%">
      <v-row no-gutters style="height: 100%">
        <v-col
          class="d-flex flex-column"
          align-self="start"
          style="height: 100%"
        >
          <!-- Header -->

          <v-row class="flex-grow-0">
            <v-col cols="10" class="mr-auto mt-1 activity-row">
              <div v-if="story.isSharingSet">
                <span class="last-activity font-weight-light">Shared on: </span>
                <span class="last-activity font-weight-bold">
                  {{ getLastActivity() }} </span
                ><br />
                <span class="last-activity font-weight-light">Shared by: </span>
                <span class="last-activity font-weight-bold">
                  {{ story.originator }}
                </span>
              </div>

              <div v-else>
                <span class="last-activity font-weight-light"
                  >Last activity:
                </span>
                <span class="last-activity font-weight-bold">
                  {{ getLastActivity() }}
                </span>
              </div>
            </v-col>

            <v-col cols="2" class="text-right">
              <pin :value="story.pinned" @click="pinStory(story.id)" />
            </v-col>
          </v-row>

          <!-- Title -->

          <v-row class="flex-grow-0 mt-0">
            <v-col class="py-3">
              <h2 class="story-card-title">
                {{ story.title }}
              </h2>
            </v-col>
          </v-row>

          <v-row class="flex-grow-0 mt-0">
            <v-col>
              <tag-norm v-for="tag in story.tags" :key="tag.label" :tag="tag" />
            </v-col>
          </v-row>

          <!-- spacer -->

          <v-spacer></v-spacer>

          <!-- summary -->

          <v-row class="flex-grow-0 mt-0 mb-0">
            <v-col>
              <p class="story-card-summary">
                {{ story.summary }}
              </p>
            </v-col>
          </v-row>

          <!-- Footer -->

          <v-row
            no-gutter
            wrap
            align="center"
            justify="end"
            class="flex-grow-0 mt-0"
          >
            <v-col cols="12" md="8" class="mx-0 d-flex justify-start">
              <v-container class="mx-0 pa-0">
                <v-row class="mx-0">
                  <v-col cols="6" class="pa-0 pt-0 pr-1">
                    <v-icon left small>mdi-file-outline</v-icon>
                    <span class="text-caption font-weight-light dark-grey--text"
                      >{{ story.items.total }}/</span
                    >
                    <span
                      class="text-caption font-weight-bold dark-grey--text"
                      >{{ story.items.new }}</span
                    >
                  </v-col>
                  <v-col cols="6" class="pa-0 pt-0 pr-1">
                    <v-icon
                      @click.native.capture="upvote($event)"
                      left
                      small
                      color="awake-green-color"
                      >mdi-arrow-up-circle-outline</v-icon
                    >
                    <span
                      class="text-caption font-weight-light dark-grey--text"
                      >{{ story.votes.up }}</span
                    >
                  </v-col>
                  <v-col cols="6" class="pa-0 pt-0 pr-1">
                    <v-icon left small>mdi-message-outline</v-icon>
                    <span class="text-caption font-weight-light dark-grey--text"
                      >{{ story.comments.total }}/</span
                    >
                    <span
                      class="text-caption font-weight-bold dark-grey--text"
                      >{{ story.comments.new }}</span
                    >
                  </v-col>
                  <v-col cols="6" class="pa-0 pt-0 pr-1">
                    <v-icon
                      @click.native.capture="downvote($event)"
                      left
                      small
                      color="awake-red-color"
                      >mdi-arrow-down-circle-outline</v-icon
                    >
                    <span
                      class="text-caption font-weight-light dark-grey--text"
                      >{{ story.votes.down }}</span
                    >
                  </v-col>
                </v-row>
              </v-container>
            </v-col>
            <v-col cols="12" md="4" class="mx-0 d-flex justify-end">
              <button-outlined
                label="view story"
                icon="mdi-eye"
                extraClass="mt-1"
                @click="viewStory($event)"
              />
            </v-col>
          </v-row>
        </v-col>
      </v-row>
    </v-container>
  </v-card>
</template>

<script>
import TagNorm from '@/components/common/tags/TagNorm'
import buttonOutlined from '@/components/_subcomponents/buttonOutlined'
import pin from '@/components/_subcomponents/pin'
import moment from 'moment'

import { mapActions } from 'vuex'

export default {
  name: 'CardStory',
  components: {
    TagNorm,
    buttonOutlined,
    pin
  },
  props: {
    story: {}
  },
  data: () => ({
    selected: this.story.selected
  }),
  methods: {
    ...mapActions('dashboard', [
      'pinStory',
      'upvoteStory',
      'downvoteStory',
      'selectStory'
    ]),

    getLastActivity () {
      return moment(this.story.lastActivity).format('DD/MM/YYYY hh:mm:ss')
    },

    toggleSelection () {
      this.selected = !this.selected
      this.selectStory(this.story.id)
    },
    upvote (event) {
      event.stopPropagation()
      this.upvoteStory(this.story.id)
    },
    downvote (event) {
      event.stopPropagation()
      this.downvoteStory(this.story.id)
    },
    viewStory (event) {
      event.stopPropagation()
      this.$router.push({ path: '/assess', query: { story: this.story.id } })
    }
  },
  mounted () {
    this.$emit('init')
  }
}
</script>
