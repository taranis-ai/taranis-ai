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
    <ReportTypeForm>
    </ReportTypeForm>
  </div>
</template>

<script>
import ConfigTable from '../../components/config/ConfigTable'
// import EditConfig from '../../components/config/EditConfig'
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
  computed: {
    formFormat() {
      return [
        {
          name: 'id',
          label: 'ID',
          type: 'text',
          disabled: true
        },
        {
          name: 'title',
          label: 'Title',
          type: 'text',
          required: true
        },
        {
          name: 'description',
          label: 'Description',
          type: 'textarea',
          required: true
        },
        {
          name: 'attribute_groups',
          label: 'Attribute Groups',
          type: 'table',
          addButton: true,
          headers: [
            { text: 'Title', value: 'title' },
            { text: 'Description', value: 'description' },
            { text: 'Section', value: 'section', type: 'number' },
            { text: 'Section Title', value: 'section_title' },
            { text: 'Index', value: 'index', type: 'number' },
            { text: 'Attribute Group Items', value: 'attribute_group_items' }
          ],
          items: this.formData.attribute_groups
        }
      ]
    }
  },
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
