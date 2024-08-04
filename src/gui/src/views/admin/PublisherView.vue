<template>
  <v-container fluid class="pa-2">
    <v-row no-gutters>
      <v-col class="pa-2 mt-2">
        <h1>Publisher Settings</h1>
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col class="pa-2">
        <DataTable
          :items="publisher.items"
          :add-button="true"
          :header-filter="['name', 'description', 'type', 'actions']"
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
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { defineComponent, ref, computed, onMounted } from 'vue'
import DataTable from '@/components/common/DataTable.vue'
import EditConfig from '@/components/config/EditConfig.vue'
import { deletePublisher, createPublisher, updatePublisher } from '@/api/config'
import { notifySuccess, notifyFailure, baseFormat } from '@/utils/helpers'
import { useConfigStore } from '@/stores/ConfigStore'
import { useMainStore } from '@/stores/MainStore'
import { storeToRefs } from 'pinia'

export default defineComponent({
  name: 'PublisherView',
  components: {
    DataTable,
    EditConfig
  },
  setup() {
    const configStore = useConfigStore()
    const mainStore = useMainStore()

    const { publisher, publisher_types, parameters } = storeToRefs(configStore)

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
          items: publishersList.value,
          disabled: edit.value,
          rules: ['required']
        }
      ]
      return [...baseFormat, ...additionalFormat]
    })

    const updateData = () => {
      configStore.loadPublisher().then(() => {
        mainStore.itemCountTotal = publisher.value.total_count
        mainStore.itemCountFiltered = publisher.value.items.length
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
      edit.value = true
      showForm.value = true
    }

    const editTitle = computed(() => {
      return edit.value
        ? `Edit Publisher: '${formData.value['name']}'`
        : 'Add Publisher'
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
        deletePublisher(item)
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
      createPublisher(item)
        .then(() => {
          notifySuccess(`Successfully created ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to create ${item.name}`)
        })
    }

    const updateItem = (item) => {
      updatePublisher(item)
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
      publisher,
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
