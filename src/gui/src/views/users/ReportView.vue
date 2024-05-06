<template>
  <v-container fluid>
    <report-item
      v-if="readyToRender"
      :edit="edit"
      :report-item-prop="report_item"
      @reportcreated="reportCreated"
    />
  </v-container>
</template>

<script>
import { ref, onBeforeMount } from 'vue'
import { getReportItem } from '@/api/analyze'
import ReportItem from '@/components/analyze/ReportItem.vue'

export default {
  name: 'ReportView',
  components: {
    ReportItem
  },
  props: {
    reportId: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const default_report_item = ref({
      title: '',
      completed: false,
      report_item_type_id: null,
      stories: []
    })
    const report_item = ref(default_report_item.value)
    const edit = ref(true)
    const readyToRender = ref(false)

    const loadReportItem = async () => {
      console.debug('Loading report item', props.reportId)
      if (props.reportId) {
        const response = await getReportItem(props.reportId)
        return response.data
      }
      edit.value = false
      return default_report_item.value
    }

    const reportCreated = () => {
      edit.value = true
    }

    onBeforeMount(async () => {
      report_item.value = await loadReportItem()
      readyToRender.value = true
    })

    return { report_item, edit, readyToRender, reportCreated }
  }
}
</script>
