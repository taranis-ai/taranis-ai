<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilter title="nav_menu.report_types" total_count_title="report_type.total_count"
                           total_count_getter="getReportItemTypesConfig">
                <template v-slot:addbutton>
                    <NewReportType/>
                </template>
            </ToolbarFilter>
        </template>
        <template v-slot:content>
            <ContentData
                    name="ReportTypes"
                    cardItem="CardCompact"
                    action="getAllReportItemTypesConfig"
                    getter="getReportItemTypesConfig"
                    deletePermission="CONFIG_REPORT_TYPE_DELETE"
            />
        </template>
    </ViewLayout>
</template>

<script>
import ViewLayout from '../../components/layouts/ViewLayout'
import ToolbarFilter from '../../components/common/ToolbarFilter'
import ContentData from '../../components/common/content/ContentData'
import NewReportType from '../../components/config/report_types/NewReportType'
import { deleteReportItemType } from '@/api/config'

export default {
  name: 'ReportTypes',
  components: {
    ViewLayout,
    ToolbarFilter,
    ContentData,
    NewReportType
  },
  data: () => ({}),
  mounted () {
    this.$root.$on('delete-item', (item) => {
      deleteReportItemType(item).then(() => {
        this.$root.$emit('notification',
          {
            type: 'success',
            loc: 'report_type.removed'
          }
        )
      }).catch(() => {
        this.$root.$emit('notification',
          {
            type: 'error',
            loc: 'report_type.removed_error'
          }
        )
      })
    })
  },
  beforeDestroy () {
    this.$root.$off('delete-item')
  }
}
</script>
