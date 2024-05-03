<template>
  <v-container fluid>
    <DataTable
      v-model:items="users.items"
      :add-button="true"
      :header-filter="[
        'id',
        'username',
        'name',
        'roles.length',
        'permissions.length',
        'actions'
      ]"
      :sort-by="sortBy"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
      @update-items="updateData"
      @selection-change="selectionChange"
    >
      <template #titlebar>
        <ImportExport @import="importData" @export="exportData" />
      </template>
    </DataTable>
    <UserForm
      v-if="showForm"
      :user-prop="user"
      :edit="edit"
      @updated="formUpdated"
    />
  </v-container>
</template>

<script>
import DataTable from '@/components/common/DataTable.vue'
import UserForm from '@/components/config/user/UserForm.vue'
import ImportExport from '@/components/config/ImportExport.vue'
import {
  deleteUser,
  createUser,
  updateUser,
  importUsers,
  exportUsers
} from '@/api/config'
import { ref, onMounted } from 'vue'
import { useConfigStore } from '@/stores/ConfigStore'
import { useMainStore } from '@/stores/MainStore'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { storeToRefs } from 'pinia'

export default {
  name: 'UsersView',
  components: {
    ImportExport,
    DataTable,
    UserForm
  },
  setup() {
    const store = useConfigStore()
    const { users } = storeToRefs(store)
    const mainStore = useMainStore()
    const showForm = ref(false)
    const selected = ref([])
    const user = ref({})
    const edit = ref(false)
    const sortBy = ref([{ key: 'username', order: 'desc' }])

    const updateData = () => {
      store.loadUsers().then(() => {
        mainStore.itemCountTotal = users.value.total_count
        mainStore.itemCountFiltered = users.value.items?.length || 0
      })
    }

    const formUpdated = () => {
      showForm.value = false
      updateData()
    }

    const addItem = () => {
      user.value = {
        username: '',
        name: '',
        organization: undefined,
        roles: [],
        permissions: []
      }
      edit.value = false
      showForm.value = true
    }

    const editItem = (item) => {
      user.value = item
      edit.value = true
      showForm.value = true
    }

    const handleSubmit = (submittedData) => {
      if (showForm.value) {
        updateItem(submittedData)
      } else {
        createItem(submittedData)
      }
    }

    const deleteItem = (item) => {
      deleteUser(item)
        .then(() => {
          notifySuccess(`Successfully deleted ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to delete ${item.name}`)
        })
    }

    const createItem = (item) => {
      createUser(item)
        .then(() => {
          notifySuccess(`Successfully created ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to create ${item.name}`)
        })
    }

    const updateItem = (item) => {
      updateUser(item)
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

    async function importData(data) {
      try {
        await importUsers(data)
        updateData()
        notifySuccess(`Successfully imported ${data.get('file').name}`)
      } catch (error) {
        notifyFailure(`Failed to import ${data.get('file').name}`)
      }
    }

    async function exportData() {
      let queryString = ''
      if (selected.value.length > 0) {
        queryString = 'ids=' + selected.value.join('&ids=')
      }
      await exportUsers(queryString)
    }

    onMounted(() => {
      updateData()
    })

    return {
      showForm,
      sortBy,
      users,
      selected,
      user,
      edit,
      updateData,
      formUpdated,
      addItem,
      editItem,
      handleSubmit,
      deleteItem,
      createItem,
      updateItem,
      importData,
      exportData,
      selectionChange
    }
  }
}
</script>
