<template>
  <div>
    <DataTable
      :addButton="true"
      :items.sync="attributes"
      :headerFilter="['tag', 'id', 'name', 'description']"
      sortByItem="id"
      :actionColumn="true"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
      @update-items="updateData"
    />
    <EditConfig
      v-if="formData && Object.keys(formData).length > 0"
      :configData="formData"
      :formFormat="formFormat"
      @submit="handleSubmit"
    ></EditConfig>
  </div>
</template>

<script>
import DataTable from '@/components/common/DataTable'
import EditConfig from '../../components/config/EditConfig'
import { deleteAttribute, createAttribute, updateAttribute } from '@/api/config'
import { mapActions, mapGetters } from 'vuex'
import { notifySuccess, emptyValues, notifyFailure } from '@/utils/helpers'

export default {
  name: 'Attributes',
  components: {
    DataTable,
    EditConfig
  },
  data: () => ({
    attributes: [],
    formData: {},
    edit: false,
    formFormat: [
      {
        name: 'id',
        label: 'ID',
        type: 'text',
        disabled: true
      },
      {
        name: 'name',
        label: 'Name',
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
        name: 'default_value',
        label: 'Default Value',
        type: 'text'
      },
      {
        name: 'type',
        label: 'Type',
        type: 'select',
        options: [
          'STRING',
          'NUMBER',
          'BOOLEAN',
          'RADIO',
          'ENUM',
          'TEXT',
          'RICH_TEXT',
          'DATE',
          'TIME',
          'DATE_TIME',
          'LINK',
          'ATTACHMENT',
          'TLP',
          'CVE',
          'CPE',
          'CVSS'
        ]
      },
      {
        name: 'validator',
        label: 'Validator',
        type: 'select',
        options: ['NONE', 'EMAIL', 'NUMBER', 'RANGE', 'REGEXP']
      },
      {
        name: 'validator_parameter',
        label: 'Validator Parameter',
        type: 'text'
      }
    ]
  }),
  methods: {
    ...mapActions('config', ['loadAttributes']),
    ...mapGetters('config', ['getAttributes']),
    ...mapActions(['updateItemCount']),
    updateData() {
      this.loadAttributes().then(() => {
        const sources = this.getAttributes()
        this.attributes = sources.items
        this.updateItemCount({
          total: sources.total_count,
          filtered: sources.length
        })
      })
    },
    addItem() {
      this.formData = emptyValues(this.attributes[0])
      this.edit = false
    },
    editItem(item) {
      this.formData = item
      this.edit = true
    },
    handleSubmit(submittedData) {
      console.log(submittedData)
      if (this.edit) {
        this.updateItem(submittedData)
      } else {
        this.createItem(submittedData)
      }
    },
    deleteItem(item) {
      if (!item.default) {
        deleteAttribute(item)
          .then(() => {
            notifySuccess(`Successfully deleted ${item.name}`)
            this.updateData()
          })
          .catch(() => {
            notifyFailure(`Failed to delete ${item.name}`)
          })
      }
    },
    createItem(item) {
      createAttribute(item)
        .then(() => {
          notifySuccess(`Successfully created ${item.name}`)
          this.updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to create ${item.name}`)
        })
    },
    updateItem(item) {
      updateAttribute(item)
        .then(() => {
          notifySuccess(`Successfully updated ${item.name}`)
          this.updateData()
        })
        .catch(() => {
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
