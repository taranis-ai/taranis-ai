<template>
  <v-card>
    <v-card-text>
      <v-select
          solo
          single-line
          label="Select Report"
          v-model="reportItemSelection"
          :items="reportItems"
       />
    </v-card-text>
    <v-card-actions class="mt-1">
      <v-btn
        color="awake-red-color darken-1"
        outlined
        @click="$emit('input', false)"
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
import { getReportItemData, updateReportItem } from '@/api/analyze'

export default {
  name: 'PopupShareItems',
  components: {
  },
  props: {
    newsItem: [],
    dialog: Boolean
  },
  data: () => ({
    reportItems: [],
    reportItemSelection: {}
  }),
  methods: {
    ...mapGetters('assess', ['getNewsItemById']),
    ...mapGetters('analyze', ['getReportItems']),
    ...mapActions('analyze', ['loadReportItems']),

    share () {
      if (this.dialog === 7) {
        getReportItemData()
        updateReportItem()
      }
      console.log(`Share ${this.newsItem} with ${this.reportItemSelection}`)
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
