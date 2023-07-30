<template>
  <div>
    <DeprecationWarning />
    <DataTable
      v-model:items="roles"
      :add-button="true"
      sort-by-item="id"
      :header-filter="['tag', 'id', 'name', 'description']"
      :action-column="true"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
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
import DeprecationWarning from '@/components/common/DeprecationWarning.vue'
import {
  deleteNotificationTemplate,
  createNotificationTemplate,
  updateNotificationTemplate
} from '@/api/assets'
import { mapActions, mapState, mapWritableState } from 'pinia'
import { notifySuccess, objectFromFormat, notifyFailure } from '@/utils/helpers'
import { useAssetsStore } from '@/stores/AssetsStore'
import { useMainStore } from '@/stores/MainStore'

export default {
  name: 'NotificationTemplatesView',
  components: {
    DataTable,
    EditConfig,
    DeprecationWarning
  },
  data: () => ({
    roles: [],
    formData: {},
    edit: false,
    permissions: []
  }),
  computed: {
    ...mapState(useAssetsStore, ['notification_templates']),
    ...mapWritableState(useMainStore, ['itemCountTotal', 'itemCountFiltered']),
    formFormat() {
      return [
        {
          name: 'id',
          label: 'ID',
          type: 'number',
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
          name: 'message_title',
          label: 'Message Title',
          type: 'text'
        },
        {
          name: 'message_body',
          label: 'Message Body',
          type: 'textarea'
        },
        {
          name: 'recipients',
          label: 'Recipients',
          type: 'table',
          addButton: true,
          headers: [
            { title: 'Name', key: 'name' },
            { title: 'E-Mail', key: 'email' }
          ],
          items: this.formData.recipients || []
        }
      ]
    }
  },
  mounted() {
    this.updateData()
  },
  methods: {
    ...mapActions(useAssetsStore, ['loadNotificationTemplates']),
    updateData() {
      this.loadNotificationTemplates().then(() => {
        const sources = this.notification_templates
        this.roles = sources.items
        this.itemCountFiltered = sources.length
        this.itemCountTotal = sources.total_count
      })
    },
    addItem() {
      this.formData = objectFromFormat(this.formFormat)
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
        deleteNotificationTemplate(item)
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
      createNotificationTemplate(item)
        .then(() => {
          notifySuccess(`Successfully created ${item.name}`)
          this.updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to create ${item.name}`)
        })
    },
    updateItem(item) {
      updateNotificationTemplate(item)
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
