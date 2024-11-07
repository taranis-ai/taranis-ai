<template>
  <div>
    <v-date-input
      v-model="selected"
      variant="outlined"
      first-day-of-week="1"
      :label="label"
      :name="'dateFilter-' + label"
      :min="timefrom"
      :max="timeto"
      clearable
      @open="openMenu"
      @click:clear="selected = null"
    />
    <v-tooltip activator="parent" :text="tooltipText" />
  </div>

  <v-text-field
    v-model="time"
    label="Time input"
    prepend-icon="mdi-clock-time-four-outline"
    readonly
    @click="openTimeMenu"
  >
    <template #append>
      <v-menu
        v-model="menu2"
        :close-on-content-click="false"
        activator="parent"
        transition="scale-transition"
        offset-y
      >
        <v-time-picker
          v-if="menu2"
          v-model="time"
          full-width
          @click:close="menu2 = false"
        />
      </v-menu>
    </template>
  </v-text-field>
</template>
<script>
import { ref, computed, watch, nextTick } from 'vue'
import { useUserStore } from '@/stores/UserStore'

export default {
  name: 'DateFilter',
  props: {
    modelValue: {
      type: String,
      default: null
    },
    label: {
      type: String,
      default: 'Enter date'
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
    tooltipText: {
      type: String,
      required: false,
      default: null
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const selected = ref(props.modelValue)
    const time = ref(null)
    const menu2 = ref(false)
    const userStore = useUserStore()

    const locale = computed(() => {
      return userStore.language
    })

    function updateSelected(val) {
      if (val === null) {
        selected.value = null
      } else {
        selected.value = val.toISOString()
      }
      emit('update:modelValue', selected.value)
    }

    function openMenu() {
      if (selected.value === null && props.defaultDate !== null) {
        selected.value = props.defaultDate
      }
    }

    function openTimeMenu() {
      menu2.value = false
      nextTick(() => {
        menu2.value = true
      })
    }

    watch(
      () => props.modelValue,
      (val) => {
        selected.value = val
      }
    )

    return {
      openMenu,
      openTimeMenu,
      locale,
      selected: computed({
        get: () => (selected.value ? new Date(selected.value) : null),
        set: updateSelected
      }),
      time,
      menu2
    }
  }
}
</script>
