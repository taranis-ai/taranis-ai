<template>
  <div>
    <DataTable
      :addButton="true"
      :items.sync="roles"
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
import { deleteRole, createRole, updateRole } from '@/api/config'
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
    selected: [],
    edit: false,
    permissions: []
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
          name: 'permissions',
          label: 'Permissions',
          type: 'table',
          headers: [
            { text: 'Name', value: 'name' },
            { text: 'Description', value: 'description' }
          ],
          items: this.permissions
        }
      ]
    }
  },
  methods: {
    ...mapActions('config', ['loadRoles', 'loadPermissions']),
    ...mapGetters('config', ['getRoles', 'getPermissions']),
    ...mapActions(['updateItemCount']),
    updateData() {
      this.loadRoles().then(() => {
        const sources = this.getRoles()
        this.roles = sources.items
        this.updateItemCount({
          total: sources.total_count,
          filtered: sources.length
        })
      })
      this.loadPermissions().then(() => {
        this.permissions = this.getPermissions().items
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
        deleteRole(item)
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
      createRole(item)
        .then(() => {
          notifySuccess(`Successfully created ${item.name}`)
          this.updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to create ${item.name}`)
        })
    },
    updateItem(item) {
      updateRole(item)
        .then(() => {
          notifySuccess(`Successfully updated ${item.name}`)
          this.updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to update ${item.name}`)
        })
    },
    selectionChange(selected) {
      this.selected = selected.map((item) => item.id)
    }
  },
  mounted() {
    this.updateData()
  },
  beforeDestroy() {}
}
</script>
