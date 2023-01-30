<template>
  <div>
    <ConfigTable
      :addButton="true"
      :items.sync="report_types"
      :headerFilter="['tag', 'id', 'title', 'description']"
      sortByItem="id"
      :actionColumn="true"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
    />
    <ReportTypeForm
      v-if="formData && Object.keys(formData).length > 0"
      :report_type_data="formData"
    >
    </ReportTypeForm>
  </div>
</template>

<script>
import ConfigTable from '../../components/config/ConfigTable'
import ReportTypeForm from '../../components/config/ReportTypeForm'
import {
  deleteReportItemType,
  createReportItemType,
  updateReportItemType
} from '@/api/config'
import { mapActions, mapGetters } from 'vuex'
import { notifySuccess, emptyValues, notifyFailure } from '@/utils/helpers'

export default {
  name: 'ReportTypes',
  components: {
    ConfigTable,
    ReportTypeForm
  },
  data: () => ({
    report_types: [],
    formData: {},
    edit: false
  }),
  computed: {},
  methods: {
    ...mapActions('config', ['loadReportItemTypesConfig']),
    ...mapGetters('config', ['getReportItemTypesConfig']),
    ...mapActions(['updateItemCount']),
    updateData() {
      this.loadReportItemTypesConfig().then(() => {
        const sources = this.getReportItemTypesConfig()
        this.report_types = sources.items
        this.updateItemCount({
          total: sources.total_count,
          filtered: sources.length
        })
      })
    },
    addItem() {
      this.formData = emptyValues(this.report_types[0])
      this.edit = false
    },
    editItem(item) {
      this.formData = item
      this.edit = true
    },
    handleSubmit(submittedData) {
      console.debug(submittedData)
      if (this.edit) {
        this.updateItem(submittedData)
      } else {
        this.createItem(submittedData)
      }
    },
    deleteItem(item) {
      if (!item.default) {
        deleteReportItemType(item).then(() => {
          notifySuccess(`Successfully deleted ${item.name}`)
          this.updateData()
        }).catch(() => {
          notifyFailure(`Failed to delete ${item.name}`)
        })
      }
    },
    createItem(item) {
      createReportItemType(item).then(() => {
        notifySuccess(`Successfully created ${item.name}`)
        this.updateData()
      }).catch(() => {
        notifyFailure(`Failed to create ${item.name}`)
      })
    },
    updateItem(item) {
      updateReportItemType(item).then(() => {
        notifySuccess(`Successfully updated ${item.name}`)
        this.updateData()
      }).catch(() => {
        notifyFailure(`Failed to update ${item.name}`)
      })
    }
  },
  mounted() {
    this.updateData()
  },
  beforeDestroy() {}
}
</script>
