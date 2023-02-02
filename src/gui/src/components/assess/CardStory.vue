<template>
  <v-row dense class="ma-0 pa-0">
    <v-row dense class="mx-0 mb-0 mt-2 py-0 px-5">
      <!-- DIALOGS -->
      <v-dialog :value="deleteDialog" width="auto">
        <popup-delete-item
          :newsItem="story"
          @deleteItem="deleteNewsItem()"
          @close="deleteDialog = false"
        />
      </v-dialog>
      <v-dialog :value="sharingDialog" width="auto">
        <popup-share-items
          :newsItem="story"
          @deleteItem="deleteNewsItem()"
          @close="sharingDialog = false"
        />
      </v-dialog>

      <v-col cols="12" class="pb-0">
        <v-card
          tile
          elevation="3"
          outlined
          v-ripple="{ class: 'accent--text' }"
          class="container no-gutters"
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
          <v-row>
            <!-- STORY TITLE -->
            <v-col
              cols="12"
              sm="12"
              lg="6"
              class="d-flex flex-grow-1 mt-3 px-5 py-2"
              align-self="center"
              order="1"
              order-sm="1"
            >
              <h2 class="news-item-title">
                {{ story.title }}
              </h2>
            </v-col>

            <!-- STORY ACTIONS -->
            <v-col
              order="3"
              order-sm="2"
              class="d-flex flex-row flex-grow-1 mt-3 px-5 py-2 item-action-container"
              cols="12"
              sm="12"
              lg="6"
              style="justify-content: space-evenly"
            >
              <v-btn
                small
                class="item-action-btn"
                outlined
                :to="'/story/' + story.id"
                v-on:click.stop
                v-ripple="false"
              >
                <span>Details</span>
                <v-icon right>mdi-text-box-search-outline</v-icon>
              </v-btn>

              <v-btn
                small
                class="item-action-btn"
                outlined
                v-on:click.stop="sharingDialog = true"
                v-ripple="false"
              >
                <span>Add to Report</span>
                <v-icon right>mdi-google-circles-communities</v-icon>
              </v-btn>

              <v-btn
                small
                class="item-action-btn open-close-btn"
                :class="openSummary ? 'opened' : 'closed'"
                outlined
                v-on:click.stop
                v-ripple="false"
                :style="{ minWidth: minButtonWidth }"
                @click.stop="openSummary = !openSummary"
              >
                <span>{{ news_item_summary_text }}</span>
                <span v-if="news_item_length > 1" class="primary--text">&nbsp;[{{ news_item_length }}]</span>
                <v-icon right>mdi-chevron-down</v-icon>
              </v-btn>

              <v-btn
                small
                class="item-action-btn hidden-lg-and-down"
                outlined
                v-on:click.stop="markAsRead()"
                v-ripple="false"
              >
                <span>mark as read</span>
                <v-icon right>mdi-eye-outline</v-icon>
              </v-btn>

              <div class="item-action-btn btn-group">
                <v-btn
                  small
                  outlined
                  v-on:click.stop="upvote()"
                  v-ripple="false"
                >
                  <span>{{ likes }}</span>
                  <v-icon right color="awake-green-color"
                    >mdi-arrow-up-circle-outline</v-icon
                  >
                </v-btn>
                <v-btn
                  small
                  outlined
                  v-on:click.stop="downvote()"
                  v-ripple="false"
                >
                  <span>{{ dislikes }}</span>
                  <v-icon right color="awake-red-color"
                    >mdi-arrow-down-circle-outline</v-icon
                  >
                </v-btn>
              </div>

              <v-menu bottom offset-y>
                <template v-slot:activator="{ on, attrs }">
                  <v-btn
                    small
                    class="item-action-btn expandable"
                    outlined
                    v-on:click.stop
                    v-ripple="false"
                    v-bind="attrs"
                    v-on="on"
                  >
                    <v-icon>mdi-dots-vertical</v-icon>
                  </v-btn>
                </template>

                <v-list class="extraActionsList" dense>
                  <v-list-item
                    @click.stop="markAsRead()"
                    class="hidden-xl-only"
                  >
                    <v-icon left>mdi-eye-outline</v-icon>mark as read
                  </v-list-item>
                  <v-list-item @click.stop="markAsImportant()">
                    <v-icon left>mdi-star-outline</v-icon>mark as important
                  </v-list-item>
                  <v-list-item @click.stop>
                    <v-icon left>mdi-bookmark-outline</v-icon>mark as trusted
                    author
                  </v-list-item>
                  <v-list-item @click.stop="deleteDialog = true">
                    <v-icon left>mdi-delete-outline</v-icon>delete
                  </v-list-item>
                </v-list>
              </v-menu>
            </v-col>
            <v-col
              cols="12"
              sm="12"
              class="px-5"
              order="2"
              order-sm="3"
              lg="6"
              align-self="stretch"
            >
              <!-- DESCRIPTION -->
              <p :class="news_item_summary_class">
                {{ getDescription() }}
              </p>
            </v-col>
            <v-col
              class="item-meta-info px-5 pt-2 pb-3"
              order="4"
              order-sm="4"
              cols="12"
              sm="12"
              lg="6"
            >
              <v-container column class="pa-0 pb-3">
                <!-- META INFO -->
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
                    <div>
                      <span
                        class="plain-tags"
                        v-for="(tag, i) in getTags()"
                        v-bind:key="tag+i"
                      >
                        <a href="#">{{ tag }}</a
                        >,
                      </span>
                    </div>
                  </v-col>
                </v-row>
                <!-- <v-row class="news-item-meta-infos mb-2">
                  <v-col class="news-item-meta-infos-label d-flex align-center">
                    <strong>Summarzied:</strong>
                  </v-col>
                  <v-col>
                    <v-icon small v-if="isSummarized()">mdi-check</v-icon>
                    <v-icon small v-else>mdi-close</v-icon>
                  </v-col>
                </v-row> -->
                <metainfo
                  v-if="openSummary && news_item_length == 1"
                  :newsItem="story.news_items[0]"
                />
              </v-container>
            </v-col>
          </v-row>
        </v-card>
      </v-col>
    </v-row>
    <v-row dense class="ma-0 py-0 px-5">
      <v-col cols="12" class="py-0 px-1">
        <div
          class="hidden-story-items-wrapper"
          :class="openSummary && news_item_length > 1 ? 'expanded' : ''"
        >
          <transition name="collapse" mode="in-out">
            <div
              v-if="openSummary && news_item_length > 1"
              class="hidden-story-items-internal-wrapper"
            >
              <card-news-item
                class="pa-0 my-2 story-news-item"
                v-for="item in story.news_items"
                :key="item.id"
                :newsItem="item"
              />
            </div>
          </transition>
        </div>
      </v-col>
    </v-row>
  </v-row>
</template>

<script>
import PopupDeleteItem from '@/components/popups/PopupDeleteItem'
import PopupShareItems from '@/components/popups/PopupShareItems'
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
    CardNewsItem,
    PopupDeleteItem,
    PopupShareItems,
    metainfo
  },
  emits: ['selectItem', 'deleteItem'],
  props: {
    story: {
      type: Object,
      required: true
    },
    selected: Boolean
  },
  data: () => ({
    viewDetails: false,
    openSummary: false,
    sharingDialog: false,
    deleteDialog: false,
    likes: 0,
    dislikes: 0,
    showDialog: false
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
    news_item_length() {
      return this.story.news_items.length
    },
    news_item_summary_text() {
      return this.openSummary
        ? 'Close'
        : 'Open'
    },
    minButtonWidth() {
      const longestText = `${
        this.news_item_length > 1 ? '(' + this.news_item_length + ')' : ''
      }`
      return longestText.length + 11 + 'ch'
    },
    published_date_outdated() {
      const pub_date = new Date(this.published_date)
      if (!pub_date) {
        return false
      }
      const oneWeekAgo = new Date()
      oneWeekAgo.setDate(oneWeekAgo.getDate() - 7)
      return oneWeekAgo > pub_date
    },
    story_in_reports() {
      return this.story ? this.story.in_reports_count : 0
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
      const tags = this.story.tags.map((tag) => tag.name)
      return tags.slice(0, this.openSummary ? tags.length : 5)
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

    storyRestricted() {
      return false
    }
  },
  updated() {
    // console.log('card rendered!')
  },
  mounted() {
    this.likes = this.story ? this.story.likes : 0
    this.dislikes = this.story ? this.story.dislikes : 0
  }
}
</script>
