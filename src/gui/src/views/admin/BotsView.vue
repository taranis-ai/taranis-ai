<template>
  <v-container fluid class="pa-2">
    <v-row no-gutters>
      <v-col class="pa-2 mt-2">
        <h1>Bots Settings</h1>
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col class="pa-2">
        <DataTable
          v-model:items="bots.items"
          :add-button="true"
          :header-filter="['name', 'description', 'type', 'index', 'actions']"
          sort-by-item="index"
          @delete-item="deleteItem"
          @edit-item="editItem"
          @add-item="addItem"
          @selection-change="selectionChange"
          @update-items="updateData"
        >
          <template #actionColumn="{ item }">
            <v-tooltip left>
              <template #activator="{ props }">
                <v-icon
                  v-bind="props"
                  color="primary"
                  icon="mdi-run"
                  @click.stop="executeBot(item)"
                />
              </template>
              <span>Execute Bot</span>
            </v-tooltip>
          </template>
        </DataTable>
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
import DataTable from '@/components/common/DataTable.vue'
import EditConfig from '@/components/config/EditConfig.vue'
import { createBot, deleteBot, updateBot, executeBotTask } from '@/api/config'
import { ref, computed, onMounted } from 'vue'
import { notifySuccess, notifyFailure, baseFormat } from '@/utils/helpers'
import { useConfigStore } from '@/stores/ConfigStore'
import { useMainStore } from '@/stores/MainStore'
import { storeToRefs } from 'pinia'

export default {
  name: 'BotsView',
  components: {
    DataTable,
    EditConfig
  },
  setup() {
    const configStore = useConfigStore()
    const mainStore = useMainStore()
    const { bots, bot_types, parameters } = storeToRefs(configStore)
    const selected = ref([])
    const formData = ref({})
    const edit = ref(false)
    const bot_options = ref([])
    const showForm = ref(false)

    const formFormat = computed(() => {
      const additionalFormat = [
        {
          name: 'type',
          label: 'Type',
          type: 'select',
          items: bot_options.value
        },
        {
          name: 'index',
          label: 'Index',
          type: 'number'
        }
      ]
      return [...baseFormat, ...additionalFormat]
    })

    const updateData = () => {
      configStore.loadBots().then(() => {
        mainStore.itemCountTotal = bots.value.total_count
        mainStore.itemCountFiltered = bots.value.items.length
      })
      configStore.loadWorkerTypes().then(() => {
        bot_options.value = bot_types.value.map((bot) => {
          return {
            value: bot.type,
            title: bot.name
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

    const handleSubmit = (submittedData) => {
      if (edit.value) {
        updateItem(submittedData)
      } else {
        createItem(submittedData)
      }
      showForm.value = false
    }

    const editTitle = computed(() => {
      return edit.value ? `Edit Bot: '${formData.value['name']}'` : 'Add Bot'
    })

    const deleteItem = (item) => {
      deleteBot(item)
        .then(() => {
          notifySuccess(`Successfully deleted ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to delete ${item.name}`)
        })
    }

    const createItem = (item) => {
      createBot(item)
        .then(() => {
          notifySuccess(`Successfully created ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to create ${item.name}`)
        })
    }

    async function updateItem(item) {
      try {
        const result = await updateBot(item)
        notifySuccess(result.data.message)
        updateData()
      } catch (error) {
        notifyFailure(error)
      }
    }

    const selectionChange = (new_selection) => {
      selected.value = new_selection
    }

    const executeBot = (item) => {
      executeBotTask(item.id)
        .then(() => {
          notifySuccess(`Successfully executed ${item.id}`)
        })
        .catch(() => {
          notifyFailure(`Failed to execute ${item.id}`)
        })
    }

    onMounted(() => {
      updateData()
    })

    return {
      bots,
      selected,
      formData,
      editTitle,
      formFormat,
      showForm,
      parameters,
      addItem,
      editItem,
      handleSubmit,
      updateData,
      deleteItem,
      createItem,
      updateItem,
      selectionChange,
      executeBot
    }
  }
}
</script>
