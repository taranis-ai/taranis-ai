<template>
  <div>
    <DataTable
      :addButton="true"
      :items.sync="roles"
      sortByItem="id"
      :headerFilter="['tag', 'id', 'name', 'description']"
      :actionColumn="true"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
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
import {
  deleteNotificationTemplate,
  createNotificationTemplate,
  updateNotificationTemplate
} from '@/api/assets'
import { mapActions, mapGetters } from 'vuex'
import { notifySuccess, objectFromFormat, notifyFailure } from '@/utils/helpers'

export default {
  name: 'Roles',
  components: {
    DataTable,
    EditConfig
  },
  data: () => ({
    roles: [],
    formData: {},
    edit: false,
    permissions: []
  }),
  computed: {
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
            { text: 'Name', value: 'name' },
            { text: 'E-Mail', value: 'email' }
          ],
          items: this.formData.recipients || []
        }
      ]
    }
  },
  methods: {
    ...mapActions('assets', ['loadNotificationTemplates']),
    ...mapGetters('assets', ['getNotificationTemplates']),
    ...mapActions(['updateItemCount']),
    updateData() {
      this.loadNotificationTemplates().then(() => {
        const sources = this.getNotificationTemplates()
        this.roles = sources.items
        this.updateItemCount({
          total: sources.total_count,
          filtered: sources.length
        })
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
        deleteNotificationTemplate(item).then(() => {
          notifySuccess(`Successfully deleted ${item.name}`)
          this.updateData()
        }).catch(() => {
          notifyFailure(`Failed to delete ${item.name}`)
        })
      }
    },
    createItem(item) {
      createNotificationTemplate(item).then(() => {
        notifySuccess(`Successfully created ${item.name}`)
        this.updateData()
      }).catch(() => {
        notifyFailure(`Failed to create ${item.name}`)
      })
    },
    updateItem(item) {
      updateNotificationTemplate(item).then(() => {
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
