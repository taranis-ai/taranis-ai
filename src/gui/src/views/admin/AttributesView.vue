<template>
  <v-container fluid class="pa-2">
    <v-row no-gutters>
      <v-col class="pa-2 mt-2">
        <h1>Attributes Settings</h1>
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col class="pa-2">
        <DataTable
          v-model:items="attributes.items"
          :add-button="true"
          :header-filter="[
            'tag',
            'id',
            'name',
            'description',
            'type',
            'actions'
          ]"
          sort-by-item="id"
          @delete-item="deleteItem"
          @edit-item="editItem"
          @add-item="addItem"
          @update-items="updateData"
        />
        <AttributeForm
          v-if="showForm"
          :attribute-prop="formData"
          :edit="edit"
          @submit="handleSubmit"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { ref, onMounted } from 'vue'
import DataTable from '@/components/common/DataTable.vue'
import AttributeForm from '@/components/config/AttributeForm.vue'
import { deleteAttribute, createAttribute, updateAttribute } from '@/api/config'
import { useConfigStore } from '@/stores/ConfigStore'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { useMainStore } from '@/stores/MainStore'
import { storeToRefs } from 'pinia'

export default {
  name: 'AttributesView',
  components: {
    DataTable,
    AttributeForm
  },
  setup() {
    const formData = ref({})
    const edit = ref(false)
    const showForm = ref(false)

    const configStore = useConfigStore()
    const mainStore = useMainStore()

    const { attributes } = storeToRefs(configStore)

    const updateData = async () => {
      configStore.loadAttributes().then(() => {
        mainStore.itemCountTotal = attributes.value.total_count
        mainStore.itemCountFiltered = attributes.value.items.length
      })
    }

    const addItem = () => {
      formData.value = {
        attribute_enums: [],
        default_value: '',
        description: '',
        name: '',
        type: ''
      }

      edit.value = false
      showForm.value = true
    }

    const editItem = (item) => {
      formData.value = item
      edit.value = true
      showForm.value = true
    }

    const handleSubmit = (submittedData) => {
      const nonemptyEntries = Object.entries(submittedData).filter(
        ([, value]) => value !== ''
      )
      const nonemptyValues = Object.fromEntries(nonemptyEntries)
      if (edit.value) {
        updateItem(nonemptyValues)
      } else {
        createItem(nonemptyValues)
      }
      showForm.value = false
    }

    function deleteItem(item) {
      if (!item.default) {
        deleteAttribute(item)
          .then(() => {
            notifySuccess(`Successfully deleted ${item.name}`)
            updateData()
          })
          .catch(() => {
            notifyFailure(`Failed to delete ${item.name}`)
          })
      }
    }

    function createItem(item) {
      createAttribute(item)
        .then(() => {
          notifySuccess(`Successfully created ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to create ${item.name}`)
        })
    }

    function updateItem(item) {
      updateAttribute(item)
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
      edit,
      formData,
      attributes,
      showForm,
      addItem,
      editItem,
      handleSubmit,
      deleteItem,
      updateData
    }
  }
}
</script>
