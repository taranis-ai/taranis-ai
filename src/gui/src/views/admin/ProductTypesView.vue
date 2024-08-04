<template>
  <v-container fluid class="pa-2">
    <v-row no-gutters>
      <v-col class="pa-2 mt-2">
        <h1>Product Types Settings</h1>
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col class="pa-2">
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
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import DataTable from '@/components/common/DataTable.vue'
import EditConfig from '@/components/config/EditConfig.vue'
import {
  deleteProductType,
  createProductType,
  updateProductType,
  getProductType
} from '@/api/config'
import {
  notifySuccess,
  notifyFailure,
  getMessageFromError
} from '@/utils/helpers'
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

    const { product_types, presenter_types, report_item_types } =
      storeToRefs(configStore)

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
          type: 'text',
          rules: ['required']
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
          items: presenterList.value,
          rules: ['required']
        },
        {
          name: 'report_types',
          label: 'Report Types',
          type: 'table',
          headers: [{ title: 'Name', key: 'title' }],
          items: report_item_types.value.items
        },
        {
          name: 'TEMPLATE_PATH',
          parent: 'parameters',
          label: 'Template',
          type: 'select',
          rules: ['required'],
          items: product_types.value.templates
        }
      ]
    })

    const editTitle = computed(() => {
      return edit.value
        ? `Edit Product Type: ${formData.value['title']}`
        : 'Add Product Type'
    })

    function updateData() {
      configStore.loadProductTypes().then(() => {
        mainStore.itemCountTotal = product_types.value.total_count
        mainStore.itemCountFiltered = product_types.value.length
      })

      configStore.loadReportTypes().then(() => {
        console.debug('report_item_types', report_item_types.value.items)
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

    function addItem() {
      formData.value = {}
      edit.value = false
      showForm.value = true
    }

    function editItem(item) {
      formData.value = item
      getProductType(item.id).then((response) => {
        formData.value['report_types'] = response.data.report_types
        edit.value = true
        showForm.value = true
      })
    }

    function handleSubmit(submittedData) {
      console.debug('submittedData', submittedData)
      if (edit.value) {
        updateItem(submittedData)
      } else {
        createItem(submittedData)
      }
      showForm.value = false
    }

    function createItem(item) {
      createProductType(item)
        .then(() => {
          notifySuccess(`Successfully created ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to create ${item.name}`)
        })
    }

    function deleteItem(item) {
      showForm.value = false
      deleteProductType(item)
        .then((response) => {
          notifySuccess(response.data.message)
          updateData()
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
        })
    }

    function updateItem(item) {
      updateProductType(item)
        .then((response) => {
          notifySuccess(response.data.message)
          updateData()
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
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
