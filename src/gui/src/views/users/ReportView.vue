<template>
  <v-container fluid style="min-height: 100vh">
    <report-item
      v-if="report_item"
      :report-item-prop="report_item"
      :edit="edit"
      @reportcreated="reportCreated"
    />
  </v-container>
</template>

<script>
import { getReportItem } from '@/api/analyze'
import ReportItem from '@/components/analyze/ReportItem.vue'
import { mapActions } from 'pinia'
import { useAssessStore } from '@/stores/AssessStore'
export default {
  name: 'ReportView',
  components: {
    ReportItem
  },
  data: () => ({
    default_report_item: {
      id: null,
      uuid: null,
      title: '',
      title_prefix: '',
      completed: false,
      report_item_type_id: null,
      news_item_aggregates: [],
      remote_report_items: [],
      attributes: []
    },
    report_item: undefined,
    edit: true
  }),
  async created() {
    this.report_item = await this.loadReportItem()
  },

  methods: {
    ...mapActions(useAssessStore, ['updateMaxItem']),
    async loadReportItem() {
      if (this.$route.params.id && this.$route.params.id !== '0') {
        return await getReportItem(this.$route.params.id).then((response) => {
          this.updateMaxItem(response.data.news_item_aggregates)
          return response.data
        })
      }
      this.edit = false
      return this.default_report_item
    },
    reportCreated() {
      this.edit = true
    }
  }
}
</script>
