<template>
  <div>
    <DataTable
      v-model:items="attributes.items"
      :add-button="true"
      :header-filter="['tag', 'id', 'name', 'description']"
      sort-by-item="id"
      :action-column="true"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
      @update-items="updateData"
    />
    <EditConfig
      v-if="formData && Object.keys(formData).length > 0"
      :config-data="formData"
      :form-format="formFormat"
      @submit="handleSubmit"
    ></EditConfig>
  </div>
</template>

<script>
import DataTable from '@/components/common/DataTable.vue'
import EditConfig from '@/components/config/EditConfig.vue'
import { deleteAttribute, createAttribute, updateAttribute } from '@/api/config'
import { mapActions, mapState, mapWritableState } from 'pinia'
import { useConfigStore } from '@/stores/ConfigStore'
import { notifySuccess, emptyValues, notifyFailure } from '@/utils/helpers'
import { useMainStore } from '@/stores/MainStore'

export default {
  name: 'AttributesView',
  components: {
    DataTable,
    EditConfig
  },
  data: () => ({
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
        rules: [(v) => !!v || 'Required']
      },
      {
        name: 'description',
        label: 'Description',
        type: 'textarea',
        rules: [(v) => !!v || 'Required']
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
        ],
        rules: [(v) => !!v || 'Required']
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
  computed: {
    ...mapWritableState(useMainStore, ['itemCountTotal', 'itemCountFiltered']),
    ...mapState(useConfigStore, ['attributes'])
  },
  mounted() {
    this.updateData()
  },
  methods: {
    ...mapActions(useConfigStore, ['loadAttributes']),
    async updateData() {
      await this.loadAttributes()
      this.itemCountTotal = this.attributes.total_count
      this.itemCountFiltered = this.attributes.items.length
    },
    addItem() {
      this.formData = emptyValues(this.attributes.items[0])
      delete this.formData.attribute_enums
      delete this.formData.tag
      this.edit = false
    },
    editItem(item) {
      this.formData = item
      this.edit = true
    },
    handleSubmit(submittedData) {
      const nonemptyEntries = Object.entries(submittedData).filter(
        ([key, value]) => value !== ''
      )
      const nonemptyValues = Object.fromEntries(nonemptyEntries)
      console.debug('Submitting :', nonemptyValues)
      if (this.edit) {
        this.updateItem(nonemptyValues)
      } else {
        this.createItem(nonemptyValues)
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
  }
}
</script>
