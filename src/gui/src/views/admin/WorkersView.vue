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
          {{ queue_status.status }}
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
        :items="schedule"
        :add-button="false"
        :header-filter="[
          'task',
          'schedule',
          'args',
          'last_run_at',
          'next_run_time',
          'total_run_count'
        ]"
        :action-column="true"
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

    const { schedule, workers, queue_status } = storeToRefs(configStore)

    const updateData = () => {
      Promise.all([
        configStore.loadSchedule(),
        configStore.loadWorkers(),
        configStore.loadQueueStatus()
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
      schedule,
      workers,
      queue_status,
      updateData,
      deleteItem,
      selectionChange
    }
  }
}
</script>
