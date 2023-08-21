<template>
  <div>
    <DataTable
      v-model:items="product_types.items"
      :add-button="true"
      :header-filter="['tag', 'id', 'title', 'description']"
      sort-by-item="id"
      :action-column="true"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
      @update-items="updateData"
    />
    <EditConfig
      v-if="formData && Object.keys(formData).length > 0"
      :form-format="formFormat"
      :config-data="formData"
      @submit="handleSubmit"
    ></EditConfig>
  </div>
</template>

<script>
import DataTable from '@/components/common/DataTable.vue'
import EditConfig from '@/components/config/EditConfig.vue'
import {
  deleteProductType,
  createProductType,
  updateProductType
} from '@/api/config'
import { notifySuccess, notifyFailure, objectFromFormat } from '@/utils/helpers'
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
    const parameters = ref({})
    const presenterList = ref([])

    const { product_types, presenter_types } = storeToRefs(configStore)

    const formFormat = computed(() => {
      const base = [
        {
          name: 'id',
          label: 'ID',
          type: 'number',
          disabled: true
        },
        {
          name: 'title',
          label: 'Title',
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
          name: 'presenter_id',
          label: 'Presenter',
          type: 'list',
          rules: [(v) => !!v || 'Required'],
          items: presenterList.value,
          disabled: edit.value
        }
      ]
      if (parameters.value[formData.value.presenter_id]) {
        return base.concat(parameters.value[formData.value.presenter_id])
      }
      return base
    })

    const updateData = () => {
      configStore.loadProductTypes().then(() => {
        mainStore.itemCountTotal = product_types.value.total_count
        mainStore.itemCountFiltered = product_types.value.length
      })

      configStore.loadWorkerTypes().then(() => {
        presenterList.value = presenter_types.value.map((presenter) => {
          parameters.value[presenter.type] = Object.keys(
            presenter.parameters
          ).map((key) => ({
            name: key,
            label: key,
            parent: 'parameter_values',
            type: 'text'
          }))

          return {
            value: presenter.type,
            title: presenter.name
          }
        })
      })
    }

    const addItem = () => {
      formData.value = objectFromFormat(formFormat.value)
      formData.value.parameter_values = {}
      edit.value = false
    }

    const editItem = (item) => {
      formData.value = item
      edit.value = true
    }

    const handleSubmit = (submittedData) => {
      delete submittedData.tag
      console.debug('submittedData', submittedData)
      if (edit.value) {
        updateItem(submittedData)
      } else {
        createItem(submittedData)
      }
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
      edit,
      addItem,
      editItem,
      handleSubmit,
      deleteItem,
      updateData
    }
  }
}
</script>
