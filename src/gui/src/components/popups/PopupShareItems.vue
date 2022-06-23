<template>
  <v-card>
    <v-form ref="form" v-model="valid">
      <v-container>
        <v-row>
          <v-col cols="12">
            <h2
              class="
                font-weight-bold
                headline
                dark-grey--text
                text-capitalize
                pt-3
              "
            >
              Share Items
            </h2>
            The following Items were selected:
          </v-col>
        </v-row>
        <v-row no-gutters>
          <v-col
            cols="12"
            v-for="newsItemId in selection"
            :key="newsItemId"
            class="d-flex pa-0"
          >
            <v-card
              elevation="0"
              tile
              height="100%"
              :class="[
                'align-self-stretch d-flex flex-column share-items-details py-1 pr-1',
                {
                  restricted: getItemDetails(newsItemId).restricted,
                },
              ]"
            >
              <v-row justify="start" no-gutters class="flex-grow-0">
                <v-col cols="11" class="py-1">
                  <h4
                    class="
                      font-weight-bold
                      merge-topics-details-title
                      text-capitalize
                      my-1
                    "
                  >
                    <span
                      class="awake-red-color--text pr-3"
                      v-if="getItemDetails(newsItemId).restricted"
                    >
                      <v-icon color="awake-red-color" class="mb-1 mt-0">
                        mdi-alert-octagon-outline
                      </v-icon>
                      Restricted
                    </span>

                    {{ getItemDetails(newsItemId).title }}
                  </h4>
                </v-col>
                <v-col cols="1" class="d-flex align-content-center justify-end">
                  <v-btn
                    icon
                    tile
                    class="news-item-sharing-set-action"
                    @click="deselectNewsItem(newsItemId)"
                  >
                    <v-icon> $newsItemActionRemove </v-icon>
                  </v-btn>
                </v-col>
              </v-row>
            </v-card>
          </v-col>
        </v-row>
      </v-container>

      <v-container class="pb-0 mb-0">
        <v-row class="mt-4">
          <v-col cols="12" sm="6" @mouseover="appendMode = false" class="pr-5">
            <!---------------------------->
            <!-- Create new sharing set -->
            <!---------------------------->
            <h2
              class="
                font-weight-bold
                headline
                dark-grey--text
                text-capitalize
                pt-0
              "
            >
              Create new Sharing Set
            </h2>

            Create a new sharing set based on the currently selected items.
            Further items can be added afterwards. The set is not shared until
            it is explicitly sent.

            <v-text-field
              hide-details
              dense
              label="Sharing Set Title"
              outlined
              required
              v-model="sharingSetTitle"
              class="mb-2 mt-4"
            ></v-text-field>

            <v-switch
              v-model="autogenerateSummary"
              inset
              dense
              label="auto-generate summary"
              color="success"
              hide-details
              class="my-2"
            ></v-switch>
            <v-expand-transition appear v-if="!autogenerateSummary">
              <v-textarea
                v-model="sharingSetSummary"
                label="Summary"
                hide-details
                outlined
                class="my-2"
              ></v-textarea>
            </v-expand-transition>

            <v-btn
              color="primary"
              dark
              depressed
              :disabled="appendMode || !validCreateSettings"
              class="
                text-lowercase
                selection-toolbar-btn
                pr-4
                sharing-sumbit-btn
                mt-4
              "
              @click="createSharingSet()"
            >
              <v-icon left>$awakeShareOutline</v-icon>
              create sharing set
            </v-btn>
          </v-col>

          <v-divider class="d-none d-sm-flex" vertical></v-divider>

          <v-col cols="12" sm="6" @mouseover="appendMode = true" class="pl-5">
            <!--------------------------->
            <!-- Append to sharing set -->
            <!--------------------------->
            <h2
              class="
                font-weight-bold
                headline
                dark-grey--text
                text-capitalize
                pt-0
              "
            >
              Select Sharing Set
            </h2>

            Alternatively, the selected items can be added to an existing
            sharing set, which is then shared with the corresponding recipients.
            Also with this method, the sharing set must be explicitly sent.

            <v-combobox
              v-model="existingSharingSet"
              :items="getSharingSetSelectionList()"
              label="Sharing Set"
              placeholder="select Sharing Sets"
              return-object
              item-text="title"
              outlined
              dense
              hide-selected
              append-icon="mdi-chevron-down"
              class="pl-0 mb-5 mt-4"
              hide-details
              search-input
            >
              <template v-slot:item="{ item }">
                <span class="dropdown-list-item">
                  {{ item.title }}
                </span>
              </template>
              <template v-slot:selection="{ item }">
                <span class="text-capitalize">{{ item.title }}</span>
              </template>
            </v-combobox>
            <v-btn
              color="primary"
              dark
              depressed
              :disabled="!appendMode || !validAppendSettings"
              class="
                text-lowercase
                selection-toolbar-btn
                pr-4
                sharing-sumbit-btn
              "
              @click="appendToSharingSet()"
            >
              <!-- @click="mergeSelectedTopics()" -->
              <v-icon left>$awakeShareOutline</v-icon>
              append to sharing set
            </v-btn>
          </v-col>
        </v-row>
      </v-container>

      <v-divider class="mt-3"></v-divider>

      <v-card-actions class="mt-1">
        <v-spacer></v-spacer>
        <v-btn
          color="awake-red-color darken-1"
          outlined
          @click="$emit('input', false)"
          class="text-lowercase pr-4"
        >
          <v-icon left class="red-icon">$awakeClose</v-icon>
          abort
        </v-btn>
      </v-card-actions>
    </v-form>
  </v-card>
</template>

<script>
import { mapActions, mapGetters, mapState } from 'vuex'
import { faker } from '@faker-js/faker'

export default {
  name: 'PopupShareItems',
  components: {},
  props: {
    dialog: Boolean,
    selection: []
  },
  data: () => ({
    valid: true,
    appendMode: true,
    existingSharingSet: null,
    autogenerateSummary: true,
    sharingSetTitle: '',
    sharingSetSummary: ''
  }),
  methods: {
    ...mapActions('dashboard', ['createNewTopic', 'updateTopic']),
    ...mapActions('filter', ['resetNewsItemsFilter']),
    ...mapActions('assess', [
      'deselectNewsItem',
      'deselectAllNewsItems',
      'assignSharingSet'
    ]),
    ...mapGetters('assess', ['getNewsItemById']),
    ...mapGetters('dashboard', ['getTopicById', 'getSharingSetSelectionList']),

    getItemDetails (id) {
      return this.getNewsItemById()(parseInt(id))
    },

    // removeItemFromSelection(newsItemId) {
    //   this.deselectNewsItem(newsItemId)
    // },

    appendToSharingSet () {
      this.assignSharingSet({
        items: this.selection,
        sharingSet: this.existingSharingSet.id
      })

      const sharingSet = this.getTopicById()(this.existingSharingSet.id)
      sharingSet.sharingState = 'pending'
      this.updateTopic(sharingSet)

      this.leavePopup(this.existingSharingSet.id)
    },

    createSharingSet () {
      const newSharingSet = this.topicPrototype
      newSharingSet.title = this.sharingSetTitle
      newSharingSet.summary = this.sharingSetSummary
        ? this.sharingSetSummary
        : 'this is an AI created summary ... ' + faker.lorem.paragraph(10) // should be replaced by NLP algorithm
      newSharingSet.id = Math.floor(Math.random() * (700 - 500 + 1)) + 500 // get ID from creation

      this.createNewTopic(newSharingSet)
      this.assignSharingSet({
        items: this.selection,
        sharingSet: newSharingSet.id
      })

      this.leavePopup(newSharingSet.id)
    },

    leavePopup (id) {
      this.deselectAllNewsItems()
      this.resetNewsItemsFilter()

      const topic = this.getTopicById()(id)
      this.scope.sharingSets = [{ id: topic.id, title: topic.title }]
      this.scope.topics = []

      this.$router.push({
        path: '/assess',
        query: { topic: id }
      })

      this.$emit('input', false)
    }
  },
  computed: {
    ...mapState('filter', {
      scope: (state) => state.newsItemsFilter.scope
    }),

    validAppendSettings () {
      return this.existingSharingSet !== null
    },
    validCreateSettings () {
      return (
        this.sharingSetTitle !== '' &&
        (this.sharingSetSummary !== '' || this.autogenerateSummary)
      )
    },
    topicPrototype () {
      const newTopic = {
        id: null,
        relevanceScore: 100,
        title: '',
        tags: [],
        ai: false,
        originator: 'current user',
        hot: false,
        pinned: true,
        lastActivity: new Date(),
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
        hasSharedItems: true,
        isSharingSet: true,
        sharingState: 'not shared',
        sharingDirection: 'outgoing',
        sharedBy: 'current user',
        sharedWith: [],
        sharingSets: [],
        relatedTopics: [],
        keywords: []
      }

      this.selection.forEach((id) => {
        const selectedNewsItem = this.getNewsItemById()(id)
        newTopic.items.total++
        newTopic.items.new += selectedNewsItem.read ? 0 : 1

        // newTopic.comments.total += this.mergeDiscussion
        //   ? this.getTopicById()(id).comments.total
        //   : 0
        // newTopic.comments.new += this.mergeDiscussion
        //   ? this.getTopicById()(id).comments.new
        //   : 0

        // newTopic.votes.up += this.mergeVotes
        //   ? this.getTopicById()(id).votes.up
        //   : 0
        // newTopic.votes.down += this.mergeVotes
        //   ? this.getTopicById()(id).votes.down
        //   : 0
      })

      return newTopic
    }
  },
  mounted () {}
}
</script>
