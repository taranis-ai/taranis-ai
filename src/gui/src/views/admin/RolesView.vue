<template>
  <v-container fluid class="pa-2">
    <v-row no-gutters>
      <v-col class="pa-2 mt-2">
        <h1>Roles Settings</h1>
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col class="pa-2">
        <DataTable
          :items="roles.items"
          :add-button="true"
          :header-filter="[
            'id',
            'name',
            'description',
            'permissions.length',
            'actions'
          ]"
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
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import DataTable from '@/components/common/DataTable.vue'
import EditConfig from '@/components/config/EditConfig.vue'
import { deleteRole, createRole, updateRole } from '@/api/config'
import { ref, onBeforeMount, computed } from 'vue'
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
        rules: ['required']
      },
      {
        name: 'description',
        label: 'Description',
        type: 'textarea'
      },
      {
        name: 'tlp_level',
        label: 'TLP Level',
        type: 'select',
        items: [
          { title: 'Clear', value: 'clear' },
          { title: 'Green', value: 'green' },
          { title: 'Amber', value: 'amber' },
          { title: 'Amber+Strict', value: 'amber+strict' },
          { title: 'Red', value: 'red' }
        ]
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

    function updateData() {
      showForm.value = false

      store.loadRoles().then(() => {
        mainStore.itemCountTotal = roles.value.total_count
        mainStore.itemCountFiltered = roles.value.items.length
      })
      store.loadPermissions().then()
    }

    function addItem() {
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
      deleteRole(item)
        .then((result) => {
          notifySuccess(result.data.message)
          updateData()
        })
        .catch((error) => {
          notifyFailure(error)
        })
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

    onBeforeMount(() => {
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
