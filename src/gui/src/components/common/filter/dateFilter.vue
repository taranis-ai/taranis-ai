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
      @click:clear="clearDate"
    />
    <v-tooltip activator="parent" :text="tooltipTextDate" />
  </div>

  <div class="pt-1">
    <v-menu
      v-model="time_menu"
      :close-on-content-click="false"
      transition="scale-transition"
      offset-y
    >
      <template #activator="{ props }">
        <v-text-field
          v-model="formattedTime"
          density="compact"
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
        v-show="time_menu"
        v-model:hour="selectedHour"
        v-model:minute="selectedMinute"
        @click:close="time_menu = false"
        format="24hr"
      />
    </v-menu>
    <v-tooltip activator="parent" :text="tooltipTextTime" />
  </div>
</template>

<script>
import { ref, computed } from 'vue'

export default {
  name: 'DateFilter',
  props: {
    modelValue: {
      type: String,
      default: null
    },
    dateLabel: {
      type: String,
      default: 'Enter date'
    },
    timeLabel: {
      type: String,
      default: 'Enter time'
    },
    timeto: {
      type: String,
      default: null
    },
    timefrom: {
      type: String,
      default: null
    },
    tooltipTextDate: {
      type: String,
      default: 'Date'
    },
    tooltipTextTime: {
      type: String,
      default: 'Time'
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const selectedDate = computed({
      get() {
        if (props.modelValue) {
          const datetime = new Date(props.modelValue)
          return new Date(
            datetime.getFullYear(),
            datetime.getMonth(),
            datetime.getDate()
          )
        }
        return null
      },
      set(newDate) {
        if (newDate) {
          const currentTime = props.modelValue
            ? new Date(props.modelValue)
            : new Date()
          currentTime.setFullYear(
            newDate.getFullYear(),
            newDate.getMonth(),
            newDate.getDate()
          )
          emit('update:modelValue', currentTime.toISOString())
        } else {
          emit('update:modelValue', null)
        }
      }
    })

    const selectedHour = computed({
      get() {
        if (props.modelValue) {
          return new Date(props.modelValue).getHours()
        }
        return null
      },
      set(newHour) {
        if (newHour !== null) {
          const currentDate = props.modelValue
            ? new Date(props.modelValue)
            : new Date()
          currentDate.setHours(newHour)
          emit('update:modelValue', currentDate.toISOString())
        }
      }
    })

    const selectedMinute = computed({
      get() {
        if (props.modelValue) {
          return new Date(props.modelValue).getMinutes()
        }
        return null
      },
      set(newMinute) {
        if (newMinute !== null) {
          const currentDate = props.modelValue
            ? new Date(props.modelValue)
            : new Date()
          currentDate.setMinutes(newMinute)
          emit('update:modelValue', currentDate.toISOString())
        }
      }
    })

    const formattedTime = computed(() => {
      if (selectedHour.value !== null && selectedMinute.value !== null) {
        const hour = selectedHour.value.toString().padStart(2, '0')
        const minute = selectedMinute.value.toString().padStart(2, '0')
        return `${hour}:${minute}`
      }
      return ''
    })

    const time_menu = ref(false)

    const clearDate = () => {
      selectedDate.value = null
      emit('update:modelValue', null)
    }

    const clearTime = () => {
      selectedHour.value = null
      selectedMinute.value = null
      const currentDate = props.modelValue
        ? new Date(props.modelValue)
        : new Date()
      currentDate.setHours(0, 0)
      emit('update:modelValue', currentDate.toISOString())
    }

    return {
      selectedDate,
      selectedHour,
      selectedMinute,
      formattedTime,
      time_menu,
      clearDate,
      clearTime
    }
  }
}
</script>
