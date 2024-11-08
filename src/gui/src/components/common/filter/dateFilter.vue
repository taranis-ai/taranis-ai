<template>
  <div>
    <v-date-input
      v-model="selectedDate"
      variant="outlined"
      first-day-of-week="1"
      :placeholder="dateLabel"
      :name="'dateFilter-' + dateLabel"
      :min="timefrom"
      :max="timeto"
      clearable
      @open="openMenu"
      @click:clear="selectedDate = null"
    />
    <v-tooltip activator="parent" :text="tooltipDateText" />
  </div>

  <v-menu
    v-model="time_menu"
    :close-on-content-click="false"
    transition="scale-transition"
    offset-y
  >
    <template #activator="{ props }">
      <v-text-field
        v-model="formattedTime"
        :placeholder="timeLabel"
        prepend-icon="mdi-clock-time-four-outline"
        variant="outlined"
        v-bind="props"
        readonly
        clearable
      />
    </template>
    <v-time-picker
      v-show="time_menu"
      v-model:hour="selectedTime.hour"
      v-model:minute="selectedTime.minute"
      @click:close="time_menu = false"
      format="24hr"
    />
  </v-menu>
</template>
<script>
import { ref, computed, reactive, watch, onMounted} from 'vue'
import { useUserStore } from '@/stores/UserStore'

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
    defaultDate: {
      type: Date,
      required: false,
      default: null
    },
    tooltipDateText: {
      type: String,
      required: false,
      default: null
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const userStore = useUserStore()

    const locale = computed(() => {
      return userStore.language
    })

    const selectedDate = ref(null)
    const selectedTime = reactive({
      hour: null,
      minute: null
    })
    const formattedTime = ref('')
    const time_menu = ref(false)

    onMounted(() => {
      if (props.modelValue) {
        const datetime = new Date(props.modelValue)
        selectedDate.value = new Date(
          datetime.getFullYear(),
          datetime.getMonth(),
          datetime.getDate()
        )
        selectedTime.hour = datetime.getHours()
        selectedTime.minute = datetime.getMinutes()
      }
    })

    // Update formattedTime whenever selectedTime changes
    watch(
      selectedTime,
      () => {
        if (selectedTime.hour != null && selectedTime.minute != null) {
          const hour = String(selectedTime.hour).padStart(2, '0')
          const minute = String(selectedTime.minute).padStart(2, '0')
          formattedTime.value = `${hour}:${minute}`
        } else {
          formattedTime.value = ''
        }
      },
      { immediate: true, deep: true }
    )

    // Emit update:modelValue when selectedDate or selectedTime changes
    watch(
      [selectedDate, formattedTime],
      () => {
        if (selectedDate.value && formattedTime.value) {
          const [hourStr, minuteStr] = formattedTime.value.split(':')
          const datetime = new Date(selectedDate.value)
          datetime.setHours(parseInt(hourStr, 10))
          datetime.setMinutes(parseInt(minuteStr, 10))
          datetime.setSeconds(0)
          datetime.setMilliseconds(0)
          emit('update:modelValue', datetime.toISOString())
        } else if (selectedDate.value) {
          const datetime = new Date(selectedDate.value)
          datetime.setHours(0, 0, 0, 0)
          emit('update:modelValue', datetime.toISOString())
        } else {
          emit('update:modelValue', null)
        }
      },
      { immediate: true }
    )

    function openMenu() {
      if (!selectedDate.value && props.defaultDate) {
        selectedDate.value = props.defaultDate
      }
    }

    return {
      openMenu,
      selectedDate,
      selectedTime,
      formattedTime,
      time_menu,
      locale
    }
  }
}
</script>
