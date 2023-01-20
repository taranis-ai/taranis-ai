<template>
  <div>
    <ConfigTable
      :addButton="true"
      :items.sync="RemoteAccess"
      :headerFilter="['tag', 'name', 'title', 'description']"
      :actionColumn=true
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
import ConfigTable from '../../components/config/ConfigTable'
import EditConfig from '../../components/config/EditConfig'
import { deleteRemoteAccess, createRemoteAccess, updateRemoteAccess } from '@/api/config'
import { mapActions, mapGetters } from 'vuex'
import { notifySuccess, notifyFailure, emptyValues } from '@/utils/helpers'

export default {
  name: 'RemoteAccess',
  components: {
    ConfigTable,
    EditConfig
  },
  data: () => ({
    RemoteAccess: [],
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
          name: 'api_url',
          label: 'Node URL',
          type: 'text'
        },
        {
          name: 'api_key',
          label: 'API Key',
          type: 'text'
        }
      ]
    }
  },
  methods: {
    ...mapActions('config', ['loadRemoteAccesses']),
    ...mapGetters('config', ['getRemoteAccesses']),
    ...mapActions(['updateItemCount']),
    updateData() {
      this.loadRemoteAccesses().then(() => {
        const sources = this.getRemoteAccesses()
        this.RemoteAccess = sources.items
        this.updateItemCount({ total: sources.total_count, filtered: sources.length })
      })
    },
    addItem() {
      this.formData = emptyValues(this.RemoteAccess[0])
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
      console.log(item)
      deleteRemoteAccess(item).then(() => {
        notifySuccess(`Successfully deleted ${item.name}`)
        this.updateData()
      }).catch(() => {
        notifyFailure(`Failed to delete ${item.name}`)
      })
    },
    createItem(item) {
      createRemoteAccess(item).then(() => {
        notifySuccess(`Successfully created ${item.name}`)
        this.updateData()
      }).catch(() => {
        notifyFailure(`Failed to create ${item.name}`)
      })
    },
    updateItem(item) {
      updateRemoteAccess(item).then(() => {
        notifySuccess(`Successfully updated ${item.name}`)
        this.updateData()
      }).catch(() => {
        notifyFailure(`Failed to update ${item.name}`)
      })
    }
  },
  mounted () {
    this.updateData()
  },
  beforeDestroy () {}
}
</script>
