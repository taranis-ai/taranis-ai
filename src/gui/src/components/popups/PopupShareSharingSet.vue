<template>
  <v-card>
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
            Share Sharing Set
          </h2>
          <span v-if="!sharingSet.sharedWith.length">
            This sharing set has not yet been shared. Please select one or more
            recipients with whom this set should be shared.
          </span>
          <span v-else>
            This sharing set has already been shared with
            <strong> {{ currentRecipientList }}</strong
            >. You have the option of adding more recipients or sharing the set
            again with the same list of recipients.
          </span>
        </v-col>
      </v-row>
      <v-row>
        <v-col cols="12">
          <dropdown-selection
            v-model="recipients"
            :items="getUsersSelectionList()"
            attribute="username"
            label="Recipients"
            placeholder=""
          />
        </v-col>
      </v-row>

      <v-row v-if="hasRestrictedItems">
        <v-col cols="12">
          <span class="awake-red-color--text pr-3">
            <v-icon color="awake-red-color" class="mb-1 mt-0">
              mdi-alert-octagon-outline
            </v-icon>
            <strong>Attention!</strong> The sharing set you are about to share
            contains items that are marked as restricted.
          </span>
        </v-col>
      </v-row>
    </v-container>

    <v-divider></v-divider>

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

      <v-btn
        color="primary"
        dark
        depressed
        @click="share()"
        class="text-lowercase selection-toolbar-btn pr-4"
      >
        <v-icon left>$awakeShareOutline</v-icon>
        share
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import { mapActions, mapGetters, mapState } from 'vuex'
import { xorConcat } from '@/utils/helpers'
import dropdownSelection from '@/components/_subcomponents/dropdownSelection'

export default {
  name: 'PopupShareSharingSet',
  components: {
    dropdownSelection
  },
  props: {
    dialog: Boolean,
    sharingSet: {},
    hasRestrictedItems: Boolean,
    currentRecipientList: []
  },
  data: () => ({
    recipients: []
  }),
  methods: {
    ...mapActions('dashboard', ['createNewTopic', 'updateTopic']),
    ...mapActions('filter', ['resetNewsItemsFilter']),
    ...mapActions('assess', [
      'deselectNewsItem',
      'deselectAllNewsItems',
      'assignSharingSet'
    ]),
    ...mapGetters('users', ['getUsersSelectionList']),
    ...mapGetters('assess', ['getNewsItemById']),
    ...mapGetters('dashboard', ['getTopicById', 'getSharingSetSelectionList']),

    recipientsSelectionList () {
      this.getUsersSelectionList()
    },

    share () {
      this.sharingSet.sharingState = 'shared'
      this.sharingSet.sharedWith = this.recipients
      this.$emit('input', false)
    }
  },
  mounted () {
    this.recipients = this.sharingSet.sharedWith.length
      ? this.sharingSet.sharedWith
      : []
  }
}
</script>
