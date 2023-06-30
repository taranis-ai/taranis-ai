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
      v-if="formData && Object.keys(formData).length > 0"
      :form-format="formFormat"
      :config-data="formData"
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
import { notifySuccess, objectFromFormat, notifyFailure } from '@/utils/helpers'
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
    const store = useConfigStore()
    const mainStore = useMainStore()

    const { publisher_presets, publishers } = storeToRefs(store)

    const publishersList = ref([])
    const formData = ref({})
    const parameters = ref({})
    const edit = ref(false)

    const formFormat = computed(() => {
      const base = [
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
          rules: [(v) => !!v || 'Required']
        },
        {
          name: 'description',
          label: 'Description',
          type: 'textarea',
          rules: [(v) => !!v || 'Required']
        },
        {
          name: 'publisher_id',
          label: 'Type',
          type: 'select',
          rules: [(v) => !!v || 'Required'],
          options: publishersList.value,
          disabled: edit.value
        }
      ]
      if (parameters.value[formData.value.publisher_id]) {
        return base.concat(parameters.value[formData.value.publisher_id])
      }
      return base
    })

    const updateData = () => {
      store.loadPublisherPresets().then(() => {
        mainStore.itemCountTotal = publisher_presets.value.total_count
        mainStore.itemCountFiltered = publisher_presets.value.items.length
      })
      store.loadPublishers().then(() => {
        publishersList.value = publishers.value.items.map((item) => {
          return {
            title: item.name,
            value: item.id
          }
        })
        publishers.value.items.forEach((publisher) => {
          parameters.value[publisher.id] = publisher.parameters.map(
            (parameter) => {
              return {
                name: parameter.key,
                label: parameter.name,
                parent: 'parameter_values',
                type: 'text'
              }
            }
          )
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
      publishers,
      formData,
      parameters,
      edit,
      formFormat,
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
