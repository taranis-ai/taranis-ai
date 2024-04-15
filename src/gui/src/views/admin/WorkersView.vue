<template>
  <v-container fluid>
    <v-row>
      <v-card
        title="RabbitMQ"
        class="mt-2 mb-2"
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
    </v-row>
    <v-row>
      <DataTable
        :items="workers"
        :add-button="false"
        :header-filter="['name', 'status']"
      >
        <template #titlebar>
          <v-col cols="12" class="mt-3">
            <h1>Workers</h1>
          </v-col>
        </template>
      </DataTable>
    </v-row>
    <v-row class="mt-5">
      <DataTable
        :items="queue_tasks"
        :add-button="false"
        :header-filter="['name', 'messages']"
      >
        <template #titlebar>
          <v-col cols="12" class="mt-3">
            <h1>Tasks</h1>
          </v-col>
        </template>
      </DataTable>
    </v-row>
    <v-row class="mt-5">
      <DataTable
        :items="enhanced_schedule"
        :add-button="false"
        :header-filter="[
          'task',
          'schedule',
          'args',
          'last_run_at',
          'total_run_count',
          'actions'
        ]"
        @delete-item="deleteItem"
        @selection-change="selectionChange"
      >
        <template #titlebar>
          <v-col cols="12" class="mt-3">
            <h1>Schedule</h1>
          </v-col>
        </template>
      </DataTable>
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

    const { enhanced_schedule, workers, queue_status, queue_tasks } =
      storeToRefs(configStore)

    const updateData = () => {
      Promise.all([
        configStore.loadOSINTSources(),
        configStore.loadQueueStatus(),
        configStore.loadSchedule(),
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
      enhanced_schedule,
      updateData,
      deleteItem,
      selectionChange
    }
  }
}
</script>
