<template>
  <div>
    <ConfigTable
      :addButton="true"
      :items.sync="nodes"
      :headerFilter="['tag', 'name', 'description']"
      :actionColumn="true"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
      @update-items="updateData"
      @selection-change="selectionChange"
    >
      <template v-slot:titlebar>
        <v-btn color="blue-grey" dark class="ml-4" @click="triggerWorkers">
          <v-icon>mdi-run</v-icon>Trigger Workers
        </v-btn>
      </template>
    </ConfigTable>
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
import { deleteNode, createNode, updateNode, triggerNode } from '@/api/config'
import { mapActions, mapGetters } from 'vuex'
import { notifySuccess, notifyFailure, objectFromFormat } from '@/utils/helpers'

export default {
  name: 'Nodes',
  components: {
    ConfigTable,
    EditConfig
  },
  data: () => ({
    nodes: [],
    formData: {},
    edit: false,
    selected: [],
    workers: []
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
        },
        {
          name: this.formData.type,
          label: `${this.formData.type} Types`,
          type: 'table',
          disabled: true,
          headers: [
            { text: 'Name', value: 'name' },
            { text: 'Description', value: 'description' },
            { text: 'Type', value: 'type' }
          ],
          items: this.workers
        }
      ]
    }
  },
  methods: {
    ...mapActions('config', ['loadNodes', 'loadCollectors']),
    ...mapGetters('config', ['getNodes', 'getCollectors']),
    ...mapActions(['updateItemCount']),
    updateData() {
      this.loadNodes().then(() => {
        const sources = this.getNodes()
        this.nodes = sources.items
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
      if (item.type === 'bot') {
        this.workers = item.bots
      } else if (item.type === 'collector') {
        this.loadCollectors().then(() => {
          this.workers = this.getCollectors().items
        })
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
      deleteNode(item)
        .then(() => {
          notifySuccess(`Successfully deleted ${item.name}`)
          this.updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to delete ${item.name}`)
        })
    },
    createItem(item) {
      createNode(item)
        .then(() => {
          notifySuccess(`Successfully created ${item.name}`)
          this.updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to create ${item.name}`)
        })
    },
    updateItem(item) {
      updateNode(item)
        .then(() => {
          notifySuccess(`Successfully updated ${item.name}`)
          this.updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to update ${item.name}`)
        })
    },
    selectionChange(selected) {
      this.selected = selected.map(item => item.id)
    },
    triggerWorkers() {
      triggerNode().then(() => {
        notifySuccess('Node run triggerd')
      })
    }
  },
  mounted() {
    this.updateData()
  },
  beforeDestroy() {}
}
</script>
