<template>
  <v-container fluid class="pa-0 ma-0">
    <v-card class="pa-4 mb-4">
      <v-card-title class="text-h6">Refresh Interval</v-card-title>
      <v-divider></v-divider>
      <v-card-text>
        <v-row class="mt-3">
          <v-col cols="12">
            <CronVuetify
              :key="cronKey"
              v-model="cronVuetifyValue"
              @error="handleError"
            />
          </v-col>
        </v-row>
        <v-row class="mt-3">
          <v-col cols="3">
            <v-text-field
              class="pt-3"
              style="width: 100%"
              v-model="internalCronValue"
              label="Cron Expression"
              :error-messages="error"
              variant="outlined"
            />
          </v-col>
        </v-row>
        <v-divider class="mt-3"></v-divider>
        <v-card-subtitle class="text-h6 mt-3">
          Upcoming Refresh Times
        </v-card-subtitle>
        <v-row class="mt-2">
          <v-col cols="12">
            <v-progress-circular
              v-if="nextFireTimesLoading"
              indeterminate
              color="primary"
              size="24"
              class="mr-2"
            />
            <v-list v-else>
              <v-list-item v-for="(time, index) in nextFireTimes" :key="index">
                <v-list-item-title>{{ time }}</v-list-item-title>
              </v-list-item>
              <v-list-item v-if="!nextFireTimes.length">
                <v-list-item-title class="text-error">
                  No upcoming refresh times. Please adjust your cron expression.
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import { CronVuetify } from '@vue-js-cron/vuetify'
import { ref, onMounted, computed } from 'vue'
import { getNextFireOn } from '@/api/config'

const props = defineProps({
  modelValue: {
    type: String,
    default: '0 */8 * * *'
  }
})

const emit = defineEmits(['update:modelValue', 'validation'])
const error = ref('')
const nextFireTimes = ref([])
const nextFireTimesLoading = ref(false)
const internalCronValue = computed({
  get() {
    return props.modelValue
  },
  set(newVal) {
    fetchNextFireTimes(newVal)
    emit('update:modelValue', newVal)
  }
})

const cronVuetifyValue = computed({
  get() {
    return internalCronValue.value
  },
  set(newVal) {
    internalCronValue.value = newVal
  }
})

async function fetchNextFireTimes(cronValue) {
  if (!cronValue) {
    nextFireTimes.value = []
    return
  }

  try {
    nextFireTimesLoading.value = true
    const response = await getNextFireOn(cronValue)
    nextFireTimes.value = response.data
  } catch (err) {
    nextFireTimes.value = []
  } finally {
    nextFireTimesLoading.value = false
  }
}

function handleError(errorMsg) {
  error.value = errorMsg
}

onMounted(() => {
  fetchNextFireTimes(props.modelValue)
})
</script>
