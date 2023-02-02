<template>
  <v-container fluid style="min-height: 100vh">
    <report-item v-if="report_item" :report_item_prop="report_item" :edit.sync="edit" @reportcreated="reportCreated"/>
  </v-container>
</template>

<script>
import { getReportItem } from '@/api/analyze'
import ReportItem from '@/components/analyze/ReportItem'
import { notifySuccess } from '@/utils/helpers'

export default {
  name: 'ReportView',
  data: () => ({
    report_item: undefined,
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
    edit: true
  }),
  components: {
    ReportItem
  },
  async created() {
    this.report_item = await this.loadReportItem()
    if (this.report_item === undefined) {
      this.edit = false
      this.report_item = this.default_report_item
    }
  },
  methods: {
    async loadReportItem() {
      if (this.$route.params.id && this.$route.params.id !== '0') {
        return await getReportItem(this.$route.params.id).then((response) => {
          return response.data
        })
      }
    },
    reportCreated(report_item) {
      notifySuccess(`Report with ID ${report_item} created`)
      this.edit = true
    }
  }
}
</script>
