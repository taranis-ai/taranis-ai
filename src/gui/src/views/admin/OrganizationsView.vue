<template>
  <v-container fluid>
    <DataTable
      v-model:items="organizations.items"
      :add-button="true"
      :header-filter="['id', 'name', 'description', 'actions']"
      sort-by-item="id"
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
import {
  deleteOrganization,
  createOrganization,
  updateOrganization
} from '@/api/config'
import { useConfigStore } from '@/stores/ConfigStore'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { ref, onMounted, computed } from 'vue'
import { storeToRefs } from 'pinia'

export default {
  name: 'OrganizationsView',
  components: {
    DataTable,
    EditConfig
  },
  setup() {
    const store = useConfigStore()
    const { organizations } = storeToRefs(store)
    const formData = ref({})
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
        name: 'street',
        label: 'Street',
        parent: 'address',
        type: 'text'
      },
      {
        name: 'city',
        label: 'City',
        parent: 'address',
        type: 'text'
      },
      {
        name: 'zip',
        label: 'Zip',
        parent: 'address',
        type: 'text'
      },
      {
        name: 'country',
        label: 'Country',
        parent: 'address',
        type: 'text'
      }
    ])

    const updateData = () => {
      showForm.value = false

      store.loadOrganizations()
    }

    const editTitle = computed(() => {
      return edit.value
        ? `Edit Organization: '${formData.value['name']}'`
        : 'Add Organization'
    })

    function addItem() {
      formData.value = {}
      edit.value = false
      showForm.value = true
    }

    function editItem(item) {
      formData.value = item
      edit.value = true
      showForm.value = true
    }

    function handleSubmit(submittedData) {
      if (edit.value) {
        updateItem(submittedData)
      } else {
        createItem(submittedData)
      }
    }

    function deleteItem(item) {
      deleteOrganization(item)
        .then(() => {
          notifySuccess(`Successfully deleted ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to delete ${item.name}`)
        })
    }

    function createItem(item) {
      createOrganization(item)
        .then(() => {
          notifySuccess(`Successfully created ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to create ${item.name}`)
        })
    }

    function updateItem(item) {
      updateOrganization(item)
        .then(() => {
          notifySuccess(`Successfully updated ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to update ${item.name}`)
        })
    }

    onMounted(() => {
      updateData()
    })

    return {
      organizations,
      formFormat,
      formData,
      editTitle,
      showForm,
      addItem,
      editItem,
      handleSubmit,
      updateData,
      deleteItem,
      createItem,
      updateItem
    }
  }
}
</script>
