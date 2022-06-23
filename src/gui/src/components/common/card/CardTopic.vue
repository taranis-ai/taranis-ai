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
      'topic',
      'primary--text',
      {
        selected: topic.selected,
        'pinned-topic': topic.pinned,
        'hot-topic': topic.hot,
        'corner-tag-ai': topic.ai,
        'corner-tag-shared': topic.isSharingSet,
        'sharing-set-topic': topic.isSharingSet,
        'sharing-set-topic-shared': topic.sharingState === 'shared',
      },
    ]"
    @click="toggleSelection"
  >
    <!-- Corner Tags -->
    <div v-if="topic.ai && !topic.isSharingSet" class="topic-corner-tag">
      AI
    </div>
    <div
      v-if="topic.isSharingSet && topic.sharingDirection === 'outgoing'"
      class="topic-corner-tag"
    >
      <v-icon x-small left v-if="topic.sharingState === 'shared'"
        >$awakeShare</v-icon
      >
      <v-icon x-small left v-else>$awakeShareOutline</v-icon>
    </div>
    <div
      v-if="topic.isSharingSet && topic.sharingDirection === 'incoming'"
      class="topic-corner-tag"
    >
      <v-icon
        x-small
        left
        class="flipped-icon"
        v-if="topic.sharingState === 'shared'"
        >$awakeShare</v-icon
      >
      <v-icon x-small left class="flipped-icon" v-else
        >$awakeShareOutline</v-icon
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
              <div v-if="topic.isSharingSet">
                <span class="last-activity font-weight-light">Shared on: </span>
                <span class="last-activity font-weight-bold">
                  {{ getLastActivity() }} </span
                ><br />
                <span class="last-activity font-weight-light">Shared by: </span>
                <span class="last-activity font-weight-bold">
                  {{ topic.originator }}
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
              <pin :value="topic.pinned" @click="pinTopic(topic.id)" />
            </v-col>
          </v-row>

          <!-- Title -->

          <v-row class="flex-grow-0 mt-0">
            <v-col class="py-3">
              <h2 class="topic-card-title">
                {{ topic.title }}
              </h2>
            </v-col>
          </v-row>

          <v-row class="flex-grow-0 mt-0">
            <v-col>
              <tag-norm v-for="tag in topic.tags" :key="tag.label" :tag="tag" />
            </v-col>
          </v-row>

          <!-- spacer -->

          <v-spacer></v-spacer>

          <!-- summary -->

          <v-row class="flex-grow-0 mt-0 mb-0">
            <v-col>
              <p class="topic-card-summary">
                {{ topic.summary }}
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
                      >{{ topic.items.total }}/</span
                    >
                    <span
                      class="text-caption font-weight-bold dark-grey--text"
                      >{{ topic.items.new }}</span
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
                      >{{ topic.votes.up }}</span
                    >
                  </v-col>
                  <v-col cols="6" class="pa-0 pt-0 pr-1">
                    <v-icon left small>mdi-message-outline</v-icon>
                    <span class="text-caption font-weight-light dark-grey--text"
                      >{{ topic.comments.total }}/</span
                    >
                    <span
                      class="text-caption font-weight-bold dark-grey--text"
                      >{{ topic.comments.new }}</span
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
                      >{{ topic.votes.down }}</span
                    >
                  </v-col>
                </v-row>
              </v-container>
            </v-col>
            <v-col cols="12" md="4" class="mx-0 d-flex justify-end">
              <button-outlined
                label="view topic"
                icon="$awakeEye"
                extraClass="mt-1"
                @click="viewTopic($event)"
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
  name: 'CardTopic',
  components: {
    TagNorm,
    buttonOutlined,
    pin
  },
  props: {
    topic: {}
  },
  methods: {
    ...mapActions('dashboard', [
      'pinTopic',
      'upvoteTopic',
      'downvoteTopic',
      'selectTopic'
    ]),

    getLastActivity () {
      return moment(this.topic.lastActivity).format('DD/MM/YYYY hh:mm:ss')
    },

    toggleSelection () {
      this.topic.selected = !this.topic.selected
      this.selectTopic(this.topic.id)
    },
    upvote (event) {
      event.stopPropagation()
      this.upvoteTopic(this.topic.id)
    },
    downvote (event) {
      event.stopPropagation()
      this.downvoteTopic(this.topic.id)
    },
    viewTopic (event) {
      event.stopPropagation()
      this.$router.push({ path: '/assess', query: { topic: this.topic.id } })
    }
  },
  mounted () {
    this.$emit('init')
  }
}
</script>
