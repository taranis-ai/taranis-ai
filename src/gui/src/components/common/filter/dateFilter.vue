<template>
  <VueDatePicker
    v-model="selected"
    :name="'dateFilter-' + placeholder"
    :placeholder="placeholder"
    :max-date="maxDate"
    time-picker-inline
    clearable
    auto-apply
  />
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
    placeholder: {
      type: String,
      default: 'Enter date'
    },
    maxDate: {
      type: Date,
      default: new Date()
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const selected = ref(props.modelValue)

    const updateSelected = (val) => {
      console.debug('updateSelected', val)
      if (val === null) {
        selected.value = null
      } else {
        selected.value = val.toISOString()
      }
      emit('update:modelValue', selected.value)
    }

    return {
      selected: computed({
        get: () => Date.parse(selected.value),
        set: updateSelected
      })
    }
  }
}
</script>
