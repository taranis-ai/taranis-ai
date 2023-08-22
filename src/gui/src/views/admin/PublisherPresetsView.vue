<template>
  <div>
    <DataTable
      :items="publisher_presets.items"
      :add-button="true"
      :header-filter="['tag', 'id', 'name', 'description']"
      sort-by-item="id"
      :action-column="true"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
      @update-items="updateData"
    />
    <EditConfig
      v-if="showForm"
      :config-data="formData"
      :form-format="formFormat"
      :parameters="parameters"
      :title="editTitle"
      @submit="handleSubmit"
    ></EditConfig>
  </div>
</template>

<script>
import { defineComponent, ref, computed, onMounted } from 'vue'
import DataTable from '@/components/common/DataTable.vue'
import EditConfig from '@/components/config/EditConfig.vue'
import {
  deletePublisherPreset,
  createPublisherPreset,
  updatePublisherPreset
} from '@/api/config'
import { notifySuccess, notifyFailure, baseFormat } from '@/utils/helpers'
import { useConfigStore } from '@/stores/ConfigStore'
import { useMainStore } from '@/stores/MainStore'
import { storeToRefs } from 'pinia'

export default defineComponent({
  name: 'PublisherPresetsView',
  components: {
    DataTable,
    EditConfig
  },
  setup() {
    const configStore = useConfigStore()
    const mainStore = useMainStore()

    const { publisher_presets, publisher_types, parameters } =
      storeToRefs(configStore)

    const publishersList = ref([])
    const formData = ref({})
    const edit = ref(false)
    const showForm = ref(false)

    const formFormat = computed(() => {
      const additionalFormat = [
        {
          name: 'type',
          label: 'Type',
          type: 'select',
          items: publishersList.value
        }
      ]
      return [...baseFormat, ...additionalFormat]
    })

    const updateData = () => {
      configStore.loadPublisherPresets().then(() => {
        mainStore.itemCountTotal = publisher_presets.value.total_count
        mainStore.itemCountFiltered = publisher_presets.value.items.length
      })
      configStore.loadWorkerTypes().then(() => {
        publishersList.value = publisher_types.value.map((publisher) => {
          return {
            value: publisher.type,
            title: publisher.name
          }
        })
      })
      configStore.loadParameters()
    }

    const addItem = () => {
      formData.value = {}
      edit.value = false
      showForm.value = true
    }

    const editItem = (item) => {
      formData.value = item
      edit.value = false
      showForm.value = true
    }

    const editTitle = computed(() => {
      return edit.value
        ? `Edit Publisher Preset: '${formData.value['name']}'`
        : 'Add Publisher Preset'
    })

    const handleSubmit = (submittedData) => {
      delete submittedData.tag
      if (edit.value) {
        updateItem(submittedData)
      } else {
        createItem(submittedData)
      }
      showForm.value = false
    }

    const deleteItem = (item) => {
      if (!item.default) {
        deletePublisherPreset(item)
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
      createPublisherPreset(item)
        .then(() => {
          notifySuccess(`Successfully created ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to create ${item.name}`)
        })
    }

    const updateItem = (item) => {
      updatePublisherPreset(item)
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
      publisher_presets,
      publishersList,
      formData,
      parameters,
      editTitle,
      formFormat,
      showForm,
      addItem,
      editItem,
      handleSubmit,
      deleteItem,
      createItem,
      updateItem,
      updateData
    }
  }
})
</script>
