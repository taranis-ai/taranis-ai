<template>
  <v-card
    tile
    elevation="4"
    outlined
    :ripple="false"
    v-on="storyView ? { click: toggleSelection } : null"
  >
    <div
      v-if="newsItem.shared && !newsItem.restricted"
      class="news-item-corner-tag text-caption text-weight-bold text-uppercase white--text"
    >
      <v-icon x-small class="flipped-icon">mdi-share</v-icon>
    </div>

    <!-- Actions -->

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
        @open="sharingDialog = true"
      >
        <popup-share-items
          v-if="sharingDialog"
          :item_ids="[newsItem.id]"
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
                <h2 class="news-item-title">
                  {{ newsItem.news_item_data.title }}
                </h2>
              </v-col>
            </v-row>

            <v-row class="flex-grow-0 mt-0">
              <v-col>
                <p class="news-item-summary">
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
                class="mx-0 d-flex justify-start flex-wrap pt-1 pb-8"
              >
                <v-btn class="mr-1 mt-1" outlined @click.stop="addToReport()">
                  <v-icon>mdi-google-circles-communities</v-icon>
                  <span>add to report</span>
                </v-btn>
                <v-btn
                  class="mr-1 mt-1"
                  outlined
                  :to="'/newsitem/' + newsItem.id"
                  v-on:click.stop
                  v-ripple="false"
                >
                  <v-icon>mdi-eye</v-icon>
                  <span>view Details</span>
                </v-btn>
                <v-btn
                  class="mr-1 mt-1"
                  outlined
                  @click.stop="removeFromStory()"
                >
                  <v-icon>mdi-ungroup</v-icon>
                  <span>remove from Story</span>
                </v-btn>
              </v-col>
            </v-row>
            <metainfo :newsItem="newsItem" />
          </v-container>
        </v-col>
      </v-row>
    </v-container>
  </v-card>
</template>

<script>
import newsItemAction from '@/components/_subcomponents/newsItemAction'
import newsItemActionDialog from '@/components/_subcomponents/newsItemActionDialog'
import PopupDeleteItem from '@/components/popups/PopupDeleteItem'
import PopupShareItems from '@/components/popups/PopupShareItems'
import metainfo from '@/components/assess/card/metainfo'
import { notifySuccess, notifyFailure } from '@/utils/helpers'

import { mapGetters } from 'vuex'

import {
  deleteNewsItemAggregate,
  importantNewsItemAggregate,
  readNewsItemAggregate,
  unGroupAction
} from '@/api/assess'

export default {
  name: 'CardNewsItem',
  components: {
    metainfo,
    newsItemAction,
    newsItemActionDialog,
    PopupDeleteItem,
    PopupShareItems
  },
  emits: ['selectItem', 'deleteItem'],
  props: {
    newsItem: {},
    selected: Boolean,
    storyView: Boolean
  },
  data: () => ({
    viewDetails: false,
    sharingDialog: false,
    deleteDialog: false,
    likes: 0,
    dislikes: 0
  }),
  computed: {
    item_important() {
      return 'important' in this.newsItem ? this.newsItem.important : false
    },
    item_decorateSource() {
      return 'decorateSource' in this.newsItem
        ? this.newsItem.decorateSource
        : false
    }
  },
  methods: {
    ...mapGetters('users', ['getUsernameById']),

    toggleSelection() {
      alert('toggleSelection')
      this.$emit('selectItem', this.newsItem.id)
    },
    markAsRead() {
      readNewsItemAggregate(this.newsItem.id)
    },
    markAsImportant() {
      importantNewsItemAggregate(this.newsItem.id)
    },
    decorateSource() {
      this.item_decorateSource = !this.item_decorateSource
    },
    deleteNewsItem() {
      deleteNewsItemAggregate(this.newsItem.id)
      this.$emit('deleteItem', this.newsItem.id)
    },
    addToReport() {
      this.sharingDialog = true
    },

    updateDetailsView(value) {
      this.viewDetails = value
    },

    getDescription() {
      return (
        this.newsItem.news_item_data.content ||
        this.newsItem.news_item_data.review
      )
    },

    removeFromStory() {
      unGroupAction([this.newsItem.id])
        .then(() => {
          notifySuccess('News Item removed from Story')

          this.$emit('refresh')
        })
        .catch((err) => {
          notifyFailure('Failed to remove Newsitem from Story')
          console.log(err)
        })
    }
  },
  updated() {
    // console.log('card rendered!')
  },
  mounted() {
    this.likes = this.newsItem.likes
    this.dislikes = this.newsItem.dislikes
  }
}
</script>
