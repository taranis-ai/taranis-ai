<template>
  <div>
    <DataTable
      :addButton="true"
      :items.sync="RemoteNodes"
      :headerFilter="['tag', 'name', 'title', 'description']"
      :actionColumn=true
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
import { deleteNode, createNode, updateNode } from '@/api/config'
import { mapActions, mapGetters } from 'vuex'
import { notifySuccess, notifyFailure, emptyValues } from '@/utils/helpers'

export default {
  name: 'RemoteNodes',
  components: {
    DataTable,
    EditConfig
  },
  data: () => ({
    RemoteNodes: [],
    selected: [],
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
    ...mapActions('config', ['loadRemoteNodes']),
    ...mapGetters('config', ['getRemoteNodes']),
    ...mapActions(['updateItemCount']),
    updateData() {
      this.loadRemoteNodes().then(() => {
        const sources = this.getRemoteNodes()
        this.RemoteNodes = sources.items
        this.updateItemCount({ total: sources.total_count, filtered: sources.length })
      })
    },
    addItem() {
      this.formData = emptyValues(this.RemoteNodes[0])
      this.edit = false
    },
    editItem(item) {
      if (item.bots) {
        this.worker_type = 'bots'
      } else if (item.collectors) {
        this.worker_type = 'collectors'
      } else {
        console.log('No workers found')
      }
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
      deleteNode(item).then(() => {
        notifySuccess(`Successfully deleted ${item.name}`)
        this.updateData()
      }).catch(() => {
        notifyFailure(`Failed to delete ${item.name}`)
      })
    },
    createItem(item) {
      createNode(item).then(() => {
        notifySuccess(`Successfully created ${item.name}`)
        this.updateData()
      }).catch(() => {
        notifyFailure(`Failed to create ${item.name}`)
      })
    },
    updateItem(item) {
      updateNode(item).then(() => {
        notifySuccess(`Successfully updated ${item.name}`)
        this.updateData()
      }).catch(() => {
        notifyFailure(`Failed to update ${item.name}`)
      })
    },
    selectionChange(selected) {
      this.selected = selected.map(item => item.id)
    }
  },
  mounted () {
    this.updateData()
  },
  beforeDestroy () {}
}
</script>
