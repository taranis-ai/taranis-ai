<template>
  <VueDatePicker
    v-model="selected"
    :name="'dateFilter-' + placeholder"
    :placeholder="placeholder"
    :max-date="maxDatePlus"
    time-picker-inline
    clearable
    space-confirm
    autocomplete
    @open="openMenu()"
  />
</template>

<script>
import { ref, computed, watch } from 'vue'

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
    },
    defaultDate: {
      type: Date,
      required: false,
      default: null
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const selected = ref(props.modelValue)
    const maxDatePlus = computed(() =>
      props.maxDate.setHours(props.maxDate.getHours() + 1)
    )

    function updateSelected(val) {
      if (val === null) {
        selected.value = null
      } else {
        selected.value = val.toISOString()
      }
      emit('update:modelValue', selected.value)
    }

    function openMenu() {
      console.debug(props.defaultDate)
      if (selected.value === null && props.defaultDate !== null) {
        selected.value = props.defaultDate
      }
    }

    watch(
      () => props.modelValue,
      (val) => {
        selected.value = val
      }
    )

    return {
      openMenu,
      maxDatePlus,
      selected: computed({
        get: () => Date.parse(selected.value),
        set: updateSelected
      })
    }
  }
}
</script>
