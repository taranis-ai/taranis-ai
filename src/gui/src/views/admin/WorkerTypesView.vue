<template>
  <div>
    <DataTable
      v-model:items="worker_types.items"
      :add-button="false"
      :header-filter="['name', 'description', 'category', 'type']"
      sort-by-item="category"
      :action-column="true"
      @edit-item="editItem"
      @update-items="updateData"
    >
    </DataTable>
    <EditConfig
      v-if="showForm"
      :config-data="formData"
      :form-format="formFormat"
      :parameters="disabledParameters"
      @submit="handleSubmit"
    ></EditConfig>
  </div>
</template>

<script>
import DataTable from '@/components/common/DataTable.vue'
import EditConfig from '@/components/config/EditConfig.vue'
import { ref, computed, onMounted } from 'vue'
import { useConfigStore } from '@/stores/ConfigStore'
import { useMainStore } from '@/stores/MainStore'
import { notifyFailure, baseFormat } from '@/utils/helpers'
import { storeToRefs } from 'pinia'

export default {
  name: 'WorkerTypesView',
  components: {
    DataTable,
    EditConfig
  },
  setup() {
    const mainStore = useMainStore()
    const configStore = useConfigStore()

    // data
    const { worker_types, parameters } = storeToRefs(configStore)
    const formData = ref({})
    const showForm = ref(false)

    // computed
    const formFormat = computed(() => {
      const additionalFormat = [
        {
          name: 'type',
          label: 'Type',
          type: 'text',
          disabled: true
        }
      ]
      return [...baseFormat, ...additionalFormat]
    })

    const disabledParameters = computed(() => {
      const result = {}
      for (const key in parameters.value) {
        result[key] = parameters.value[key].map((param) => {
          return {
            ...param,
            disabled: true
          }
        })
      }
      return result
    })

    // methods
    const updateData = () => {
      configStore.loadWorkerTypes().then(() => {
        mainStore.itemCountTotal = worker_types.value.total_count
        mainStore.itemCountFiltered = worker_types.value.items.length
      })
      configStore.loadParameters()
    }

    const editItem = (item) => {
      formData.value = item
      showForm.value = true
    }

    const handleSubmit = () => {
      notifyFailure('Worker Types cannot be edited')
    }

    onMounted(() => {
      updateData()
    })

    return {
      // data
      worker_types,
      formData,
      showForm,

      // computed
      formFormat,
      disabledParameters,

      // methods
      updateData,
      editItem,
      handleSubmit
    }
  }
}
</script>
