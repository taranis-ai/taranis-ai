<template>
  <v-card>
    <v-card-title>
      <span class="headline">Share Items</span>
    </v-card-title>
    <v-card-text>
      Select a report to share the item with:
      <v-select
          solo
          single-line
          label="Select Report"
          v-model="reportItemSelection"
          no-data-text="No reports found"
          :items="reportItems"
       />
    </v-card-text>
    <v-card-actions class="mt-1">
      <v-btn
        color="awake-red-color darken-1"
        outlined
        @click="close()"
        class="text-lowercase pr-4"
      >
        <v-icon left class="red-icon">mdi-close</v-icon>
        abort
      </v-btn>

      <v-btn
        color="primary"
        dark
        depressed
        @click="share()"
        class="text-lowercase selection-toolbar-btn pr-4"
      >
        <v-icon left>mdi-share-outline</v-icon>
        share
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import { mapGetters, mapActions } from 'vuex'
import { updateReportItem } from '@/api/analyze'

export default {
  name: 'PopupShareItems',
  components: {
  },
  props: {
    newsItem: [],
    dialog: Boolean
  },
  emits: ['close'],
  data: () => ({
    reportItems: [],
    reportItemSelection: {}
  }),
  methods: {
    ...mapGetters('assess', ['getNewsItemById']),
    ...mapGetters('analyze', ['getReportItems']),
    ...mapActions('analyze', ['loadReportItems']),

    share () {
      const reportItemData = { add: true, report_item_id: this.reportItemSelection, aggregate_ids: [this.newsItem.id] }
      console.debug(reportItemData)
      updateReportItem(this.reportItemSelection, reportItemData)
      this.close()
    },
    close () {
      this.$emit('close')
    }
  },
  mounted () {
    this.loadReportItems().then(() => {
      this.reportItems = this.getReportItems().map(item => {
        return {
          text: item.title,
          value: item.id
        }
      })
      console.debug(this.reportItems)
    })
  }
}
</script>
