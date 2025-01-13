<template>
  <div>
    <VueDatePicker
      v-model="selected"
      :name="'dateFilter-' + placeholder"
      :placeholder="placeholder"
      :min-date="timefrom"
      :max-date="timeto"
      format="yyyy-MM-dd HH:mm:ss"
      time-picker-inline
      auto-apply
      clearable
      space-confirm
    />
    <v-tooltip activator="parent" :text="tooltipText" />
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue'
import { useUserStore } from '@/stores/UserStore'

export default {
  name: 'DateFilter',
  props: {
    modelValue: {
      type: String,
      default: null
    },
    placeholder: {
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

    watch(
      () => props.modelValue,
      (val) => {
        selected.value = val
      }
    )

    return {
      locale,
      selected: computed({
        get: () => (selected.value ? new Date(selected.value) : null),
        set: updateSelected
      })
    }
  }
}
</script>
