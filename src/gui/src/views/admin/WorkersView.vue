<template>
  <v-container fluid class="pa-2">
    <v-row no-gutters>
      <v-col class="pa-2 mt-2">
        <h1>Workers Settings</h1>
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col class="pa-2">
        <v-card
          title="RabbitMQ"
          class="mx-auto pa-4 workers-config-card"
          width="100%"
          :subtitle="queue_status.url"
        >
          <v-card-text>
            <span v-if="queue_status.status" class="font-weight-bold">
              Status: {{ queue_status.status }}
            </span>
            <span v-else class="text-red-lighten-1">
              Error: {{ queue_status }}
            </span>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col class="pa-2">
        <DataTable
          :items="workers"
          :add-button="false"
          :header-filter="['name', 'status']"
        >
          <template #titlebar>
            <v-col cols="12" class="mt-3">
              <h3 class="text-primary">Workers</h3>
            </v-col>
          </template>
        </DataTable>
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col class="pa-2">
        <DataTable
          :items="queue_tasks"
          :add-button="false"
          :header-filter="['name', 'messages']"
        >
          <template #titlebar>
            <v-col cols="12" class="mt-3">
              <h3 class="text-primary">Tasks</h3>
            </v-col>
          </template>
        </DataTable>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import DataTable from '@/components/common/DataTable.vue'
import { useConfigStore } from '@/stores/ConfigStore'
import { notifyFailure } from '@/utils/helpers'
import { ref, onMounted } from 'vue'
import { storeToRefs } from 'pinia'

export default {
  name: 'WorkersView',
  components: {
    DataTable
  },
  setup() {
    const formData = ref({})
    const edit = ref(false)
    const selected = ref([])
    const configStore = useConfigStore()

    const { workers, queue_status, queue_tasks } = storeToRefs(configStore)

    async function updateData() {
      await Promise.all([
        configStore.loadOSINTSources(),
        configStore.loadQueueStatus(),
        configStore.loadWorkers(),
        configStore.loadQueueTasks()
      ])
    }

    const deleteItem = () => {
      notifyFailure('Not implemented yet')
    }

    const selectionChange = (new_selection) => {
      selected.value = new_selection
    }

    onMounted(() => {
      updateData()
    })

    return {
      formData,
      edit,
      selected,
      workers,
      queue_status,
      queue_tasks,
      updateData,
      deleteItem,
      selectionChange
    }
  }
}
</script>

<style lang="scss" scoped>
.workers-config-card {
  border: 2px solid white;
  transition: 180ms;
  box-shadow: 1px 2px 9px 0px rgba(0, 0, 0, 0.15);

  & a {
    color: rgb(var(--v-theme-primary));
  }
}
</style>
