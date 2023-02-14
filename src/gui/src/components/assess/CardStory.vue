<template>
  <v-row dense class="ma-0 pa-0">
    <v-col cols="12">
      <v-card
        tile
        elevation="4"
        outlined
        :ripple="false"
        height="100%"
        :class="[
          'pl-5',
          'align-self-stretch',
          'news-item',
          'dark-grey--text',
          {
            selected: selected
          }
        ]"
        @click="toggleSelection"
      >
        <div
          v-if="story.in_reports_count > 0"
          class="news-item-corner-tag text-caption text-weight-bold text-uppercase white--text"
        >
          <v-icon class="flipped-icon">mdi-share</v-icon>
          <span>{{ story.in_reports_count }}</span>
        </div>

        <div
          v-if="storyRestricted()"
          class="news-item-corner-tag text-caption text-weight-bold text-uppercase white--text"
        >
          <v-icon>mdi-lock-outline</v-icon>
        </div>

        <!-- Story Actions -->

        <div class="news-item-action-bar">
          <news-item-action-dialog
            icon="mdi-delete"
            tooltip="remove item"
            :showDialog="deleteDialog"
            @close="deleteDialog = false"
            @open="deleteDialog = true"
          >
            <popup-delete-item
              v-if="deleteDialog"
              :newsItem="story"
              @deleteItem="deleteNewsItem()"
              @close="deleteDialog = false"
            />
          </news-item-action-dialog>

          <news-item-action
            :active="story.read"
            icon="mdi-email-mark-as-unread"
            @click="markAsRead()"
            tooltip="mark as read/unread"
          />

          <news-item-action
            :active="story.important"
            icon="mdi-exclamation"
            @click="markAsImportant()"
            tooltip="mark as important"
          />

          <news-item-action-dialog
            icon="mdi-google-circles-communities"
            tooltip="add to report"
            :showDialog="sharingDialog"
            @close="sharingDialog = false"
            @open="sharingDialog = true"
          >
            <popup-share-items
              v-if="sharingDialog"
              :newsItem="story"
              @close="sharingDialog = false"
            />
          </news-item-action-dialog>
        </div>

        <v-container no-gutters class="ma-0 pa-0">
          <v-row no-gutters>
            <v-col
              cols="12"
              sm="12"
              md="7"
              class="d-flex flex-column pr-3"
              align-self="start"
            >
              <v-container column style="height: 100%">
                <v-row class="flex-grow-0 mt-0">
                  <v-col class="pb-1">
                    <h2 class="news-item-title">{{ story.title }}</h2>
                  </v-col>
                </v-row>

                <v-row class="flex-grow-0 mt-0">
                  <v-col>
                    <p :class="news_item_summary_class">
                      {{ getDescription() }}
                    </p>
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
                <v-row class="flex-grow-0 mt-1">
                  <v-col
                    cols="12"
                    class="d-flex justify-start flex-wrap pt-1 pb-4"
                  >
                    <v-btn
                      class="mr-1 mt-1"
                      outlined
                      @click.stop="addToReport()"
                    >
                      <v-icon>mdi-google-circles-communities</v-icon>
                      <span>add to report</span>
                    </v-btn>
                    <v-btn
                      class="mr-1 mt-1"
                      outlined
                      :to="'/story/' + story.id"
                    >
                      <v-icon>mdi-eye</v-icon>
                      <span>view Details</span>
                    </v-btn>
                    <v-btn
                      class="mr-1 mt-1"
                      :outlined="news_item_length ? false : true"
                      :color="news_item_length ? 'blue-grey' : null"
                      @click.stop="openSummary = !openSummary"
                    >
                      <v-icon>{{ news_item_summary_icon }}</v-icon>
                      <span>{{ news_item_summary_text }}</span>
                    </v-btn>

                    <div
                      class="d-flex align-start justify-center mr-3 ml-2 mt-1"
                    >
                      <votes :count="likes" type="up" @input="upvote()" />
                    </div>
                    <div class="d-flex align-start justify-center mr-3 mt-1">
                      <votes
                        :count="dislikes"
                        type="down"
                        @input="downvote()"
                      />
                    </div>
                  </v-col>
                </v-row>
                <v-row class="news-item-meta-infos">
                  <v-col class="news-item-meta-infos-label">
                    <strong>{{ $t('assess.published') }}:</strong>
                  </v-col>
                  <v-col>
                    <span :class="published_date_outdated ? 'red--text' : ''">
                      {{ $d(getPublishedDate(), 'long') }}
                    </span>
                    <v-icon v-if="published_date_outdated" small color="red"
                      >mdi-alert</v-icon
                    >
                  </v-col>
                </v-row>
                <v-row class="news-item-meta-infos">
                  <v-col class="news-item-meta-infos-label">
                    <strong>{{ $t('card_item.created') }}:</strong>
                  </v-col>
                  <v-col>
                    {{ $d(getCollectedDate(), 'long') }}
                  </v-col>
                </v-row>
                <v-row class="news-item-meta-infos">
                  <v-col class="news-item-meta-infos-label d-flex align-center">
                    <strong>Tags:</strong>
                  </v-col>
                  <v-col>
                    <tag-list key="tags" :tags="getTags()" />
                  </v-col>
                </v-row>
                <v-row class="news-item-meta-infos">
                  <v-col class="news-item-meta-infos-label d-flex align-center">
                    <strong>Summarzied:</strong>
                  </v-col>
                  <v-col>
                    {{ isSummarized() }}
                  </v-col>
                </v-row>
                <metainfo v-if="openSummary && story.news_items.length == 1" :newsItem="story.news_items[0]" />
              </v-container>
            </v-col>
          </v-row>
        </v-container>
      </v-card>
    </v-col>
    <v-row no-gutter v-if="openSummary && story.news_items.length > 1">
      <card-news-item
        v-for="item in story.news_items"
        :key="item.id"
        :newsItem="item"
      />
    </v-row>
  </v-row>
</template>

<script>
import TagList from '@/components/common/tags/TagList'
import newsItemAction from '@/components/_subcomponents/newsItemAction'
import newsItemActionDialog from '@/components/_subcomponents/newsItemActionDialog'
import PopupDeleteItem from '@/components/popups/PopupDeleteItem'
import PopupShareItems from '@/components/popups/PopupShareItems'
import votes from '@/components/assess/card/votes'
import metainfo from '@/components/assess/card/metainfo'
import CardNewsItem from '@/components/assess/CardNewsItem'

import { mapGetters } from 'vuex'

import {
  deleteNewsItemAggregate,
  importantNewsItemAggregate,
  readNewsItemAggregate,
  voteNewsItemAggregate
} from '@/api/assess'

export default {
  name: 'CardStory',
  components: {
    TagList,
    newsItemAction,
    newsItemActionDialog,
    CardNewsItem,
    PopupDeleteItem,
    PopupShareItems,
    votes,
    metainfo
  },
  emits: ['selectItem', 'deleteItem'],
  props: {
    story: {},
    selected: Boolean
  },
  data: () => ({
    viewDetails: false,
    openSummary: false,
    sharingDialog: false,
    deleteDialog: false,
    likes: 0,
    dislikes: 0
  }),
  computed: {
    item_important() {
      return 'important' in this.story ? this.story.important : false
    },
    published_date() {
      return this.story.news_items[0].news_item_data.published || false
    },
    news_item_summary_class() {
      return this.openSummary
        ? 'news-item-summary-no-clip'
        : 'news-item-summary'
    },
    news_item_summary_icon() {
      return this.openSummary
        ? 'mdi-unfold-less-horizontal'
        : 'mdi-unfold-more-horizontal'
    },
    news_item_length() {
      return this.story.news_items.length > 1 ? this.story.news_items.length : ''
    },
    news_item_summary_text() {
      return this.openSummary ? 'Close' : `Open ${this.news_item_length}`
    },
    published_date_outdated() {
      const pub_date = new Date(this.published_date)
      if (!pub_date) {
        return false
      }
      const oneWeekAgo = new Date()
      oneWeekAgo.setDate(oneWeekAgo.getDate() - 7)
      return oneWeekAgo > pub_date
    }
  },
  methods: {
    ...mapGetters('users', ['getUsernameById']),

    toggleSelection() {
      this.$emit('selectItem', this.story.id)
    },
    markAsRead() {
      readNewsItemAggregate(this.story.id)
    },
    markAsImportant() {
      importantNewsItemAggregate(this.story.id)
    },
    deleteNewsItem() {
      deleteNewsItemAggregate(this.story.id)
      this.$emit('deleteItem', this.story.id)
    },
    upvote() {
      this.likes += 1
      voteNewsItemAggregate(this.story.id, 1)
    },
    downvote() {
      this.dislikes += 1
      voteNewsItemAggregate(this.story.id, -1)
    },
    addToReport() {
      this.sharingDialog = true
    },
    showRelated(event) {
      console.log('not yet implemented')
    },

    updateDetailsView(value) {
      this.viewDetails = value
    },

    isSummarized() {
      return this.story.summary !== undefined && this.story.summary !== ''
    },

    getDescription() {
      return this.story.summary || this.story.description
    },

    getTags() {
      return this.story.tags.map((tag) => tag.name)
    },

    getPublishedDate() {
      const published = this.published_date
      if (published) {
        return new Date(published)
      }
      return '** no published date **'
    },

    getCollectedDate() {
      const collected = this.story.created
      return collected ? new Date(collected) : new Date(this.story.created)
    },

    getAuthor() {
      return this.story.news_items[0].news_item_data.author
    },

    storyInReport() {
      return this.story.in_reports_count
    },

    storyRestricted() {
      return false
    }
  },
  updated() {
    // console.log('card rendered!')
  },
  mounted() {
    this.likes = this.story.likes || 0
    this.dislikes = this.story.dislikes || 0
  }
}
</script>
