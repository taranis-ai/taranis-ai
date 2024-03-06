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
    >
      <template #additionalData>
        <code-editor
          v-if="showForm"
          v-model:content="templateData"
          class="mb-3"
          header="Template Content"
        />
      </template>
    </EditConfig>
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
import CodeEditor from '@/components/common/CodeEditor.vue'

export default {
  name: 'ProductTypesView',
  components: {
    DataTable,
    EditConfig,
    CodeEditor
  },
  setup() {
    const configStore = useConfigStore()
    const mainStore = useMainStore()

    const formData = ref({})
    const edit = ref(false)
    const presenterList = ref([])
    const showForm = ref(false)

    const templateData = ref('')

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
          name: 'TEMPLATE_PATH',
          parent: 'parameters',
          label: 'Template',
          type: 'select',
          items: product_types.value.templates
        },
        {
          name: 'report_types',
          label: 'Report Types',
          type: 'table',
          headers: [{ title: 'Name', key: 'title' }],
          items: report_item_types.value.items
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
        templateData.value =
          response.data.template !== '' ? atob(response.data.template) : ''
        edit.value = true
        showForm.value = true
      })
    }

    function handleSubmit(submittedData) {
      submittedData.template = btoa(templateData.value)
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
      templateData,
      addItem,
      editItem,
      handleSubmit,
      deleteItem,
      updateData
    }
  }
}
</script>
