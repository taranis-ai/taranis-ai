<template>
  <div>
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
  </div>
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

    const { schedule, workers } = storeToRefs(configStore)

    const updateData = () => {
      configStore.loadWorkers()
      configStore.loadSchedule()
    }

    const deleteItem = (item) => {
      notifyFailure('Not implemented yet')
    }

    const selectionChange = (selectedItems) => {
      selected.value = selectedItems.map((item) => item.id)
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
      updateData,
      deleteItem,
      selectionChange
    }
  }
}
</script>
