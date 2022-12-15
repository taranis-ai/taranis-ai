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
          selected: selected,
          //'corner-tag-shared': item.shared && !item.restricted,
          //'corner-tag-restricted': item.restricted,
          //'status-important': item.important,
          //'status-unread': !item.read,
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

      <!-- Story Actions -->

      <div class="news-item-action-bar">
        <news-item-action-dialog
          icon="$newsItemActionRemove"
          tooltip="remove item"
          ref="deleteDialog"
        >
          <popup-delete-item
            :newsItem="newsItem"
            @deleteItem="deleteNewsItem()"
            @close="$refs.deleteDialog.close()"
          />
        </news-item-action-dialog>

        <news-item-action
          :active="newsItem.read"
          icon="$newsItemActionRead"
          @click="markAsRead()"
          tooltip="mark as read/unread"
        />

        <news-item-action
          :active="newsItem.important"
          icon="$newsItemActionImportant"
          @click="markAsImportant()"
          tooltip="mark as important"
        />

        <news-item-action
          :active="newsItem.decorateSource"
          icon="$newsItemActionRibbon"
          @click="decorateSource()"
          tooltip="emphasise originator"
        />

        <news-item-action-dialog
          icon="mdi-tag-outline"
          tooltip="manage tags"
          ref="manageTagsDialog"
        >
          <popup-manage-tags
            :newsItem="newsItem"
            @deleteItem="deleteNewsItem()"
            @close="$refs.manageTagsDialog.close()"
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
                  <news-item-title
                    :title="newsItem.title"
                    :read="newsItem.read"
                  />
                </v-col>
              </v-row>

              <v-row class="flex-grow-0 mt-0">
                <v-col>
                  <p class="news-item-summary">
                    {{ getDescription() }}
                  </p>
                </v-col>
              </v-row>

              <v-row class="flex-grow-0 mt-1">
                <v-col
                  cols="12"
                  class="mx-0 d-flex justify-start flex-wrap pt-1 pb-8"
                >
                  <button-outlined
                    label="view details"
                    icon="$awakeEye"
                    extraClass="mr-1 mt-1"
                    @click="viewDetails($event)"
                  />
                  <button-outlined
                    label="create report"
                    icon="$awakeReport"
                    extraClass="mr-1 mt-1"
                    @click="createReport($event)"
                  />
                  <button-outlined
                    label="show related items"
                    icon="$awakeRelated"
                    extraClass="mr-1 mt-1"
                    @click="showRelated($event)"
                  />

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
                  {{ getSource().name }} <br />
                  <a
                    :href="getSource().link"
                    target="_blank"
                    icon
                    class="meta-link d-flex"
                  >
                    <v-icon left x-small color="primary" class="mr-1"
                      >mdi-open-in-new</v-icon
                    >
                    <span class="label">{{ getSource().link }}</span>
                  </a>
                </v-col>
              </v-row>
              <v-row class="news-item-meta-infos">
                <v-col class="news-item-meta-infos-label">
                  <strong>Source Type:</strong>
                </v-col>
                <v-col>
                  {{ getSource().type }}
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
                      >$awakeRibbon</v-icon
                    >
                  </span>
                </v-col>
              </v-row>
              <!-- <v-row class="news-item-meta-infos">
                <v-col class="news-item-meta-infos-label">
                  <strong>Stories:</strong>
                </v-col>
                <v-col>
                  <span class="news-item-meta-stories-list text-capitalize">
                    {{ metaData.storiesList }}
                  </span>
                </v-col>
              </v-row> -->
              <v-row class="news-item-meta-infos">
                <v-col class="news-item-meta-infos-label d-flex align-center">
                  <strong>Tags:</strong>
                </v-col>
                <v-col>
                  <tag-list
                    key="tags"
                    limit=5
                    :tags="getTags()"
                  />
                </v-col>
              </v-row>
            </v-container>
          </v-col>
        </v-row>
      </v-container>
    </v-card>
    <NewsItemDetail ref="newsItemDetail" />
  </v-col>
</template>

<script>
import moment from 'moment'
import TagList from '@/components/common/tags/TagList'
import newsItemAction from '@/components/_subcomponents/newsItemAction'
import newsItemActionDialog from '@/components/_subcomponents/newsItemActionDialog'
import PopupDeleteItem from '@/components/popups/PopupDeleteItem'
import PopupManageTags from '@/components/popups/PopupManageTags'
import buttonOutlined from '@/components/_subcomponents/buttonOutlined'
import newsItemTitle from '@/components/_subcomponents/newsItemTitle'
import NewsItemDetail from '@/components/assess/NewsItemDetail'

import votes from '@/components/_subcomponents/votes'
import { isValidUrl, stripHtml } from '@/utils/helpers'

import { mapGetters } from 'vuex'

export default {
  name: 'CardNewsItem',
  components: {
    TagList,
    newsItemAction,
    newsItemActionDialog,
    PopupDeleteItem,
    PopupManageTags,
    buttonOutlined,
    newsItemTitle,
    NewsItemDetail,
    votes
  },
  props: {
    newsItem: {},
    storiesList: [],
    selected: Boolean
  },
  data: () => ({
  }),
  computed: {
    item_selected() {
      return this.has('selected') ? this.get('selected') : false
    },
    item_read() {
      return this.newsItem.has('read') ? this.newsItem.get('read') : false
    },
    item_important() {
      return this.newsItem.has('important') ? this.newsItem.get('important') : false
    },
    item_decorateSource() {
      return this.newsItem.has('decorateSource') ? this.newsItem.get('decorateSource') : false
    }
  },
  methods: {
    ...mapGetters('users', ['getUsernameById']),

    toggleSelection() {
      this.$emit('selectItem', this.newsItem.id)
    },
    markAsRead() {
      this.item_read = !this.item_read
    },
    markAsImportant() {
      this.item_important = !this.item_important
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

    viewDetails(event) {
      this.$refs.newsItemDetail.open(this.newsItem)
    },
    createReport(event) {
      console.log('not yet implemented')
    },
    showRelated(event) {
      console.log('not yet implemented')
    },

    getDescription() {
      return stripHtml(this.newsItem.description + this.newsItem.news_items[0].news_item_data.content)
    },

    getTags() {
      return this.newsItem.news_items[0].news_item_data.tags
    },

    getPublishedDate() {
      const published = this.newsItem.news_items[0].news_item_data.published
      if (published) return moment(published).format('DD/MM/YYYY hh:mm:ss')
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
    },

    getStoriesList() {
      const storyTitles = []
      this.newsItem.stories.forEach((id) => {
        const newStoryTitle = this.storiesList.find(
          (story) => story.id === id
        ).title
        if (storyTitles.indexOf(newStoryTitle) === -1) {
          storyTitles.push(newStoryTitle)
        }
      })

      return storyTitles.length ? storyTitles.join(', ') : '-'
    }
  },
  updated() {
    // console.log('card rendered!')
  },
  mounted() {
    this.$emit('init')
  }
}
</script>
