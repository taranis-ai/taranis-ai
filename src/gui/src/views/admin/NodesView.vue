<template>
  <div>
    <DeprecationWarning />
    <DataTable
      v-model:items="nodes.items"
      :add-button="false"
      :header-filter="['tag', 'name', 'description']"
      :action-column="true"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
      @update-items="updateData"
      @selection-change="selectionChange"
    >
      <template #titlebar>
        <v-btn
          color="blue-grey"
          dark
          class="ml-4"
          prepend-icon="mdi-run"
          @click="triggerWorkers"
        >
          Trigger Workers
        </v-btn>
      </template>
    </DataTable>
    <EditConfig
      v-if="formData && Object.keys(formData).length > 0"
      :config-data="formData"
      :form-format="formFormat"
      @submit="handleSubmit"
    ></EditConfig>
  </div>
</template>

<script>
import DataTable from '@/components/common/DataTable.vue'
import DeprecationWarning from '@/components/common/DeprecationWarning.vue'
import EditConfig from '@/components/config/EditConfig.vue'
import { deleteNode, createNode, updateNode, triggerNode } from '@/api/config'
import { useConfigStore } from '@/stores/ConfigStore'
import { useMainStore } from '@/stores/MainStore'
import { notifySuccess, notifyFailure, objectFromFormat } from '@/utils/helpers'
import { ref, computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'

export default {
  name: 'NodesView',
  components: {
    DeprecationWarning,
    DataTable,
    EditConfig
  },
  setup() {
    const formData = ref({})
    const edit = ref(false)
    const selected = ref([])
    const workers = ref([])
    const mainStore = useMainStore()
    const configStore = useConfigStore()

    const { nodes, collectors } = storeToRefs(configStore)

    const formFormat = computed(() => {
      return [
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
          name: 'api_url',
          label: 'Node URL',
          type: 'text'
        },
        {
          name: 'api_key',
          label: 'API Key',
          type: 'text'
        },
        {
          name: formData.value.type,
          label: `${formData.value.type} Types`,
          type: 'table',
          disabled: true,
          headers: [
            { title: 'Name', key: 'name' },
            { title: 'Description', key: 'description' },
            { title: 'Type', key: 'type' }
          ],
          items: workers.value
        }
      ]
    })

    const updateData = () => {
      configStore.loadNodes().then(() => {
        mainStore.itemCountTotal = nodes.value.total_count
        mainStore.itemCountFiltered = nodes.value.items.length
      })
    }

    const addItem = () => {
      formData.value = objectFromFormat(formFormat.value)
      edit.value = false
    }

    const editItem = (item) => {
      if (item.type === 'bot') {
        workers.value = item.bots
      } else if (item.type === 'collector') {
        configStore.loadCollectors().then(() => {
          workers.value = collectors.items
        })
      } else {
        console.log('No workers found')
      }
      formData.value = item
      edit.value = true
    }

    const handleSubmit = (submittedData) => {
      if (edit.value) {
        updateItem(submittedData)
      } else {
        createItem(submittedData)
      }
    }

    const deleteItem = (item) => {
      deleteNode(item)
        .then(() => {
          notifySuccess(`Successfully deleted ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to delete ${item.name}`)
        })
    }

    const createItem = (item) => {
      createNode(item)
        .then(() => {
          notifySuccess(`Successfully created ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to create ${item.name}`)
        })
    }

    const updateItem = (item) => {
      updateNode(item)
        .then(() => {
          notifySuccess(`Successfully updated ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to update ${item.name}`)
        })
    }

    const selectionChange = (selectedItems) => {
      selected.value = selectedItems.map((item) => item.id)
    }

    const triggerWorkers = () => {
      triggerNode().then(() => {
        notifySuccess('Node run triggerd')
      })
    }

    onMounted(() => {
      updateData()
    })

    return {
      formData,
      edit,
      selected,
      workers,
      nodes,
      collectors,
      formFormat,
      updateData,
      addItem,
      editItem,
      handleSubmit,
      deleteItem,
      createItem,
      updateItem,
      selectionChange,
      triggerWorkers
    }
  }
}
</script>
