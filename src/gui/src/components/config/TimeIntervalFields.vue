<template>
  <v-container fluid class="pa-0 ma-0">
    <v-row>
      <v-col cols="12">
        <v-switch
          v-model="isEnabled"
          label="Define a custom REFRESH_INTERVAL"
          @update:model-value="handleSwitchChange"
        />
      </v-col>
    </v-row>
    <v-card class="pa-4 mb-4">
      <v-card-title class="text-h6">Refresh Interval</v-card-title>
      <v-divider></v-divider>
      <v-card-text>
        <v-row class="mt-3">
          <v-col cols="12">
            <CronVuetify
              :key="cronKey"
              v-model="internalCronValue"
              @error="handleError"
              :disabled="!isEnabled"
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
              :disabled="!isEnabled"
            />
          </v-col>
        </v-row>
        <v-divider class="mt-3"></v-divider>
        <div :style="{ opacity: isEnabled ? 1 : 0.5 }">
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
              ></v-progress-circular>
              <v-list v-else>
                <v-list-item
                  v-for="(time, index) in nextFireTimes"
                  :key="index"
                >
                  <v-list-item-title>{{ time }}</v-list-item-title>
                </v-list-item>
                <v-list-item v-if="!nextFireTimes.length">
                  <v-list-item-title class="text-error">
                    No upcoming refresh times. Please adjust your cron
                    expression.
                  </v-list-item-title>
                </v-list-item>
              </v-list>
            </v-col>
          </v-row>
        </div>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import { CronVuetify } from '@vue-js-cron/vuetify'
import { ref, watch } from 'vue'
import { getNextFireOn } from '@/api/config'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'validation'])
const error = ref('')
const nextFireTimes = ref([])
const nextFireTimesLoading = ref(false)
const isEnabled = ref(props.modelValue !== '')
const cronKey = ref(0)
const internalCronValue = ref(props.modelValue)

watch([isEnabled, nextFireTimes, error], () => {
  const isValid =
    !isEnabled.value || (nextFireTimes.value.length > 0 && !error.value)
  emit('validation', isValid)
})

watch(internalCronValue, (newVal, oldVal) => {
  if (newVal !== oldVal) {
    emit('update:modelValue', newVal)
    fetchNextFireTimes(newVal)
  }
})

async function fetchNextFireTimes(cronValue) {
  if (!cronValue || !isEnabled.value) {
    nextFireTimes.value = []
    return
  }

  nextFireTimesLoading.value = true

  try {
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

function handleSwitchChange(newVal) {
  isEnabled.value = newVal
  if (newVal) {
    const defaultValue = '0 */8 * * *'
    internalCronValue.value = defaultValue
    emit('update:modelValue', defaultValue)
  } else {
    internalCronValue.value = ''
    emit('update:modelValue', '')
    error.value = ''
    nextFireTimes.value = []
    cronKey.value++
  }
}
</script>
