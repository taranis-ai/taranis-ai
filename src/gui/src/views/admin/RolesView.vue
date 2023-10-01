<template>
  <v-container fluid>
    <DataTable
      :items="roles.items"
      :add-button="true"
      :header-filter="['tag', 'id', 'name', 'description', 'actions']"
      tag-icon="mdi-account-arrow-right"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
      @update-items="updateData"
    />
    <EditConfig
      v-if="showForm"
      :config-data="formData"
      :form-format="formFormat"
      :title="editTitle"
      @submit="handleSubmit"
    ></EditConfig>
  </v-container>
</template>

<script>
import DataTable from '@/components/common/DataTable.vue'
import EditConfig from '@/components/config/EditConfig.vue'
import { deleteRole, createRole, updateRole } from '@/api/config'
import { ref, onMounted, computed } from 'vue'
import { useConfigStore } from '@/stores/ConfigStore'
import { useMainStore } from '@/stores/MainStore'
import { storeToRefs } from 'pinia'
import { notifySuccess, objectFromFormat, notifyFailure } from '@/utils/helpers'

export default {
  name: 'RolesView',
  components: {
    DataTable,
    EditConfig
  },
  setup() {
    const store = useConfigStore()
    const mainStore = useMainStore()
    const { roles, permissions } = storeToRefs(store)
    const formData = ref({})
    const selected = ref([])
    const edit = ref(false)
    const showForm = ref(false)

    const formFormat = computed(() => [
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
        name: 'permissions',
        label: 'Permissions',
        type: 'table',
        headers: [
          { title: 'ID', key: 'id' },
          { title: 'Name', key: 'name' },
          { title: 'Description', key: 'description' }
        ],
        items: permissions.value.items
      }
    ])

    const updateData = () => {
      store.loadRoles().then(() => {
        mainStore.itemCountTotal = roles.value.total_count
        mainStore.itemCountFiltered = roles.value.items.length
      })
      store.loadPermissions().then()
    }

    const addItem = () => {
      formData.value = objectFromFormat(formFormat.value)
      delete formData.value['id']
      edit.value = false
      showForm.value = true
    }

    const editItem = (item) => {
      formData.value = item
      edit.value = true
      showForm.value = true
    }

    const editTitle = computed(() => {
      return edit.value ? `Edit Role: '${formData.value['name']}'` : 'Add Role'
    })

    const handleSubmit = (submittedData) => {
      if (edit.value) {
        updateItem(submittedData)
      } else {
        createItem(submittedData)
      }
      showForm.value = false
    }

    const deleteItem = (item) => {
      if (!item.default) {
        deleteRole(item)
          .then(() => {
            notifySuccess(`Successfully deleted ${item.name}`)
            updateData()
          })
          .catch(() => {
            notifyFailure(`Failed to delete ${item.name}`)
          })
      }
    }

    const createItem = (item) => {
      createRole(item)
        .then(() => {
          notifySuccess(`Successfully created ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to create ${item.name}`)
        })
    }

    const updateItem = (item) => {
      updateRole(item)
        .then(() => {
          notifySuccess(`Successfully updated ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to update ${item.name}`)
        })
    }

    const selectionChange = (new_selection) => {
      selected.value = new_selection
    }

    onMounted(() => {
      updateData()
    })

    return {
      roles,
      formData,
      selected,
      editTitle,
      permissions,
      formFormat,
      showForm,
      addItem,
      editItem,
      handleSubmit,
      deleteItem,
      selectionChange,
      updateData
    }
  }
}
</script>
