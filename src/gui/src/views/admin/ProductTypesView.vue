<template>
  <v-container fluid>
    <DataTable
      v-model:items="product_types.items"
      :add-button="true"
      :header-filter="['id', 'title', 'description', 'actions']"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
      @update-items="updateData"
    />
    <EditConfig
      v-if="showForm"
      :form-format="formFormat"
      :config-data="formData"
      :title="editTitle"
      @submit="handleSubmit"
    />
  </v-container>
</template>

<script>
import DataTable from '@/components/common/DataTable.vue'
import EditConfig from '@/components/config/EditConfig.vue'
import {
  deleteProductType,
  createProductType,
  updateProductType
} from '@/api/config'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { useConfigStore } from '@/stores/ConfigStore'
import { useMainStore } from '@/stores/MainStore'
import { ref, computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'

export default {
  name: 'ProductTypesView',
  components: {
    DataTable,
    EditConfig
  },
  setup() {
    const configStore = useConfigStore()
    const mainStore = useMainStore()

    const formData = ref({})
    const edit = ref(false)
    const presenterList = ref([])
    const showForm = ref(false)

    const { product_types, presenter_types } = storeToRefs(configStore)

    const formFormat = computed(() => {
      return [
        {
          name: 'id',
          label: 'ID',
          type: 'text',
          disabled: true
        },
        {
          name: 'title',
          label: 'Title',
          type: 'text'
        },
        {
          name: 'description',
          label: 'Description',
          type: 'textarea'
        },
        {
          name: 'type',
          label: 'Type',
          type: 'select',
          items: presenterList.value
        },
        {
          name: 'TEMPLATE_PATH',
          parent: 'parameters',
          label: 'Template',
          type: 'select',
          items: product_types.value.templates
        }
      ]
    })

    const updateData = () => {
      configStore.loadProductTypes().then(() => {
        mainStore.itemCountTotal = product_types.value.total_count
        mainStore.itemCountFiltered = product_types.value.length
      })

      configStore.loadWorkerTypes().then(() => {
        presenterList.value = presenter_types.value.map((presenter) => {
          return {
            value: presenter.type,
            title: presenter.name
          }
        })
      })
    }

    const addItem = () => {
      formData.value = {}
      edit.value = false
      showForm.value = true
    }

    const editItem = (item) => {
      formData.value = item
      edit.value = true
      showForm.value = true
    }

    const editTitle = computed(() => {
      return edit.value
        ? `Edit Product Type: ${formData.value['title']}`
        : 'Add Product Type'
    })

    const handleSubmit = (submittedData) => {
      delete submittedData.tag
      console.debug('submittedData', submittedData)
      if (edit.value) {
        updateItem(submittedData)
      } else {
        createItem(submittedData)
      }
      showForm.value = false
    }

    const createItem = (item) => {
      createProductType(item)
        .then(() => {
          notifySuccess(`Successfully created ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to create ${item.name}`)
        })
    }

    const deleteItem = (item) => {
      if (!item.default) {
        deleteProductType(item)
          .then(() => {
            notifySuccess(`Successfully deleted ${item.name}`)
            updateData()
          })
          .catch(() => {
            notifyFailure(`Failed to delete ${item.name}`)
          })
      }
    }

    const updateItem = (item) => {
      updateProductType(item)
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
      product_types,
      formData,
      formFormat,
      editTitle,
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
