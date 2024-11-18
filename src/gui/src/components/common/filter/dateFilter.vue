<template>
  <div>
    <v-date-input
      v-model="selectedDate"
      variant="outlined"
      density="compact"
      first-day-of-week="1"
      :placeholder="dateLabel"
      :name="'dateFilter-' + dateLabel"
      :min="timefrom"
      :max="timeto"
      clearable
      hide-details
      @update:modelValue="onDateChange"
      @click:clear="clearDate"
    />
    <v-tooltip activator="parent" :text="tooltipTextDate" />
  </div>

  <div class="pt-1">
    <v-menu
      v-model="timeMenu"
      :close-on-content-click="false"
      transition="scale-transition"
      offset-y
    >
      <template #activator="{ props }">
        <v-text-field
          v-model="timeInput"
          density="compact"
          :disabled="!selectedDate"
          :placeholder="timeLabel"
          prepend-icon="mdi-clock-time-four-outline"
          variant="outlined"
          v-bind="props"
          readonly
          clearable
          hide-details
          @click:clear="clearTime"
        />
      </template>
      <v-time-picker
        v-if="timeMenu && selectedDate"
        v-model:hour="selectedHour"
        v-model:minute="selectedMinute"
        @click:close="timeMenu = false"
        @update:hour="onTimeChange"
        @update:minute="onTimeChange"
        format="24hr"
      />
    </v-menu>
    <v-tooltip activator="parent" :text="tooltipTextTime" />
  </div>
</template>

<script>
import { ref, watch } from 'vue'

export default {
  name: 'DateFilter',
  props: {
    modelValue: String,
    dateLabel: { type: String, default: 'Enter date' },
    timeLabel: { type: String, default: 'Enter time' },
    timeto: String,
    timefrom: String,
    tooltipTextDate: { type: String, default: 'Date' },
    tooltipTextTime: { type: String, default: 'Time' }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const selectedDate = ref(null)
    const selectedHour = ref(null)
    const selectedMinute = ref(null)
    const timeInput = ref('')
    const timeMenu = ref(false)

    const parseModelValue = () => {
      if (props.modelValue) {
        const initialDate = new Date(props.modelValue)
        if (!isNaN(initialDate)) {
          selectedDate.value = new Date(initialDate.toDateString())
          selectedHour.value = initialDate.getHours()
          selectedMinute.value = initialDate.getMinutes()
          timeInput.value = `${String(initialDate.getHours()).padStart(2, '0')}:${String(initialDate.getMinutes()).padStart(2, '0')}`
        }
      } else {
        selectedDate.value = null
        selectedHour.value = null
        selectedMinute.value = null
        timeInput.value = ''
      }
    }

    parseModelValue()

    watch(
      () => props.modelValue,
      () => {
        parseModelValue()
      }
    )

    const onDateChange = (newDate) => {
      selectedDate.value = newDate
      updateModelValue()
    }

    const onTimeChange = () => {
      updateTimeInput()
      updateModelValue()
    }

    const updateModelValue = () => {
      if (selectedDate.value) {
        const datetime = new Date(selectedDate.value)
        datetime.setHours(selectedHour.value || 0)
        datetime.setMinutes(selectedMinute.value || 0)
        emit('update:modelValue', datetime.toISOString())
      } else {
        emit('update:modelValue', null)
      }
    }

    const updateTimeInput = () => {
      if (selectedHour.value !== null && selectedMinute.value !== null) {
        timeInput.value = `${String(selectedHour.value).padStart(2, '0')}:${String(selectedMinute.value).padStart(2, '0')}`
      } else {
        timeInput.value = ''
      }
    }

    const clearDate = () => {
      selectedDate.value = null
      updateModelValue()
    }

    const clearTime = () => {
      selectedHour.value = null
      selectedMinute.value = null
      timeInput.value = ''
      updateModelValue()
    }

    return {
      timeMenu,
      selectedDate,
      selectedHour,
      selectedMinute,
      timeInput,
      onDateChange,
      onTimeChange,
      clearDate,
      clearTime
    }
  }
}
</script>
