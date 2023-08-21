<template>
  <div>
    <DataTable
      v-model:items="bots.items"
      :add-button="true"
      :header-filter="['tag', 'name', 'description', 'type']"
      sort-by-item="id"
      :action-column="true"
      tag-icon="mdi-robot"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
      @selection-change="selectionChange"
      @update-items="updateData"
    >
      <template #actionColumn="bot">
        <v-tooltip left>
          <template #activator="{ props }">
            <v-icon
              v-bind="props"
              color="secondary"
              icon="mdi-run"
              @click.stop="executeBot(bot.item)"
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
      @submit="handleSubmit"
    ></EditConfig>
  </div>
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

    const updateItem = (item) => {
      updateBot(item)
        .then(() => {
          notifySuccess(`Successfully updated ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to update ${item.name}`)
        })
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
      edit,
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
