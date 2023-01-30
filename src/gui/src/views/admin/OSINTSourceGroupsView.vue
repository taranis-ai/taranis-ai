<template>
  <div>
    <ConfigTable
      :addButton="true"
      :items.sync="osint_source_groups"
      :headerFilter="['tag', 'default', 'name', 'description']"
      sortByItem="id"
      :actionColumn="true"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
      @selection-change="selectionChange"
      @update-items="updateData"
    >
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
import {
  createOSINTSourceGroup,
  deleteOSINTSourceGroup,
  updateOSINTSourceGroup
} from '@/api/config'
import { mapActions, mapGetters } from 'vuex'
import { notifySuccess, objectFromFormat, notifyFailure } from '@/utils/helpers'

export default {
  name: 'OSINTSources',
  components: {
    ConfigTable,
    EditConfig
  },
  data: () => ({
    osint_source_groups: [],
    osint_sources: [],
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
          name: 'osint_sources',
          label: 'Sources',
          type: 'table',
          headers: [
            { text: 'Name', value: 'name' },
            { text: 'Description', value: 'description' }
          ],
          items: this.osint_sources
        }
      ]
    }
  },
  methods: {
    ...mapActions('config', ['loadOSINTSourceGroups', 'loadOSINTSources']),
    ...mapGetters('config', ['getOSINTSourceGroups', 'getOSINTSources']),

    ...mapActions(['updateItemCount']),
    updateData() {
      this.loadOSINTSourceGroups().then(() => {
        const sources = this.getOSINTSourceGroups()
        this.osint_source_groups = sources.items
        this.updateItemCount({
          total: sources.total_count,
          filtered: sources.length
        })
      })
      this.loadOSINTSources().then(() => {
        this.osint_sources = this.getOSINTSources().items
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
      if (this.edit) {
        console.debug(`Update: ${submittedData}`)
        this.updateItem(submittedData)
      } else {
        console.debug(`Create: ${submittedData}`)
        this.createItem(submittedData)
      }
    },
    deleteItem(item) {
      deleteOSINTSourceGroup(item).then(() => {
        notifySuccess(`Successfully deleted ${item.name}`)
        this.updateData()
      }).catch(() => {
        notifyFailure(`Failed to delete ${item.name}`)
      })
    },
    createItem(item) {
      createOSINTSourceGroup(item).then(() => {
        notifySuccess(`Successfully created ${item.name}`)
        this.updateData()
      }).catch(() => {
        notifyFailure(`Failed to create ${item.name}`)
      })
    },
    updateItem(item) {
      updateOSINTSourceGroup(item).then(() => {
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
  mounted() {
    this.updateData()
  },
  beforeDestroy() {}
}
</script>
