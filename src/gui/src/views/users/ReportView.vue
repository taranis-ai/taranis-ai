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
import { useAssessStore } from '@/stores/AssessStore'
import ReportItem from '@/components/analyze/ReportItem.vue'
import { useRoute } from 'vue-router'

export default {
  name: 'ReportView',
  components: {
    ReportItem
  },
  props: {
    reportId: {
      type: String,
      required: false,
      default: null
    }
  },
  setup(props) {
    const route = useRoute()
    const assessStore = useAssessStore()

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
      if (route.query.story) {
        const stories = await assessStore.getStoriesByID(route.query.story)
        return {
          ...default_report_item.value,
          stories: stories
        }
      }
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
