<template>
  <div>
    <DataTable
      v-model:items="bots.items"
      :add-button="false"
      :header-filter="['name', 'description']"
      sort-by-item="name"
      :action-column="false"
      @edit-item="editItem"
      @update-items="updateData"
    />
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
import EditConfig from '@/components/config/EditConfig.vue'
import { updateBot } from '@/api/config'
import { ref, computed, onMounted } from 'vue'
import { useConfigStore } from '@/stores/ConfigStore'
import { useMainStore } from '@/stores/MainStore'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { storeToRefs } from 'pinia'

export default {
  name: 'BotsView',
  components: {
    DataTable,
    EditConfig
  },
  setup() {
    const mainStore = useMainStore()
    const configStore = useConfigStore()

    // data
    const { bots } = storeToRefs(configStore)
    const formData = ref({})
    const parameters = ref({})
    const bot_types = ref([])

    // computed
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
          name: 'type',
          label: 'Type',
          type: 'text',
          disabled: true
        }
      ]
      if (parameters.value[formData.value.type]) {
        return base.concat(parameters.value[formData.value.type])
      }
      return base
    })

    // methods
    const updateData = () => {
      configStore.loadBots().then(() => {
        mainStore.itemCountTotal = bots.value.total_count
        mainStore.itemCountFiltered = bots.value.items.length
        bots.value.items.forEach((item) => {
          parameters.value[item.type] = Object.keys(item[item.type]).map(
            (key) => {
              return {
                name: key,
                label: key,
                parent: item.type,
                type: 'text'
              }
            }
          )
        })
      })
    }

    const editItem = (item) => {
      formData.value = item
    }

    const handleSubmit = (submittedData) => {
      console.debug(submittedData)
      updateItem(submittedData)
    }

    const updateItem = (item) => {
      updateBot(item)
        .then(() => {
          notifySuccess(`Successfully updated ${item.id}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to update ${item.id}`)
        })
    }

    onMounted(() => {
      updateData()
    })

    return {
      // data
      bots,
      formData,
      parameters,
      bot_types,

      // computed
      formFormat,

      // methods
      updateData,
      editItem,
      handleSubmit,
      updateItem
    }
  }
}
</script>
