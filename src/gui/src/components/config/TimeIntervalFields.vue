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
              :rules="[rulesDict.cron]"
              :error-messages="error"
              :hint="
                !internalCronValue && !error
                  ? type === 'sources'
                    ? 'Value empty, OSINT sources have a default - 0 */8 * * *'
                    : 'Value empty, there is no default refresh interval'
                  : ''
              "
              :persistent-hint="!error && !internalCronValue"
              variant="outlined"
            />
          </v-col>
        </v-row>
        <v-divider class="mt-3"></v-divider>
        <v-card-subtitle class="text-h6 mt-3">
          Upcoming Refresh Times
        </v-card-subtitle>
        <v-row class="mt-2" style="min-height: 18vh">
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
                <v-list-item-title>{{
                  formatTimestamp(time)
                }}</v-list-item-title>
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
import { useI18n } from 'vue-i18n'
import { debounce } from 'lodash-es'

const { d } = useI18n()

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  type: {
    type: String,
    default: ''
  }
})
const emit = defineEmits(['update:modelValue', 'validation'])
const error = ref('')
const nextFireTimes = ref([])
const nextFireTimesLoading = ref(false)
const cronKey = ref(0) // Used to force re-rendering if needed

const rulesDict = {
  cron: (v) =>
    v === '' ||
    /^(\S+\s){4}\S$/.test(v) ||
    'Cron expression must be exactly five tokens separated by whitespace'
}

// This function transforms the day-of-week (example: "* * * * 0,2-3,5-6") field in the cron expression using a single regex replace.
// It applies the provided transformation function to every numeric token (or valid numeric range)
// in the last field, leaving tokens like "*" or those containing letters unchanged.
function transformDayOfWeek(cronExp, transformFn) {
  return cronExp.replace(/(^.+\s+)(\S+)$/, (match, prefix, dowField) => {
    if (dowField === '*' || /[a-zA-Z]/.test(dowField)) return match
    const transformed = dowField
      .split(',')
      .map((token) =>
        token
          .split('-')
          .map((t) => {
            const num = parseInt(t.trim(), 10)
            return isNaN(num) ? t : transformFn(num)
          })
          .join('-')
      )
      .join(',')
    return prefix + transformed
  })
}

// Forward transformation: Frontend (0=Sun,1=Mon, …,6=Sat)
// to Backend (0=Mon,1=Tue, …,6=Sun)
function shiftCronExpressionForward(cronExp) {
  return transformDayOfWeek(cronExp, (num) => ((num + 6) % 7).toString())
}

// Backward transformation: Backend -> Frontend
function shiftCronExpressionBackward(cronExp) {
  return transformDayOfWeek(cronExp, (num) => ((num + 1) % 7).toString())
}

// Debounced function that triggers the API call only after a short delay and only if there is no error.
const debouncedFetchNextFireTimes = debounce((cronValue) => {
  if (!error.value) {
    fetchNextFireTimes(cronValue)
  } else {
    nextFireTimes.value = []
  }
}, 300)

const internalCronValue = computed({
  get() {
    return shiftCronExpressionBackward(props.modelValue)
  },
  set(newVal) {
    if (!newVal) {
      error.value = ''
      cronKey.value++
      emit('update:modelValue', newVal)
      nextFireTimes.value = []
      return
    }

    const isValid = rulesDict.cron(newVal)
    if (isValid !== true) {
      error.value = isValid
      cronKey.value++
      emit('update:modelValue', newVal)
      nextFireTimes.value = []
      return
    } else {
      error.value = ''
    }

    // Convert the unshifted (frontend) input into the shifted version for the backend.
    const shiftedVal = shiftCronExpressionForward(newVal)
    emit('update:modelValue', shiftedVal)
    // Use debounced API call so that we wait for any error state to be set before firing the request.
    debouncedFetchNextFireTimes(shiftedVal)
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

function formatTimestamp(timestamp, formatKey = 'long') {
  return d(new Date(timestamp), formatKey)
}

onMounted(() => {
  fetchNextFireTimes(props.modelValue)
})
</script>
