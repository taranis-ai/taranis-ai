<template>
  <v-col cols="12">
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
          selected: selected
        }
      ]"
      @click="toggleSelection"
    >
      <div
        v-if="newsItem.shared && !newsItem.restricted"
        class="news-item-corner-tag text-caption text-weight-bold text-uppercase white--text"
      >
        <v-icon x-small class="flipped-icon">mdi-share</v-icon>
      </div>

      <div
        v-if="newsItem.restricted"
        class="news-item-corner-tag text-caption text-weight-bold text-uppercase white--text"
      >
        <v-icon x-small>mdi-lock-outline</v-icon>
      </div>

      <!-- Story Actions -->

      <div class="news-item-action-bar">
        <news-item-action-dialog
          icon="mdi-delete"
          tooltip="remove item"
          :showDialog="deleteDialog"
          @close="deleteDialog = false"
        >
          <popup-delete-item
            v-if="deleteDialog"
            :newsItem="newsItem"
            @deleteItem="deleteNewsItem()"
            @close="deleteDialog = false"
          />
        </news-item-action-dialog>

        <news-item-action
          :active="newsItem.read"
          icon="mdi-email-mark-as-unread"
          @click="markAsRead()"
          tooltip="mark as read/unread"
        />

        <news-item-action
          :active="newsItem.important"
          icon="mdi-exclamation"
          @click="markAsImportant()"
          tooltip="mark as important"
        />

        <news-item-action
          :active="newsItem.decorateSource"
          icon="mdi-seal"
          @click="decorateSource()"
          tooltip="emphasise originator"
        />

        <news-item-action-dialog
          icon="mdi-google-circles-communities"
          tooltip="add to report"
          :showDialog="sharingDialog"
          @close="sharingDialog = false"
        >
          <popup-share-items
            v-if="sharingDialog"
            :newsItem="newsItem"
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
                  <h2 class="news-item-title">{{ newsItem.title }}</h2>
                </v-col>
              </v-row>

              <v-row class="flex-grow-0 mt-0">
                <v-col>
                  <p :class="news_item_summary_class">
                    {{ getDescription() }}
                  </p>
                </v-col>
              </v-row>

              <v-row class="flex-grow-0 mt-1">
                <v-col
                  cols="12"
                  class="mx-0 d-flex justify-start flex-wrap pt-1 pb-8"
                >
                  <v-btn
                    class="buttonOutlined mr-1 mt-1"
                    :style="{ borderColor: '#c8c8c8' }"
                    outlined
                    @click.stop="addToReport()"
                  >
                    <v-icon>mdi-google-circles-communities</v-icon>
                    <span>add to report</span>
                  </v-btn>
                  <v-btn
                    class="buttonOutlined mr-1 mt-1"
                    :style="{ borderColor: '#c8c8c8' }"
                    outlined
                    @click.stop="viewDetails = true"
                  >
                    <v-icon>mdi-eye</v-icon>
                    <span>view Details</span>
                  </v-btn>
                  <v-btn
                    class="buttonOutlined mr-1 mt-1"
                    :style="{ borderColor: '#c8c8c8' }"
                    outlined
                    @click.stop="openSummary = !openSummary"
                  >
                    <v-icon>{{ news_item_summary_icon }}</v-icon>
                    <span>{{ news_item_summary_text }}</span>
                  </v-btn>

                  <div class="d-flex align-start justify-center mr-3 ml-2 mt-1">
                    <votes
                      :count="newsItem.likes"
                      type="up"
                      @input="upvote($event)"
                    />
                  </div>
                  <div class="d-flex align-start justify-center mr-3 mt-1">
                    <votes
                      :count="newsItem.dislikes"
                      type="down"
                      @input="downvote($event)"
                    />
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
                  <span :class="published_date_outdated ? 'red--text' : ''">
                    {{ getPublishedDate() }}
                  </span>
                  <v-icon v-if="published_date_outdated" small color="red"
                    >mdi-alert</v-icon
                  >
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
                  {{ getSource().name }} <br />
                  <a
                    :href="getSource().link"
                    target="_blank"
                    icon
                    class="meta-link d-flex"
                  >
                    <v-icon left x-small color="primary"
                      >mdi-open-in-new</v-icon
                    >
                    <span class="label">{{ getSource().link }}</span>
                  </a>
                </v-col>
              </v-row>
              <v-row class="news-item-meta-infos">
                <v-col class="news-item-meta-infos-label">
                  <strong>Author:</strong>
                </v-col>
                <v-col>
                  <span :class="[{ decorateSource: newsItem.decorateSource }]">
                    {{ getAuthor() }}
                    <v-icon
                      right
                      small
                      v-if="newsItem.decorateSource"
                      class="ml-0"
                      >mdi-seal</v-icon
                    >
                  </span>
                </v-col>
              </v-row>
              <v-row class="news-item-meta-infos">
                <v-col class="news-item-meta-infos-label d-flex align-center">
                  <strong>Tags:</strong>
                </v-col>
                <v-col>
                  <tag-list key="tags" limit="5" :tags="getTags()" />
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
            </v-container>
          </v-col>
        </v-row>
      </v-container>
    </v-card>
    <NewsItemDetail
      v-if="viewDetails"
      @view="updateDetailsView"
      :view_details_prop.sync="viewDetails"
      :news_item_prop="newsItem.news_items[0]"
    />
  </v-col>
</template>

<script>
import moment from 'moment'
import TagList from '@/components/common/tags/TagList'
import newsItemAction from '@/components/_subcomponents/newsItemAction'
import newsItemActionDialog from '@/components/_subcomponents/newsItemActionDialog'
import PopupDeleteItem from '@/components/popups/PopupDeleteItem'
import PopupShareItems from '@/components/popups/PopupShareItems'

import NewsItemDetail from '@/components/assess/NewsItemDetail'
import votes from '@/components/_subcomponents/votes'
import { isValidUrl } from '@/utils/helpers'

import { mapGetters } from 'vuex'

export default {
  name: 'CardNewsItem',
  components: {
    TagList,
    newsItemAction,
    newsItemActionDialog,
    PopupDeleteItem,
    PopupShareItems,
    NewsItemDetail,
    votes
  },
  emits: [
    'selectItem',
    'deleteItem',
    'downvoteItem',
    'upvoteItem',
    'readItem',
    'importantItem'
  ],
  props: {
    newsItem: {},
    selected: Boolean
  },
  data: () => ({
    viewDetails: false,
    openSummary: false,
    sharingDialog: false,
    deleteDialog: false
  }),
  computed: {
    item_selected() {
      return this.has('selected') ? this.get('selected') : false
    },
    item_important() {
      return this.newsItem.has('important')
        ? this.newsItem.get('important')
        : false
    },
    item_decorateSource() {
      return this.newsItem.has('decorateSource')
        ? this.newsItem.get('decorateSource')
        : false
    },
    published_date() {
      const published = this.newsItem.news_items[0].news_item_data.published
      return published ? moment(published) : false
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
    news_item_summary_text() {
      return this.openSummary ? 'Close' : 'Open'
    },
    published_date_outdated() {
      const pub_date = this.published_date
      if (!pub_date) {
        return false
      }
      const last_week = moment().subtract(1, 'week') // date one week ago
      if (last_week.diff(pub_date, 'weeks') > 0) {
        return true
      }
      return false
    }
  },
  methods: {
    ...mapGetters('users', ['getUsernameById']),

    toggleSelection() {
      this.$emit('selectItem', this.newsItem.id)
    },
    markAsRead() {
      this.$emit('readItem', this.newsItem.id)
    },
    markAsImportant() {
      this.$emit('importantItem', this.newsItem.id)
    },
    decorateSource() {
      this.item_decorateSource = !this.item_decorateSource
    },
    deleteNewsItem() {
      this.$emit('deleteItem', this.newsItem.id)
    },
    upvote(event) {
      this.$emit('upvoteItem', this.newsItem.id)
    },
    downvote(event) {
      this.$emit('downvoteItem', this.newsItem.id)
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
      return this.newsItem.summary !== undefined && this.newsItem.summary !== ''
    },

    getDescription() {
      const summary = this.openSummary ? false : this.newsItem.summary
      return (
        summary ||
        this.newsItem.description ||
        this.newsItem.news_items[0].news_item_data.content ||
        this.newsItem.news_items[0].news_item_data.review
      )
    },

    getTags() {
      return this.newsItem.tags.map((tag) => tag.name)
    },

    getPublishedDate() {
      const published = this.published_date
      if (published) {
        return moment(published).format('DD/MM/YYYY hh:mm:ss')
      }
      return '** no published date **'
    },

    getCollectedDate() {
      const collected = this.newsItem.news_items[0].news_item_data.collected
      if (collected) {
        return moment(collected, 'DD.MM.YYYY - hh:mm').format(
          'DD/MM/YYYY hh:mm:ss'
        )
      }
      return moment(this.newsItem.created, 'DD.MM.YYYY - hh:mm').format(
        'DD/MM/YYYY hh:mm:ss'
      )
    },

    getAuthor() {
      const author = this.newsItem.news_items[0].news_item_data.author
      if (author) return author
      return '** no author given **'
    },

    getSource() {
      let source = this.newsItem.news_items[0].news_item_data.source
      if (isValidUrl(source)) {
        source = new URL(source).hostname.replace('www.', '')
      }

      // TODO: get Type (e.g. RSS, Web, Email, ...)

      return {
        name: source,
        link: this.newsItem.news_items[0].news_item_data.link,
        type: this.newsItem.news_items[0].news_item_data.osint_source_id
      }
    }
  },
  updated() {
    // console.log('card rendered!')
  },
  mounted() {}
}
</script>
