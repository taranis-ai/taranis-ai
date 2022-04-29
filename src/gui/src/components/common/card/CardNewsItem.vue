<template>
  <v-col cols="12" xl="6">
    <v-card
      tile
      elevation="4"
      outlined
      height="100%"
      :class="[
        'pl-5',
        'align-self-stretch',
        'news-item',
        'dark-grey--text',
        {
          selected: selected,
          'corner-tag-shared': newsItem.shared && !newsItem.restricted,
          'corner-tag-restricted': newsItem.restricted,
          'status-important': newsItem.important,
          'status-unread': !newsItem.read,
        },
      ]"
      @click="toggleSelection"
    >
      <div
        v-if="newsItem.shared && !newsItem.restricted"
        class="
          news-item-corner-tag
          text-caption text-weight-bold text-uppercase
          white--text
        "
      >
        <v-icon x-small class="flipped-icon">$awakeShare</v-icon>
      </div>

      <div
        v-if="newsItem.restricted"
        class="
          news-item-corner-tag
          text-caption text-weight-bold text-uppercase
          white--text
        "
      >
        <v-icon x-small>mdi-lock-outline</v-icon>
      </div>

      <!-- Topic Actions -->

      <div class="news-item-action-bar">
        <div v-show="scopeTopic">
          <news-item-action
            icon="$newsItemActionRemove"
            tooltip="remove from topic"
            extraClass="news-item-topic-action"
            @input="removeFromTopic()"
          />
        </div>

        <div v-show="scopeSharingSet">
          <news-item-action
            icon="$newsItemActionRemove"
            tooltip="remove from sharing set"
            extraClass="news-item-sharing-set-action"
            @input="removeFromTopic()"
          />
        </div>

        <!-- News Items Actions -->

        <news-item-action
          :active="newsItem.read"
          icon="$newsItemActionRead"
          @input="markAsRead()"
          tooltip="mark as read/unread"
        />

        <news-item-action
          :active="newsItem.important"
          icon="$newsItemActionImportant"
          @input="markAsImportant()"
          tooltip="mark as important"
        />

        <v-dialog v-model="deleteDialog" width="600">
          <template #activator="{ on: deleteDialog }">
            <v-tooltip>
              <template #activator="{ on: tooltip }">
                <v-btn
                  v-on="{ ...tooltip, ...deleteDialog }"
                  icon
                  tile
                  class="news-item-action"
                >
                  <v-icon> $newsItemActionDelete </v-icon>
                </v-btn>
              </template>
              <span>delete item</span>
            </v-tooltip>
          </template>

          <popup-delete-item
            v-model="deleteDialog"
            :newsItem="newsItem"
            @deleteItem="$emit('deleteItem', newsItem.id)"
          />
        </v-dialog>

        <news-item-action
          :active="newsItem.decorateSource"
          icon="$newsItemActionRibbon"
          @input="decorateSource()"
          tooltip="emphasise originator"
        />
      </div>

      <v-container no-gutters class="ma-0 pa-0">
        <v-row no-gutters>
          <v-col
            cols="12"
            sm="12"
            md="7"
            class="d-flex flex-column"
            align-self="start"
          >
            <v-container column style="height: 100%">
              <v-row class="flex-grow-0 mt-0">
                <v-col class="pb-1">
                  <h2
                    :class="[
                      'news-item-title',
                      {
                        'status-unread': !newsItem.read,
                      },
                    ]"
                  >
                    <sup v-if="!newsItem.read" class="new-indicator"> * </sup>
                    {{ newsItem.title }}
                  </h2>
                </v-col>
              </v-row>

              <v-row class="flex-grow-0 mt-0">
                <v-col>
                  <p
                    class="
                      font-weight-light
                      dark-grey--text
                      news-item-summary
                      mb-0
                    "
                  >
                    {{ newsItem.summary }}
                  </p>
                </v-col>
              </v-row>

              <v-row class="flex-grow-0 mt-1">
                <v-col
                  cols="12"
                  class="mx-0 d-flex justify-start flex-wrap py-1"
                >
                  <v-btn
                    outlined
                    class="text-lowercase news-item-btn mr-1 mt-1"
                    @click.native.capture="viewTopic($event)"
                  >
                    <v-icon left>$awakeEye</v-icon>
                    view details
                  </v-btn>

                  <v-btn
                    outlined
                    class="text-lowercase news-item-btn mr-1 mt-1"
                    @click.native.capture="viewTopic($event)"
                  >
                    <v-icon left>$awakeReport</v-icon>
                    create report
                  </v-btn>
                  <v-btn
                    outlined
                    class="text-lowercase news-item-btn mr-1 mt-1"
                    @click.native.capture="viewTopic($event)"
                  >
                    <v-icon left>$awakeRelated</v-icon>
                    show related items
                  </v-btn>
                  <div class="d-flex align-start justify-center mr-3 ml-2 mt-1">
                    <v-icon
                      left
                      small
                      color="awake-green-color"
                      class="align-self-center mr-1"
                      @click.native.capture="upvote($event)"
                      >mdi-arrow-up-circle-outline</v-icon
                    >
                    <span
                      class="
                        text-caption
                        font-weight-light
                        dark-grey--text
                        align-self-center
                      "
                      >{{ newsItem.votes.up }}</span
                    >
                  </div>
                  <div class="d-flex align-start justify-center mr-3 mt-1">
                    <v-icon
                      left
                      small
                      color="awake-red-color"
                      class="align-self-center mr-1"
                      @click.native.capture="downvote($event)"
                      >mdi-arrow-down-circle-outline</v-icon
                    >
                    <span
                      class="
                        text-caption
                        font-weight-light
                        dark-grey--text
                        align-self-center
                      "
                      >{{ newsItem.votes.down }}</span
                    >
                  </div>
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
            <v-container column style="height: 100%" class="pb-5">
              <v-row class="news-item-meta-infos">
                <v-col class="news-item-meta-infos-label">
                  <strong>Published:</strong>
                </v-col>
                <v-col>
                  {{ getPublishedDate() }}
                </v-col>
              </v-row>
              <v-row class="news-item-meta-infos">
                <v-col class="news-item-meta-infos-label">
                  <strong>Collected:</strong>
                </v-col>
                <v-col>
                  {{ getCollectedDate() }}
                </v-col>
              </v-row>
              <v-row class="news-item-meta-infos">
                <v-col class="news-item-meta-infos-label">
                  <strong>Source:</strong>
                </v-col>
                <v-col>
                  {{ newsItem.source.domain }} <br />
                  <a
                    :href="newsItem.source.url"
                    target="_blank"
                    icon
                    class="meta-link d-flex"
                  >
                    <v-icon left x-small class="mr-1">mdi-open-in-new</v-icon>
                    <span class="label">{{ newsItem.source.url }}</span>
                  </a>
                </v-col>
              </v-row>
              <v-row class="news-item-meta-infos">
                <v-col class="news-item-meta-infos-label">
                  <strong>Source Type:</strong>
                </v-col>
                <v-col>
                  {{ newsItem.source.type }}
                </v-col>
              </v-row>
              <v-row class="news-item-meta-infos">
                <v-col class="news-item-meta-infos-label">
                  <strong>Added by:</strong>
                </v-col>
                <v-col>
                  <span :class="[{ decorateSource: newsItem.decorateSource }]">
                    {{ getAddedByUser() }}
                    <v-icon
                      right
                      small
                      v-if="newsItem.decorateSource"
                      class="ml-0"
                      >$awakeRibbon</v-icon
                    >
                  </span>
                </v-col>
              </v-row>
              <v-row class="news-item-meta-infos">
                <v-col class="news-item-meta-infos-label">
                  <strong>Topics:</strong>
                </v-col>
                <v-col>
                  <span class="news-item-meta-topics-list text-capitalize">
                    {{ getTopicsList() }}
                  </span>
                </v-col>
              </v-row>
              <v-row class="news-item-meta-infos">
                <v-col class="news-item-meta-infos-label d-flex align-center">
                  <strong>Tags:</strong>
                </v-col>
                <v-col>
                  <tag-norm
                    v-for="tag in newsItem.tags"
                    :key="tag.label"
                    :tag="tag"
                  />
                </v-col>
              </v-row>
            </v-container>
          </v-col>
        </v-row>
      </v-container>
    </v-card>
  </v-col>
</template>

<script>
import TagNorm from '@/components/common/tags/TagNorm'
import moment from 'moment'
import newsItemAction from '@/components/inputs/newsItemAction'
import PopupDeleteItem from '@/components/popups/PopupDeleteItem'

import { mapActions, mapGetters, mapState } from 'vuex'

export default {
  name: 'CardNewsItem',
  components: {
    TagNorm,
    newsItemAction,
    PopupDeleteItem
  },
  props: {
    newsItem: {}
  },
  data: () => ({
    deleteDialog: false
  }),
  computed: {
    ...mapState('newsItemsFilter', ['filter']),

    scopeSharingSet () {
      return (
        this.filter.scope.sharingSets.length === 1 &&
        this.filter.scope.topics.length === 0
      )
    },
    scopeTopic () {
      return this.filter.scope.topics.length === 1
    },
    selected () {
      return this.getNewsItemsSelection().includes(this.newsItem.id)
    }
  },
  methods: {
    ...mapGetters('dashboard', ['getTopicById', 'getTopicTitleById']),
    ...mapGetters('users', ['getUsernameById']),
    ...mapGetters('assess', ['getNewsItemsSelection']),

    ...mapActions('assess', [
      'selectNewsItem',
      'upvoteNewsItem',
      'downvoteNewsItem',
      'removeTopicFromNewsItem'
    ]),

    getTopicTitle (topicId) {
      return this.getTopicTitleById()(topicId)
    },
    toggleSelection () {
      this.selectNewsItem(this.newsItem.id)
    },
    removeFromTopic () {
      const topicId = this.scopeSharingSet
        ? this.filter.scope.sharingSets[0].id
        : this.filter.scope.topics[0].id
      this.removeTopicFromNewsItem({
        newsItemId: this.newsItem.id,
        topicId: topicId
      })
    },
    markAsRead () {
      this.newsItem.read = !this.newsItem.read
    },
    markAsImportant () {
      this.newsItem.important = !this.newsItem.important
    },
    decorateSource () {
      this.newsItem.decorateSource = !this.newsItem.decorateSource
    },
    deleteNewsItem () {
      this.$emit('deleteItem', this.newsItem.id)
    },
    upvote (event) {
      event.stopPropagation()
      this.upvoteNewsItem(this.newsItem.id)
    },
    downvote (event) {
      event.stopPropagation()
      this.downvoteNewsItem(this.newsItem.id)
    },
    getAddedByUser () {
      return this.getUsernameById()(this.newsItem.addedBy)
    },
    getPublishedDate () {
      return moment(this.newsItem.published).format('DD/MM/YYYY hh:mm:ss')
    },
    getCollectedDate () {
      return moment(this.newsItem.collected).format('DD/MM/YYYY hh:mm:ss')
    },
    getTopicsList () {
      const topicTitles = []
      this.newsItem.topics.forEach((id) => {
        const newTopicTitle = this.getTopicTitleById()(id)
        if (topicTitles.indexOf(newTopicTitle) === -1) {
          topicTitles.push(newTopicTitle)
        }
      })

      return topicTitles.length ? topicTitles.join(', ') : '-'
    }
  }
}
</script>
