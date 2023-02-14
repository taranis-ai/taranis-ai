<template>
  <div>
    <DataTable
      :addButton="false"
      :items.sync="bots"
      :headerFilter="['name', 'description']"
      sortByItem="name"
      :actionColumn="false"
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
import {
  updateBot
} from '@/api/config'
import { mapActions, mapGetters } from 'vuex'
import { notifySuccess, objectFromFormat, notifyFailure, parseParameterValues, parseSubmittedParameterValues } from '@/utils/helpers'

export default {
  name: 'Bots',
  components: {
    DataTable,
    EditConfig
  },
  data: () => ({
    bots: [],
    unparsed_bots: [],
    formData: {},
    parameters: {},
    bot_types: [],
    edit: false
  }),
  computed: {
    formFormat() {
      const base = [
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
          name: 'type',
          label: 'Type',
          type: 'select',
          required: true,
          options: this.bot_types,
          disabled: this.edit
        }
      ]
      if (this.parameters[this.formData.type]) {
        return base.concat(this.parameters[this.formData.type])
      }
      return base
    }
  },
  methods: {
    ...mapActions('config', ['loadBots', 'loadParameters']),
    ...mapGetters('config', ['getBots', 'getParameters']),
    ...mapActions(['updateItemCount']),
    updateData() {
      this.loadBots().then(() => {
        const sources = this.getBots()
        this.unparsed_sources = sources.items
        this.bots = parseParameterValues(sources.items)

        this.bot_types = sources.items.map(item => {
          this.parameters[item.type] = item.parameter_values.map(param => {
            return {
              name: param.parameter.key,
              label: param.parameter.key,
              type: 'text'
            }
          })
          return item.type
        })
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
      const params = parseSubmittedParameterValues(this.unparsed_bots, submittedData)
      if (this.edit) {
        this.updateItem(params)
      } else {
        this.createItem(params)
      }
    },
    deleteItem(item) {
      notifyFailure('Deleting Bots not supported')
    },
    createItem(item) {
      notifyFailure('Creating Bots not supported')
    },
    updateItem(item) {
      updateBot(item).then(() => {
        notifySuccess(`Successfully updated ${item.id}`)
        this.updateData()
      }).catch(() => {
        notifyFailure(`Failed to update ${item.id}`)
      })
    }
  },
  mounted() {
    this.updateData()
  },
  beforeDestroy() {}
}
</script>
