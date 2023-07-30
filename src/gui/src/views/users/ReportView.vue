<template>
  <v-container fluid style="min-height: 100vh">
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
import { useRoute } from 'vue-router'

export default {
  name: 'ReportView',
  components: {
    ReportItem
  },
  setup() {
    const route = useRoute()
    const default_report_item = ref({
      uuid: null,
      title: '',
      title_prefix: '',
      completed: false,
      report_item_type_id: null,
      news_item_aggregates: [],
      remote_report_items: [],
      attributes: []
    })
    const report_item = ref(default_report_item.value)
    const edit = ref(true)
    const readyToRender = ref(false)

    const loadReportItem = async () => {
      console.debug('Loading report item', route.params.id)
      if (route.params.id && route.params.id !== '0') {
        const response = await getReportItem(route.params.id)
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
